
# pylint: disable=C0114, C0115, C0116, E1101, R0914, R1702, R1732, R0913
# pylint: disable=R0917, R0912, R0915, R0902, W0718, E1121, E0611
import os
import gc
import time
import traceback
import glob
import shutil
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. core.exceptions import RunStopException
from .. core.colors import color_str
from .utils import read_img, read_and_validate_img
from .base_stack_algo import TempDirBase
from .pyramid import PyramidBase


class PyramidTilesStack(PyramidBase, TempDirBase):
    supports_alpha = True

    def __init__(self, **kwargs):
        PyramidBase.__init__(self, "fast_pyramid", **kwargs)
        TempDirBase.__init__(self)
        pyramid_default_params = DEFAULTS['pyramid_params']
        focus_stack_defaults_params = DEFAULTS['focus_stack_params']
        self.offset = np.arange(-self.pad_amount, self.pad_amount + 1)
        self.dtype = None
        self.num_pixel_values = None
        self.max_pixel_value = None
        self.tile_size = kwargs.get('tile_size', pyramid_default_params['tile_size'])
        self.n_tiled_layers = kwargs.get('n_tiled_layers', pyramid_default_params['n_tiled_layers'])
        self.n_tiles = 0
        self.level_shapes = {}
        available_cores = os.cpu_count() or 1
        max_threads = kwargs.get('max_threads', focus_stack_defaults_params['max_threads'])
        self.num_threads = max(1, min(max_threads, available_cores))
        self.min_free_space_gb = 5

    @property
    def n_ch(self):
        return 4 if self.alpha_mode else 3

    def init(self, filenames):
        super().init(filenames)
        self.n_tiles = 0
        for layer in range(self.n_tiled_layers):
            h, w = max(1, self.shape[0] // (2 ** layer)), max(1, self.shape[1] // (2 ** layer))
            self.n_tiles += (h // self.tile_size + 1) * (w // self.tile_size + 1)

    def total_steps(self, n_frames):
        n_steps = super().total_steps(n_frames)
        return n_steps + self.n_tiles

    def _process_single_image_wrapper(self, args):
        img_path, idx, _n = args
        img = read_and_validate_img(img_path, self.shape, self.dtype)
        self.check_running(self.cleanup_temp_files)
        level_count = self.process_single_image(img, self.n_levels, idx)
        return idx, img_path, level_count

    def process_single_image(self, img, levels, img_index):
        img = self.premultiply_alpha(img)
        laplacian = self.single_image_laplacian(img, levels)
        self.level_shapes[img_index] = [level.shape for level in laplacian[::-1]]
        for level_idx, level_data in enumerate(laplacian[::-1]):
            h, w = level_data.shape[:2]
            if level_idx < self.n_tiled_layers:
                for y in range(0, h, self.tile_size):
                    for x in range(0, w, self.tile_size):
                        y_end, x_end = min(y + self.tile_size, h), min(x + self.tile_size, w)
                        tile = level_data[y:y_end, x:x_end]
                        self._check_disk_space()
                        np.save(
                            os.path.join(
                                self.temp_dir_path,
                                f'img_{img_index}_level_{level_idx}_tile_{y}_{x}.npy'),
                            tile
                        )
            else:
                self._check_disk_space()
                np.save(
                    os.path.join(self.temp_dir_path,
                                 f'img_{img_index}_level_{level_idx}.npy'), level_data)
        return len(laplacian)

    def load_level_tile(self, img_index, level, y, x):
        return np.load(
            os.path.join(self.temp_dir_path,
                         f'img_{img_index}_level_{level}_tile_{y}_{x}.npy'),
            mmap_mode='r').copy()

    def load_level(self, img_index, level):
        return np.load(os.path.join(self.temp_dir_path, f'img_{img_index}_level_{level}.npy'))

    def cleanup_temp_files(self):
        try:
            if self.temp_dir_manager:
                self.temp_dir_manager.cleanup()
            else:
                pattern = os.path.join(self.temp_dir_path, 'img_*_level_*.npy')
                for file_path in glob.glob(pattern):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
        except Exception:
            traceback.print_exc()
            try:
                if self.temp_dir_manager:
                    shutil.rmtree(self.temp_dir_manager.name, ignore_errors=True)
                else:
                    pattern = os.path.join(self.temp_dir_path, 'img_*_level_*.npy')
                    for file_path in glob.glob(pattern):
                        try:
                            os.remove(file_path)
                        except Exception:
                            pass
            except Exception:
                traceback.print_exc()

    def _fuse_level_tiles_serial(self, level, num_images, all_level_counts, h, w, count):
        fused_level = np.zeros((h, w, self.n_ch), dtype=self.float_type)
        for y in range(0, h, self.tile_size):
            for x in range(0, w, self.tile_size):
                y_end, x_end = min(y + self.tile_size, h), min(x + self.tile_size, w)
                self.print_message(f': fusing tile [{x}, {x_end - 1}]×[{y}, {y_end - 1}]')
                laplacians = []
                for img_index in range(num_images):
                    if level < all_level_counts[img_index]:
                        try:
                            tile = self.load_level_tile(img_index, level, y, x)
                            laplacians.append(tile)
                        except FileNotFoundError:
                            continue
                if laplacians:
                    fused_tile = self.fuse_laplacian(laplacians)
                    fused_level[y:y_end, x:x_end] = fused_tile
                self.after_step(count)
                self.check_running(self.cleanup_temp_files)
                count += 1
        return fused_level, count

    def _fuse_level_tiles_parallel(self, level, num_images, all_level_counts, h, w, count):
        fused_level = np.zeros((h, w, self.n_ch), dtype=self.float_type)
        tiles = []
        for y in range(0, h, self.tile_size):
            for x in range(0, w, self.tile_size):
                tiles.append((y, x))
        self.print_message(f': starting parallel propcessging on {self.num_threads} cores')
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            future_to_tile = {
                executor.submit(
                    self._process_tile, level, num_images, all_level_counts, y, x, h, w): (y, x)
                for y, x in tiles
            }
            for future in as_completed(future_to_tile):
                y, x = future_to_tile[future]
                try:
                    fused_tile = future.result()
                    if fused_tile is not None:
                        y_end, x_end = min(y + self.tile_size, h), min(x + self.tile_size, w)
                        fused_level[y:y_end, x:x_end] = fused_tile
                        self.print_message(f': fused tile [{x}, {x_end - 1}]×[{y}, {y_end - 1}]')
                except RunStopException as e:
                    self.print_message(
                        color_str(f": error processing tile ({y}, {x}): {str(e)}",
                                  constants.LOG_COLOR_ALERT),
                        level=logging.ERROR)
                    raise
                except Exception as e:
                    traceback.print_exc()
                    self.print_message(f": error processing tile ({y}, {x}): {str(e)}")
                self.after_step(count)
                self.check_running(self.cleanup_temp_files)
                count += 1
        return fused_level, count

    def _process_tile(self, level, num_images, all_level_counts, y, x, h, w):
        try:
            laplacians = []
            tiles_loaded = []
            for img_index in range(num_images):
                if level < all_level_counts[img_index]:
                    try:
                        tile = self.load_level_tile(img_index, level, y, x)
                        laplacians.append(tile)
                    except FileNotFoundError:
                        traceback.print_exc()
                        continue
            if laplacians:
                result = self.fuse_laplacian(laplacians)
                for img_index, tile_y, tile_x in tiles_loaded:
                    self._delete_single_tile(img_index, level, tile_y, tile_x)
                return result
            y_end = min(y + self.tile_size, h)
            x_end = min(x + self.tile_size, w)
            gc.collect()
            return np.zeros((y_end - y, x_end - x, self.n_ch), dtype=self.float_type)
        except Exception:
            traceback.print_exc()
            self.print_message(color_str(
                f": failed to process tile ({y},{x}) at level {level}: ",
                constants.LOG_COLOR_ALERT), level=logging.ERROR)
            raise

    def _delete_single_tile(self, img_index, level, y, x):
        tile_path = os.path.join(
            self.temp_dir_path,
            f'img_{img_index}_level_{level}_tile_{y}_{x}.npy'
        )
        if os.path.exists(tile_path):
            try:
                os.remove(tile_path)
            except Exception:
                traceback.print_exc()

    def fuse_pyramids(self, all_level_counts):
        num_images = self.num_images()
        max_levels = max(all_level_counts)
        fused = []
        count = super().total_steps(num_images)
        n_layers = max_levels - 1
        self.process.callback(constants.CALLBACKS_SET_TOTAL_ACTIONS,
                              self.process.name, self.output_filename, n_layers + 1)
        action_count = 0
        for level in range(n_layers, -1, -1):
            self.print_message(f': fusing pyramids, layer: {level + 1}')
            if level < self.n_tiled_layers:
                h, w = None, None
                for img_index in range(num_images):
                    if level < all_level_counts[img_index]:
                        h, w = self.level_shapes[img_index][level][:2]
                        break
                if h is None or w is None:
                    continue
                if self.num_threads > 1:
                    fused_level, count = self._fuse_level_tiles_parallel(
                        level, num_images, all_level_counts, h, w, count)
                else:
                    fused_level, count = self._fuse_level_tiles_serial(
                        level, num_images, all_level_counts, h, w, count)
                self._delete_level_tiles(level, num_images, all_level_counts, h, w)
            else:
                laplacians = []
                for img_index in range(num_images):
                    if level < all_level_counts[img_index]:
                        laplacian = self.load_level(img_index, level)
                        laplacians.append(laplacian)
                if level == max_levels - 1:
                    fused_level = self.get_fused_base(laplacians)
                else:
                    fused_level = self.fuse_laplacian(laplacians)
                self._delete_level_files(level, num_images, all_level_counts)
                self.check_running(lambda: None)
            fused.append(fused_level)
            count += 1
            self.after_step(count)
            self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                  self.process.name, self.output_filename, action_count)
            action_count += 1
            self.check_running(lambda: None)
        self.print_message(': pyramids fusion completed')
        return fused[::-1]

    def _delete_level_tiles(self, level, num_images, all_level_counts, h, w):
        self.print_message(f': cleaning up tiles for level {level}')
        deleted_count = 0
        for img_index in range(num_images):
            if level < all_level_counts[img_index]:
                for y in range(0, h, self.tile_size):
                    for x in range(0, w, self.tile_size):
                        tile_path = os.path.join(
                            self.temp_dir_path,
                            f'img_{img_index}_level_{level}_tile_{y}_{x}.npy'
                        )
                        if os.path.exists(tile_path):
                            try:
                                os.remove(tile_path)
                                deleted_count += 1
                            except Exception as e:
                                traceback.print_exc()
                                self.print_message(
                                    f': warning: could not delete {tile_path}: {str(e)}')
        self.print_message(f': deleted {deleted_count} '
                           f'tile files for level {level + 1}')

    def _delete_level_files(self, level, num_images, all_level_counts):
        self.print_message(f': cleaning up level {level} files')
        deleted_count = 0
        for img_index in range(num_images):
            if level < all_level_counts[img_index]:
                level_path = os.path.join(
                    self.temp_dir_path,
                    f'img_{img_index}_level_{level}.npy'
                )
                if os.path.exists(level_path):
                    try:
                        os.remove(level_path)
                        deleted_count += 1
                    except Exception as e:
                        traceback.print_exc()
                        self.print_message(f': warning: could not delete {level_path}: {str(e)}')
        self.print_message(f': deleted {deleted_count} level files for level {level}')

    def calculate_max_disk_space_required(self):
        total_size_bytes = 0
        processing_size_bytes = 0
        for _img_index in range(self.num_images()):
            for level in range(self.n_levels):
                h = max(1, self.shape[0] // (2 ** level))
                w = max(1, self.shape[1] // (2 ** level))
                if level < self.n_tiled_layers:
                    for y in range(0, h, self.tile_size):
                        for x in range(0, w, self.tile_size):
                            y_end = min(y + self.tile_size, h)
                            x_end = min(x + self.tile_size, w)
                            tile_height = y_end - y
                            tile_width = x_end - x
                            tile_size_bytes = tile_height * tile_width * self.n_ch * 4
                            processing_size_bytes += tile_size_bytes
                else:
                    level_size_bytes = h * w * self.n_ch * 4  # float32
                    processing_size_bytes += level_size_bytes
        fusion_size_bytes = 0
        largest_level_size = 0
        for level in range(min(self.n_tiled_layers, self.n_levels)):
            h = max(1, self.shape[0] // (2 ** level))
            w = max(1, self.shape[1] // (2 ** level))
            level_tiles_size = 0
            for _img_index in range(self.num_images()):
                for y in range(0, h, self.tile_size):
                    for x in range(0, w, self.tile_size):
                        y_end = min(y + self.tile_size, h)
                        x_end = min(x + self.tile_size, w)
                        tile_height = y_end - y
                        tile_width = x_end - x
                        tile_size_bytes = tile_height * tile_width * self.n_ch * 4
                        level_tiles_size += tile_size_bytes
            fused_level_size = h * w * self.n_ch * 4
            total_level_size = level_tiles_size + fused_level_size
            largest_level_size = max(largest_level_size, total_level_size)
        fusion_size_bytes = largest_level_size
        total_size_bytes = max(processing_size_bytes, fusion_size_bytes)
        total_size_gb = (total_size_bytes / constants.ONE_GIGA) * 1.20
        self.print_message(
            ": disk space estimate - processing phase: "
            f"{processing_size_bytes / constants.ONE_GIGA:.2f} GB, "
            f"fusion phase: {fusion_size_bytes / constants.ONE_GIGA:.2f} GB, "
            f"required: {total_size_gb:.2f} GB"
        )
        return total_size_gb

    def check_disk_space_before_processing(self):
        required_space_gb = self.calculate_max_disk_space_required()
        _total, _used, free = shutil.disk_usage(self.temp_dir_path)
        free_gb = free / constants.ONE_GIGA
        self.print_message(
            f": estimated disk space required: {required_space_gb:.2f} GB, "
            f"available: {free_gb:.2f} GB"
        )
        if free_gb < required_space_gb:
            self.print_message(
                color_str(
                    f": insufficient temporary disk space: "
                    f"required {required_space_gb:.2f} GB, "
                    f"only {free_gb:.2f} GB available",
                    constants.LOG_COLOR_ALERT
                ),
                level=logging.ERROR
            )
            raise RunStopException("insufficient temporary disk space for tile processing")

    def _check_disk_space(self):
        _total, _used, free = shutil.disk_usage(self.temp_dir_path)
        free_gb = free / constants.ONE_GIGA
        runtime_min_gb = max(1.0, self.min_free_space_gb)  # At least 1GB
        if free_gb < runtime_min_gb:
            self.print_message(
                color_str(
                    f": critically low disk space during operation, "
                    f"only {free_gb:.2f} GB free",
                    constants.LOG_COLOR_ALERT
                ),
                level=logging.ERROR
            )
            raise RunStopException("critically low disk space during operation")

    def _safe_cleanup(self):
        try:
            self.cleanup_temp_files()
        except Exception as e:
            traceback.print_exc()
            self.print_message(f": warning during cleanup: {str(e)}")
            time.sleep(1)
            try:
                self.cleanup_temp_files()
            except Exception:
                traceback.print_exc()
                self.print_message(": could not fully clean up temporary files")

    def focus_stack(self):
        self.check_disk_space_before_processing()
        all_level_counts = [0] * self.num_images()
        if self.num_threads > 1:
            self.print_message(f': starting parallel processing on {self.num_threads} cores')
            args_list = [(file_path, i, self.num_images())
                         for i, file_path in enumerate(self.filenames)]
            executor = None
            try:
                executor = ThreadPoolExecutor(max_workers=self.num_threads)
                future_to_index = {}
                for i, args in enumerate(args_list):
                    f = executor.submit(self._process_single_image_wrapper, args)
                    future_to_index[f] = i
                    filename = os.path.basename(args[0])
                    self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                          self.process.input_path, filename, 200)
                completed_count = 0
                for future in as_completed(future_to_index):
                    i = future_to_index[future]
                    try:
                        img_index, file_path, level_count = future.result()
                        all_level_counts[img_index] = level_count
                        completed_count += 1
                        filename = os.path.basename(file_path)
                        self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                              self.process.input_path, filename, 201)
                        self.print_message(
                            f": preprocessing completed, {self.image_str(completed_count - 1)}")
                    except RunStopException as e:
                        traceback.print_exc()
                        self.print_message(
                            color_str(f": error processing {self.image_str(i)}: {str(e)}",
                                      constants.LOG_COLOR_ALERT),
                            level=logging.ERROR)
                        raise
                    except Exception as e:
                        traceback.print_exc()
                        self.print_message(
                            f": error processing {self.image_str(i)}: {str(e)}")
                    self.after_step(completed_count)
                    self.check_running(lambda: None)
            except RunStopException:
                self.print_message(color_str(": stopping parallel image processing...",
                                             constants.LOG_COLOR_ALERT),
                                   level=logging.ERROR)
                if executor:
                    executor.shutdown(wait=False, cancel_futures=True)
                    time.sleep(0.5)
                    self._safe_cleanup()
                raise
            finally:
                if executor:
                    executor.shutdown(wait=True)
        else:
            for i, file_path in enumerate(self.filenames):
                self.print_message(
                    f": processing {self.image_str(i)}")
                img = read_img(file_path)
                try:
                    level_count = self.process_single_image(img, self.n_levels, i)
                    all_level_counts[i] = level_count
                except Exception as e:
                    traceback.print_exc()
                    self.process.sub_message_r(color_str(
                        f": failed to process {self.image_str(i)}: ", constants.LOG_COLOR_ALERT),
                        level=logging.ERROR)
                    self._safe_cleanup()
                    raise RuntimeError(f"failed to process {self.image_str(i)}: {str(e)}") from e
                self.after_step(i + 1)
                self.check_running(lambda: None)
        try:
            self.check_running(lambda: None)
            try:
                fused_pyramid = self.fuse_pyramids(all_level_counts)
                stacked_image = self.collapse(fused_pyramid)
                stacked_image = self.unpremultiply_alpha(stacked_image).astype(self.dtype)
            except Exception as e:
                traceback.print_exc()
                self.process.sub_message_r(color_str(
                    f": failed to process {self.image_str(i)}: ", constants.LOG_COLOR_ALERT),
                    level=logging.ERROR)
                self._safe_cleanup()
                raise RuntimeError(f"failed to process {self.image_str(i)}: {str(e)}") from e
            return stacked_image
        except RunStopException:
            self.print_message(": stopping pyramid fusion...")
            raise
        finally:
            self._safe_cleanup()
