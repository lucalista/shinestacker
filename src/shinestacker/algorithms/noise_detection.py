# pylint: disable=C0114, C0115, C0116, E1101, W0718, R0914, R0915, R0902, R0912, R0913, R0917
import os
import errno
import logging
import cv2
import numpy as np
import matplotlib.pyplot as plt
from .. config.config import config
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. config.app_config import AppConfig
from .. core.colors import color_str
from .. core.exceptions import ImageLoadError, InvalidOptionError
from .. core.framework import TaskBase
from .. core.core_utils import make_tqdm_bar, setup_matplotlib_mode
from .. core.exceptions import RunStopException, ShapeError
from .stack_framework import ImageSequenceManager, SubAction
from .utils import read_img, get_img_metadata, validate_image, bgr_to_lab
setup_matplotlib_mode()


def mean_image(file_paths, max_frames=-1, message_callback=None, progress_callback=None):
    mean_img = None
    counter = 0
    for i, path in enumerate(file_paths):
        if 1 <= max_frames <= i:
            break
        if message_callback:
            message_callback(i, path)
        if not os.path.exists(path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        try:
            img = read_img(path)
        except Exception:
            logger = logging.getLogger(__name__)
            logger.error(msg=f"Can't open file: {path}")
        if mean_img is None:
            metadata = get_img_metadata(img)
            mean_img = img.astype(np.float64)
            if metadata[1] == np.uint16:
                mean_img /= 256
        else:
            validate_image(img, *metadata)
            img = img.astype(np.float64)
            if metadata[1] == np.uint16:
                img /= 256
            mean_img += img
        counter += 1
        if progress_callback:
            progress_callback(i)
    if mean_img is None:
        return None
    mean_img = np.rint(mean_img / counter)
    if metadata[1] == np.uint16:
        return mean_img.astype(np.uint16)
    return mean_img.astype(np.uint8)


class NoiseDetectionRGB:
    def __init__(self, **kwargs):
        self.noisy_masked_px = kwargs.get(
            'noisy_masked_px', DEFAULTS['noise_detection_params']['noisy_masked_px'])
        self.channel_thresholds = kwargs.get(
            'channel_thresholds', DEFAULTS['noise_detection_params']['channel_thresholds'])
        self.plot_manager = None

    def set_plot_manager(self, plot_manager):
        self.plot_manager = plot_manager
        print("set plot manager: ", self.plot_manager)

    def hot_map(self, ch, th):
        return cv2.threshold(ch, th, 255, cv2.THRESH_BINARY)[1]

    def detect_hot_pixels(self, mean_img, blurred):
        diff = cv2.absdiff(mean_img, blurred)
        channels = cv2.split(diff)
        for c in range(3):
            if self.noisy_masked_px[c] > 0:
                ch = channels[c]
                min_lumi, max_lumi = ch.min(), ch.max()
                num_bins = int(max_lumi - min_lumi + 1)
                hist = cv2.calcHist([ch], [0], None, [num_bins], [min_lumi, max_lumi + 1])
                hist = hist.flatten()
                pxls_count = np.cumsum(hist[::-1])[::-1]
                lumi = np.arange(min_lumi, max_lumi + 1)
                mask = pxls_count >= self.noisy_masked_px[c]
                if mask.any():
                    self.channel_thresholds[c] = lumi[mask].max() - 1
                else:
                    self.channel_thresholds[c] = max_lumi
        hot_px = [self.hot_map(ch, self.channel_thresholds[i]) for i, ch in enumerate(channels)]
        hot_rgb = cv2.bitwise_or(hot_px[0], cv2.bitwise_or(hot_px[1], hot_px[2]))
        msg = []
        for ch, hot in zip(['rgb', *constants.RGB_LABELS], [hot_rgb] + hot_px):
            hpx = color_str(
                f"{ch}: {np.count_nonzero(hot > 0)}",
                {'rgb': 'black', 'r': 'red', 'g': 'green', 'b': 'blue'}[ch])
            msg.append(hpx)
        return hot_rgb, {
            'channel_thresholds': self.channel_thresholds,
            'hot_px_per_channel': hot_px,
            'message': "hot pixels: " + ", ".join(msg)
        }

    def plot_detection_results(
            self, mean_img, blurred, _hot_rgb, _detection_info, working_path,
            plot_path, name, callback, idx):
        diff = cv2.absdiff(mean_img, blurred)
        channels = cv2.split(diff)
        fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
        for i, ch, color in zip(range(3), channels, constants.RGB_LABELS):
            min_val, max_val = ch.min(), ch.max()
            bin_edges = np.arange(min_val, max_val + 0.2, 0.2)
            hist, bin_edges = np.histogram(ch, bins=bin_edges)
            pxls_count = np.cumsum(hist[::-1])[::-1]
            plt.step(bin_edges[:-1], pxls_count, c=color,
                     label=color.upper() + " abs. deviation distribution")
            xt = self.channel_thresholds[i]
            idx = np.argmin(np.abs(bin_edges[:-1] - xt))
            if idx < len(pxls_count):
                yt = pxls_count[idx]
                plt.plot([xt, xt], [0, yt], c=color, linestyle="--")
                plt.plot([bin_edges[0], xt], [yt, yt], c=color, linestyle="--")
        plt.xlabel('R, G, B abs. deviation')
        plt.ylabel('# of hot pixels')
        plt.legend()
        plt.xlim(bin_edges[0], bin_edges[-2])
        plt.yscale("log", nonpositive='clip')
        plots_ext = AppConfig.get('plots_format')
        plot_path = f"{working_path}/{plot_path}/{name}-hot-pixels.{plots_ext}"
        print("save plot: ", plot_path)
        self.plot_manager.save_plot(plot_path, fig)
        callback(constants.CALLBACK_SAVE_PLOT, idx, name, f"{name}: noise", plot_path)


class NoiseDetectionLAB:
    def __init__(self, **kwargs):
        self.noisy_masked_px = kwargs.get(
            'noisy_masked_px', DEFAULTS['noise_detection_params']['noisy_masked_px'])
        self.channel_thresholds = kwargs.get(
            'channel_thresholds', DEFAULTS['noise_detection_params']['channel_thresholds'])
        self.use_lab_space = kwargs.get(
            'use_lab_space', DEFAULTS['noise_detection_params']['use_lab_space'])
        self.plot_manager = None

    def set_plot_manager(self, plot_manager):
        self.plot_manager = plot_manager

    def calculate_distance_metric(self, mean_img, blurred):
        if self.use_lab_space:
            try:
                lab_mean = bgr_to_lab(mean_img)
                lab_blurred = bgr_to_lab(blurred)
                diff = lab_mean.astype(np.float64) - lab_blurred.astype(np.float64)
                distance = np.sqrt(np.sum(diff**2, axis=2))
                metric_name = "LAB Euclidean Distance"
            except (ImportError, AttributeError):
                self.use_lab_space = False
                return self.calculate_distance_metric(mean_img, blurred)
        else:
            diff = mean_img.astype(np.float64) - blurred.astype(np.float64)
            distance = np.sqrt(np.sum(diff**2, axis=2))
            metric_name = "RGB Euclidean Distance"
        return distance, metric_name

    def detect_hot_pixels(self, mean_img, blurred):
        distance_map, metric_name = self.calculate_distance_metric(mean_img, blurred)
        if self.noisy_masked_px > 0:
            min_val, max_val = distance_map.min(), distance_map.max()
            bin_edges = np.arange(min_val, max_val + 0.01, 0.01)
            hist, bin_edges = np.histogram(distance_map, bins=bin_edges)
            pxls_count = np.cumsum(hist[::-1])[::-1]
            mask = pxls_count >= self.noisy_masked_px
            if mask.any():
                adaptive_threshold = bin_edges[:-1][mask].max()
            else:
                adaptive_threshold = max_val
            threshold_method = f"histogram (max {self.noisy_masked_px} pixels)"
        else:
            mean_dist = np.mean(distance_map)
            std_dist = np.std(distance_map)
            adaptive_threshold = mean_dist + self.channel_thresholds[0] * std_dist
            threshold_method = f"statistical (mean + {self.channel_thresholds[0]}×std)"
        hot_rgb = np.where(distance_map >= adaptive_threshold, 255, 0).astype(np.uint8)
        detection_info = {
            'distance_map': distance_map,
            'adaptive_threshold': adaptive_threshold,
            'metric_name': metric_name,
            'threshold_method': threshold_method
        }
        return hot_rgb, detection_info

    def plot_detection_results(
            self, _mean_img, _blurred, _hot_rgb, detection_info, working_path,
            plot_path, name, callback, idx):
        distance_map = detection_info['distance_map']
        adaptive_threshold = detection_info['adaptive_threshold']
        min_val, max_val = distance_map.min(), distance_map.max()
        bin_edges = np.arange(min_val, max_val + 0.01, 0.01)
        hist, bin_edges = np.histogram(distance_map, bins=bin_edges)
        pxls_count = np.cumsum(hist[::-1])[::-1]
        fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
        label = "LAB norm" if self.use_lab_space else "RGB norm"
        plt.step(bin_edges[:-1], pxls_count, c='blue', label=label + " distribution")
        idx = np.argmin(np.abs(bin_edges[:-1] - adaptive_threshold))
        if idx < len(pxls_count):
            yt = pxls_count[idx]
            plt.plot([adaptive_threshold, adaptive_threshold], [0, yt], c='blue', linestyle="--")
            plt.plot([bin_edges[0], adaptive_threshold], [yt, yt], c='blue', linestyle="--")
        plt.xlabel(label)
        plt.ylabel('# of hot pixels')
        plt.legend()
        if len(bin_edges) > 1:
            plt.xlim(bin_edges[0], bin_edges[-2])
        plt.yscale("log", nonpositive='clip')
        plots_ext = AppConfig.get('plots_format')
        plot_path = f"{working_path}/{plot_path}/{name}-distance-histogram.{plots_ext}"
        self.plot_manager.save_plot(plot_path, fig)
        callback(constants.CALLBACK_SAVE_PLOT, idx, name,
                 f"{name}: distance histogram", plot_path)
        plt.close('all')


class NoiseDetection(TaskBase, ImageSequenceManager):
    def __init__(self, name="noise-map", enabled=True, **kwargs):
        ImageSequenceManager.__init__(self, name, **kwargs)
        TaskBase.__init__(self, name, enabled)
        self.max_frames = kwargs.get(
            'max_frames', DEFAULTS['noise_detection_params']['max_frames'])
        self.blur_size = kwargs.get(
            'blur_size', DEFAULTS['noise_detection_params']['blur_size'])
        self.file_name = kwargs.get(
            'file_name', DEFAULTS['noise_detection_params']['noise_map_filename'])
        if self.file_name == '':
            self.file_name = DEFAULTS['noise_detection_params']['noise_map_filename']
        self.plot_histograms = kwargs.get(
            'plot_histograms', DEFAULTS['noise_detection_params']['plot_histograms'])
        self.tbar = None
        self.method = kwargs.pop('method', DEFAULTS['noise_detection_params']['method'])
        if self.method != constants.NOISE_METHOD_RGB:
            kwargs['noisy_masked_px'] = kwargs.get(
                'noisy_masked_px', DEFAULTS['noise_detection_params']['noisy_masked_px'])[0]
        self.max_noisy_pxls = kwargs.pop(
            'max_noisy_pxls', DEFAULTS['mask_noise_params']['max_noisy_pxls'])
        if self.method == constants.NOISE_METHOD_RGB:
            self._implementation = NoiseDetectionRGB(**kwargs)
        elif self.method == constants.NOISE_METHOD_NORM_LAB:
            self._implementation = NoiseDetectionLAB(use_lab_space=True, **kwargs)
        elif self.method == constants.NOISE_METHOD_NORM_RGB:
            self._implementation = NoiseDetectionLAB(use_lab_space=False, **kwargs)
        else:
            raise InvalidOptionError("method", self.method)

    def init(self, job):
        ImageSequenceManager.init(self, job)
        self._implementation.set_plot_manager(self.plot_manager)

    def progress(self, i):
        self.callback(constants.CALLBACK_AFTER_STEP, self.id, self.name, i + 1)
        if not config.DISABLE_TQDM:
            self.tbar.update(1)
            if self.callback(constants.CALLBACK_CHECK_RUNNING, self.id, self.name) is False:
                raise RunStopException(self.name)

    def run_core(self):
        self.print_message(
            color_str(f"noise detection with method {self.method}",
                      constants.LOG_COLOR_LEVEL_2))
        self.print_message(
            color_str(f"map noisy pixels from frames in {self.folder_list_str()}",
                      constants.LOG_COLOR_LEVEL_2))
        in_paths = self.input_filepaths()
        if len(in_paths) == 0:
            raise ValueError("No image files found in the selected path")
        n_frames = min(len(in_paths), self.max_frames) if self.max_frames > 0 else len(in_paths)
        self.callback(constants.CALLBACK_STEP_COUNTS, self.id, self.name, n_frames)
        if not config.DISABLE_TQDM:
            self.tbar = make_tqdm_bar(self.name, n_frames)

        def progress_callback(i):
            self.progress(i)
            if self.callback(constants.CALLBACK_CHECK_RUNNING, self.id, self.name) is False:
                raise RunStopException(self.name)

        mean_img = mean_image(
            file_paths=in_paths, max_frames=self.max_frames,
            message_callback=lambda i, path: self.print_message_r(
                color_str(f"reading frame {i + 1}/{n_frames}: {os.path.basename(path)}",
                          constants.LOG_COLOR_LEVEL_2)), progress_callback=progress_callback)
        # write_img(os.path.join(self.working_path, self.output_path, "mean-img.jpg"), mean_img)
        if not config.DISABLE_TQDM:
            self.tbar.close()
        if mean_img is None:
            raise RuntimeError("Mean image is None")
        blurred = cv2.GaussianBlur(mean_img, (self.blur_size, self.blur_size), 0)
        hot_rgb, detection_info = self._implementation.detect_hot_pixels(mean_img, blurred)
        if 'message' in detection_info:
            self.print_message(color_str(detection_info['message'], constants.LOG_COLOR_LEVEL_2))
        n_noisy_pixels = np.count_nonzero(hot_rgb > 0)
        self.print_message(color_str(f"hot pixels detected: {n_noisy_pixels}",
                           constants.LOG_COLOR_LEVEL_2))
        if n_noisy_pixels > self.max_noisy_pxls:
            raise RuntimeError(
                f"Too many hot pixels selected: {n_noisy_pixels} > {self.max_noisy_pxls}.\n"
                "Reduce the number of noisy pixels to mask.")
        output_full_path = os.path.join(self.working_path, self.output_path)
        if not os.path.exists(output_full_path):
            self.print_message(f"create directory: {self.output_path}")
            os.mkdir(output_full_path)
        file_path = os.path.join(self.output_path, self.file_name)
        self.print_message(color_str(f"writing hot pixels map file: {file_path}",
                           constants.LOG_COLOR_LEVEL_2))
        cv2.imwrite(os.path.join(output_full_path, self.file_name), hot_rgb)
        if self.plot_histograms:
            self._implementation.plot_detection_results(
                mean_img, blurred, hot_rgb, detection_info, self.working_path, self.plot_path,
                self.name, self.callback, self.id)
        return True


class MaskNoise(SubAction):
    def __init__(self, name='', enabled=True, **kwargs):
        self.noise_mask = kwargs.get(
            'noise_mask', DEFAULTS['noise_detection_params']['noise_map_filename'])
        self.max_noisy_pxls = kwargs.get(
            'max_noisy_pxls', DEFAULTS['mask_noise_params']['max_noisy_pxls'])
        self.kernel_size = kwargs.get(
            'kernel_size', DEFAULTS['mask_noise_params']['kernel_size'])
        self.ks2 = self.kernel_size // 2
        self.ks2_1 = self.ks2 + 1
        self.method = kwargs.get(
            'method', DEFAULTS['mask_noise_params']['method'])
        super().__init__(name, enabled)
        self.process = None
        self.noise_mask_img = None
        self.expected_shape = None

    def begin(self, process):
        self.process = process
        path = os.path.join(process.working_path, self.noise_mask)
        if os.path.exists(path):
            self.process.sub_message_r(color_str(
                f': reading noisy pixel mask file: {self.noise_mask}',
                constants.LOG_COLOR_LEVEL_3))
            self.noise_mask_img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            self.expected_shape = self.noise_mask_img.shape[:2]
            if self.noise_mask_img is None:
                raise ImageLoadError(path, f"failed to load image file {self.noise_mask}.")
        else:
            raise ImageLoadError(path, "file not found.")

    def run_frame(self, idx, _ref_idx, image):
        self.process.print_message(color_str(
            f'{self.process.frame_str(idx)}: mask noisy pixels', constants.LOG_COLOR_LEVEL_3))
        shape = image.shape[:2]
        if shape != self.expected_shape:
            raise ShapeError(self.expected_shape, shape)
        if len(image.shape) == 3:
            corrected = image.copy()
            for c in range(3):
                corrected[:, :, c] = self.correct_channel(image[:, :, c])
        else:
            corrected = self.correct_channel(image)
        return corrected

    def correct_channel(self, channel):
        corrected = channel.copy()
        noise_coords = np.argwhere(self.noise_mask_img > 0)
        n_noisy_pixels = noise_coords.shape[0]
        if n_noisy_pixels > self.max_noisy_pxls:
            raise RuntimeError(
                f"Noise map contains too many hot pixels: {n_noisy_pixels} > {self.max_noisy_pxls}")
        for y, x in noise_coords:
            neighborhood = channel[
                max(0, y - self.ks2):min(channel.shape[0], y + self.ks2_1),
                max(0, x - self.ks2):min(channel.shape[1], x + self.ks2_1)
            ]
            valid_pixels = neighborhood[neighborhood != 0]
            if len(valid_pixels) > 0:
                if self.method == constants.INTERPOLATE_MEAN:
                    corrected[y, x] = np.mean(valid_pixels)
                elif self.method == constants.INTERPOLATE_MEDIAN:
                    corrected[y, x] = np.median(valid_pixels)
        return corrected
