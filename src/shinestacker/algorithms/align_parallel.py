# pylint: disable=C0114, C0115, C0116, W0718, R0912, R0915, E1101, R0914, R0911, E0606, R0801, R0902
# pylint: disable=R0913, R0917
import gc
import os
import copy
import traceback
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. config.app_config import AppConfig
from .. core.exceptions import RunStopException
from .. core.colors import color_str
from .. core.core_utils import make_chunks
from .utils import read_img, img_bw, get_output_filename
from .align import AlignFramesBase
from .transform_estimate import check_transform


def compose_transforms(t1, t2, transform_type):
    t1 = t1.astype(np.float64)
    t2 = t2.astype(np.float64)
    if transform_type == constants.ALIGN_RIGID:
        t1_homo = np.vstack([t1, [0, 0, 1]])
        t2_homo = np.vstack([t2, [0, 0, 1]])
        result_homo = t2_homo @ t1_homo
        return result_homo[:2, :]
    return t2 @ t1


class AlignFramesParallel(AlignFramesBase):
    def __init__(self, name='', enabled=True, feature_config=None, matching_config=None,
                 alignment_config=None, **kwargs):
        super().__init__(name, enabled, feature_config, matching_config,
                         alignment_config, use_large_thresholds=False, **kwargs)
        self.max_threads = kwargs.get(
            'max_threads', DEFAULTS['align_frames_params']['max_threads'])
        self.chunk_submit = kwargs.get(
            'chunk_submit', DEFAULTS['align_frames_params']['chunk_submit'])
        self.bw_matching = kwargs.get(
            'bw_matching', DEFAULTS['align_frames_params']['bw_matching'])
        self.delta_max = kwargs.get(
            'delta_max', DEFAULTS['align_frames_params']['delta_max'])
        self._img_cache = None
        self._img_shapes = None
        self._img_locks = None
        self._cache_locks = None
        self._target_indices = None
        self._transforms = None
        self._cumulative_transforms = None
        self.step_counter = 0
        self._kp = None
        self._des = None

    def get_img_ref(self, ref_idx):
        return self.process.img_ref(ref_idx)

    def cache_img(self, idx):
        with self._cache_locks[idx]:
            self._img_locks[idx] += 1
            if self._img_cache[idx] is None:
                img = read_img(self.process.input_filepath(idx))
                if self.bw_matching:
                    img = img_bw(img)
                self._img_cache[idx] = img
                if img is not None:
                    self._img_shapes[idx] = img.shape
            return self._img_cache[idx]

    @staticmethod
    def frame_status_name(input_filepath):
        # frame status boxes are registered under the output file name
        # (see CombinedActions.begin), which differs from the input name
        # for RAW input files (e.g. DSC00001.ARW -> DSC00001.tif)
        return os.path.basename(get_output_filename(input_filepath))

    def submit_threads(self, idxs, imgs):
        with ThreadPoolExecutor(max_workers=len(imgs)) as executor:
            future_to_index = {}
            for idx in idxs:
                self.print_message(
                    f"submit alignment matches, {self.image_str(idx)}")
                future = executor.submit(self.find_transform, idx)
                future_to_index[future] = idx
                filename = self.frame_status_name(self.process.input_filepath(idx))
                self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                      self.process.output_path, filename, 100)
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                filename = self.frame_status_name(self.process.input_filepath(idx))
                try:
                    info_messages, warning_messages = future.result()
                    message = f"{self.image_str(idx)}: " \
                              f"good matches found: {self._n_good_matches[idx]}"
                    if len(info_messages) > 0:
                        message += ", " + ", ".join(info_messages)
                    color = constants.LOG_COLOR_LEVEL_3
                    level = logging.INFO
                    if len(warning_messages) > 0:
                        message += "; " + color_str("; ".join(warning_messages), 'yellow')
                        color = constants.LOG_COLOR_WARNING
                        level = logging.WARNING
                    self.print_message(message, color=color, level=level)
                    self.step_counter += 1
                    self.process.after_step(self.step_counter)
                    self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                          self.process.output_path, filename, 101)
                    self.process.check_running()
                except RunStopException as e:
                    self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                          self.process.output_path, filename, 1001)
                    raise e
                except Exception as e:
                    traceback.print_exc()
                    self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                          self.process.output_path, filename, 1001)
                    self.print_message(
                        color_str(f"failed processing {self.image_str(idx)}: {str(e)}",
                                  constants.LOG_COLOR_WARNING),
                        level=logging.WARNING)
            for i in range(self.process.num_input_filepaths()):
                if self._img_locks[i] >= 2:
                    self._img_cache[i] = None
                    self._img_locks[i] = 0
        gc.collect()

    def begin(self, process):
        super().begin(process)
        n_frames = self.process.num_input_filepaths()
        if n_frames < 2:
            return
        self.print_message(f"preprocess {n_frames} images in parallel, cores: {self.max_threads}")
        self.process.callback(constants.CALLBACK_STEP_COUNTS,
                              self.process.id, self.process.name, 2 * n_frames)
        input_filepaths = self.process.input_filepaths()
        self._img_cache = [None] * n_frames
        self._img_shapes = [None] * n_frames
        self._img_locks = [0] * n_frames
        self._cache_locks = [threading.Lock() for _ in range(n_frames)]
        self._target_indices = [None] * n_frames
        self._n_good_matches = [0] * n_frames
        self._transforms = [None] * n_frames
        self._cumulative_transforms = [None] * n_frames
        self._kp = [None] * n_frames
        self._des = [None] * n_frames
        max_chunk_size = self.max_threads
        ref_idx = self.process.ref_idx
        self.print_message(f"reference: {self.image_str(ref_idx)}")
        sub_indices = list(range(n_frames))
        sub_indices.remove(ref_idx)
        sub_img_filepaths = copy.deepcopy(input_filepaths)
        ref_filepath = input_filepaths[ref_idx]
        sub_img_filepaths.remove(ref_filepath)
        filename = self.frame_status_name(ref_filepath)
        self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                              self.process.output_path, filename, 101)
        self.step_counter = 0
        if self.chunk_submit:
            img_chunks = make_chunks(sub_img_filepaths, max_chunk_size)
            idx_chunks = make_chunks(sub_indices, max_chunk_size)
            for idxs, imgs in zip(idx_chunks, img_chunks):
                self.submit_threads(idxs, imgs)
        else:
            self.submit_threads(sub_indices, sub_img_filepaths)
        for idx in range(n_frames):
            if self._img_cache[idx] is not None:
                self._img_cache[idx] = None
                self._kp[idx] = None
                self._des[idx] = None
        gc.collect()
        self.print_message("combining transformations")
        transform_type = self.alignment_config['transform']
        if transform_type == constants.ALIGN_RIGID:
            identity = np.array([[1.0, 0.0, 0.0],
                                 [0.0, 1.0, 0.0]], dtype=np.float64)
        else:
            identity = np.eye(3, dtype=np.float64)
        self._cumulative_transforms[ref_idx] = identity
        frames_to_process = []
        for i in range(n_frames):
            if i != ref_idx:
                frames_to_process.append((i, abs(i - ref_idx)))
        frames_to_process.sort(key=lambda x: x[1])
        for i, _ in frames_to_process:
            target_idx = self._target_indices[i]
            if target_idx is not None and self._cumulative_transforms[target_idx] is not None:
                self._cumulative_transforms[i] = compose_transforms(
                    self._transforms[i], self._cumulative_transforms[target_idx], transform_type)
            else:
                self._cumulative_transforms[i] = None
                self.print_message(
                    f"warning: no cumulative transform for {self.image_str(i)}",
                    color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
        for idx in range(n_frames):
            self._transforms[idx] = None
        gc.collect()
        missing_transforms = 0
        thresholds = self.get_transform_thresholds_large()
        for i in range(n_frames):
            if self._cumulative_transforms[i] is not None:
                self._cumulative_transforms[i] = self._cumulative_transforms[i].astype(np.float32)
                is_valid, reason, result = check_transform(
                    self._cumulative_transforms[i], self._img_shapes[i],
                    transform_type, *thresholds)
                if is_valid:
                    self.save_transform_result(i, result)
                else:
                    self.print_message(
                        f"invalid cumulative transform for {self.image_str(i)}",
                        color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
                if self.alignment_config['abort_abnormal']:
                    self._cumulative_transforms[i] = None
                    raise RuntimeError(f"invalid cumulative transformation: {reason}")
            else:
                missing_transforms += 1
        msg = "feature extaction completed"
        if missing_transforms > 0:
            msg += ", " + color_str(f"images not matched: {missing_transforms}",
                                    constants.LOG_COLOR_WARNING)
        self.print_message(msg)
        self.process.add_begin_steps(n_frames)

    def find_transform(self, idx, delta=1):
        ref_idx = self.process.ref_idx
        if delta > self.delta_max:
            if self.delta_max > 1:
                msg = f"next {self.delta_max} frames not matched, frame skipped"
            else:
                msg = "next frame not matched, frame skipped"
            return [], [msg]
        pass_ref_err_msg = "cannot find path to reference frame"
        if idx < ref_idx:
            target_idx = idx + delta
            if target_idx > ref_idx:
                self._target_indices[idx] = None
                self._transforms[idx] = None
                return [], [pass_ref_err_msg]
        elif idx > ref_idx:
            target_idx = idx - delta
            if target_idx < ref_idx:
                self._target_indices[idx] = None
                self._transforms[idx] = None
                return [], [pass_ref_err_msg]
        else:
            self._target_indices[idx] = None
            self._transforms[idx] = None
            return [], []
        info_messages = []
        warning_messages = []
        img_0 = self.cache_img(idx)
        img_ref = self.cache_img(target_idx)

        idx_str = f"{idx:04d}"
        if self.plot_matches:
            plots_ext = AppConfig.get('plots_format')
            plot_path = os.path.join(
                self.process.working_path,
                self.process.plot_path,
                f"{self.process.name}-matches-{idx_str}.{plots_ext}")
        else:
            plot_path = None
        save_plot_name = self.process.output_path if self.name == '' else self.name
        callbacks = {
            'save_plot': lambda plot_path, tag="_default": self.process.callback(
                constants.CALLBACK_SAVE_PLOT, self.process.id, save_plot_name,
                f"{self.process.name}: matches\nframe {idx_str}", plot_path, tag),
        }
        m, phase_corr_called, _quality, n_good_matches = self.compute_transformation(
            idx, img_ref, img_0, callbacks, plot_path)
        self._n_good_matches[idx] = n_good_matches
        if m is None:
            if phase_corr_called:
                return info_messages, warning_messages
            return self.find_transform(idx, delta + 1)
        self._transforms[idx] = m
        self._target_indices[idx] = target_idx
        return info_messages, warning_messages

    def align_images(self, idx, img_ref, img_0):
        m = self._cumulative_transforms[idx]
        if m is None:
            self.print_message(
                f"no transformation for {self.image_str(idx)}, image skipped",
                color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
            return None
        callbacks = {
            'estimation_message':
                lambda: self.print_message(f'{self.image_str(idx)}: apply image alignment'),
            'blur_message':
                lambda: self.print_message(f'{self.image_str(idx)}: blur borders'),
            'warning':
                lambda msg: self.print_message(color_str(
                    f'{self.image_str(idx)}: {msg}', constants.LOG_COLOR_WARNING),
                    level=logging.WARNING)
        }
        return self.transformation_extractor.apply_alignment_transform(img_0, img_ref, m, callbacks)
