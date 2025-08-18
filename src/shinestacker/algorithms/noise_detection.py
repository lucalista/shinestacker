# pylint: disable=C0114, C0115, C0116, E1101, W0718, R0914, R0915
import os
import errno
import logging
import cv2
import numpy as np
import matplotlib.pyplot as plt
from .. config.config import config
from .. config.constants import constants
from .. core.colors import color_str
from .. core.exceptions import ImageLoadError
from .. core.framework import JobBase
from .. core.core_utils import make_tqdm_bar
from .. core.exceptions import RunStopException
from .stack_framework import FrameMultiDirectory, SubAction
from .utils import read_img, save_plot, get_img_metadata, validate_image

MAX_NOISY_PIXELS = 1000


def mean_image(file_paths, max_frames=-1, message_callback=None, progress_callback=None):
    mean_img = None
    counter = 0
    for i, path in enumerate(file_paths):
        if 1 <= max_frames < i:
            break
        if message_callback:
            message_callback(path)
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
        else:
            validate_image(img, *metadata)
            mean_img += img.astype(np.float64)
        counter += 1
        if progress_callback:
            progress_callback(i)
    return None if mean_img is None else (mean_img / counter).astype(np.uint8)


class NoiseDetection(JobBase, FrameMultiDirectory):
    def __init__(self, name="noise-map", enabled=True, **kwargs):
        FrameMultiDirectory.__init__(self, name, **kwargs)
        JobBase.__init__(self, name, enabled)
        self.max_frames = kwargs.get('max_frames', -1)
        self.blur_size = kwargs.get('blur_size', constants.DEFAULT_BLUR_SIZE)
        self.file_name = kwargs.get('file_name', constants.DEFAULT_NOISE_MAP_FILENAME)
        if self.file_name == '':
            self.file_name = constants.DEFAULT_NOISE_MAP_FILENAME
        self.channel_thresholds = kwargs.get(
            'channel_thresholds', constants.DEFAULT_CHANNEL_THRESHOLDS
        )
        self.plot_range = kwargs.get('plot_range', constants.DEFAULT_NOISE_PLOT_RANGE)
        self.plot_histograms = kwargs.get('plot_histograms', False)
        self.tbar = None

    def hot_map(self, ch, th):
        return cv2.threshold(ch, th, 255, cv2.THRESH_BINARY)[1]

    def progress(self, i):
        self.callback('after_step', self.id, self.name, i)
        if not config.DISABLE_TQDM:
            self.tbar.update(1)
            if self.callback('check_running', self.id, self.name) is False:
                raise RunStopException(self.name)

    def run_core(self):
        self.print_message(color_str(
            f"map noisy pixels from frames in {self.folder_list_str()}",
            constants.LOG_COLOR_LEVEL_2
        ))
        files = self.folder_filelist()
        in_paths = [self.working_path + "/" + f for f in files]
        n_frames = min(len(in_paths), self.max_frames) if self.max_frames > 0 else len(in_paths)
        self.callback('step_counts', self.id, self.name, n_frames)
        if not config.DISABLE_TQDM:
            self.tbar = make_tqdm_bar(self.name, n_frames)

        def progress_callback(i):
            self.progress(i)
            if self.callback('check_running', self.id, self.name) is False:
                raise RunStopException(self.name)
        mean_img = mean_image(
            file_paths=in_paths, max_frames=self.max_frames,
            message_callback=lambda path: self.print_message_r(
                color_str(f"reading frame: {path.split('/')[-1]}", constants.LOG_COLOR_LEVEL_2)
            ),
            progress_callback=progress_callback)
        if not config.DISABLE_TQDM:
            self.tbar.close()
        if mean_img is None:
            raise RuntimeError("Mean image is None")
        blurred = cv2.GaussianBlur(mean_img, (self.blur_size, self.blur_size), 0)
        diff = cv2.absdiff(mean_img, blurred)
        channels = cv2.split(diff)
        hot_px = [self.hot_map(ch, self.channel_thresholds[i]) for i, ch in enumerate(channels)]
        hot_rgb = cv2.bitwise_or(hot_px[0], cv2.bitwise_or(hot_px[1], hot_px[2]))
        msg = []
        for ch, hot in zip(['rgb', *constants.RGB_LABELS], [hot_rgb] + hot_px):
            hpx = color_str(f"{ch}: {np.count_nonzero(hot > 0)}",
                            {'rgb': 'black', 'r': 'red', 'g': 'green', 'b': 'blue'}[ch])
            msg.append(hpx)
        self.print_message(color_str("hot pixels: " + ", ".join(msg), constants.LOG_COLOR_LEVEL_2))
        path = "/".join(self.file_name.split("/")[:-1])
        if not os.path.exists(f"{self.working_path}/{path}"):
            self.print_message(f"create directory: {path}")
            os.mkdir(f"{self.working_path}/{path}")
        self.print_message(color_str(f"writing hot pixels map file: {self.file_name}",
                                     constants.LOG_COLOR_LEVEL_2))
        cv2.imwrite(f"{self.working_path}/{self.file_name}", hot_rgb)
        plot_range = self.plot_range
        min_th, max_th = min(self.channel_thresholds), max(self.channel_thresholds)
        if min_th < plot_range[0]:
            plot_range[0] = min_th - 1
        if max_th > plot_range[1]:
            plot_range[1] = max_th + 1
        th_range = np.arange(self.plot_range[0], self.plot_range[1] + 1)
        if self.plot_histograms:
            plt.figure(figsize=(10, 5))
            x = np.array(list(th_range))
            ys = [[np.count_nonzero(self.hot_map(ch, th) > 0)
                  for th in th_range] for ch in channels]
            for i, ch, y in zip(range(3), constants.RGB_LABELS, ys):
                plt.plot(x, y, c=ch, label=ch)
                plt.plot([self.channel_thresholds[i], self.channel_thresholds[i]],
                         [0, y[self.channel_thresholds[i] - int(x[0])]], c=ch, linestyle="--")
            plt.xlabel('threshold')
            plt.ylabel('# of hot pixels')
            plt.legend()
            plt.xlim(x[0], x[-1])
            plt.ylim(0)
            plot_path = f"{self.working_path}/{self.plot_path}/{self.name}-hot-pixels.pdf"
            save_plot(plot_path)
            self.callback('save_plot', self.id, f"{self.name}: noise", plot_path)
            plt.close('all')


class MaskNoise(SubAction):
    def __init__(self, noise_mask=constants.DEFAULT_NOISE_MAP_FILENAME,
                 kernel_size=constants.DEFAULT_MN_KERNEL_SIZE,
                 method=constants.INTERPOLATE_MEAN, **kwargs):
        super().__init__(**kwargs)
        self.noise_mask = noise_mask if noise_mask != '' else constants.DEFAULT_NOISE_MAP_FILENAME
        self.kernel_size = kernel_size
        self.ks2 = self.kernel_size // 2
        self.ks2_1 = self.ks2 + 1
        self.method = method
        self.process = None
        self.noise_mask_img = None

    def begin(self, process):
        self.process = process
        path = f"{process.working_path}/{self.noise_mask}"
        if os.path.exists(path):
            self.process.sub_message_r(color_str(
                f': reading noisy pixel mask file: {self.noise_mask}',
                constants.LOG_COLOR_LEVEL_3))
            self.noise_mask_img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if self.noise_mask_img is None:
                raise ImageLoadError(path, f"failed to load image file {self.noise_mask}.")
        else:
            raise ImageLoadError(path, "file not found.")

    def run_frame(self, _idx, _ref_idx, image):
        self.process.sub_message_r(color_str(': mask noisy pixels', constants.LOG_COLOR_LEVEL_3))
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
        if n_noisy_pixels > MAX_NOISY_PIXELS:
            raise RuntimeError(f"Noise map contains too many hot pixels: {n_noisy_pixels}")
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
