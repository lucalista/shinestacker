from config.config import config
from focus_stack.framework import JobBase
from focus_stack.stack_framework import FrameMultiDirectory, SubAction
from focus_stack.utils import read_img, save_plot, make_tqdm_bar, get_img_metadata, validate_image
from focus_stack.exceptions import ImageLoadError
from termcolor import colored
import cv2
import numpy as np
import matplotlib.pyplot as plt
import logging
import os
import errno


_DEFAULT_NOISE_MAP_FILENAME = "noise-map/hot_pixels.png"
INTERPOLATE_MEAN = 'MEAN'
INTERPOLATE_MEDIAN = 'MEDIAN'

_VALID_INTERPOLATE = {INTERPOLATE_MEAN, INTERPOLATE_MEDIAN}


def mean_image(file_paths, message_callback=None, progress_callback=None):
    mean_img = None
    for path in file_paths:
        if message_callback:
            message_callback(path)
        if not os.path.exists(path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        try:
            img = read_img(path)
        except Exception:
            logger = logging.getLogger(__name__)
            logger.error("Can't open file: " + path)
        if mean_img is None:
            metadata = get_img_metadata(img)
            mean_img = img.astype(np.float64)
        else:
            validate_image(img, *metadata)
            mean_img += img
        if progress_callback:
            progress_callback()
    return (mean_img / len(file_paths)).astype(np.uint8)


class NoiseDetection(FrameMultiDirectory, JobBase):
    def __init__(self, name="noise-map", enabled=True, plot_histograms=False, channel_thresholds=(13, 13, 13),
                 blur_size=5, file_name='', plot_range=(5, 30), **kwargs):
        FrameMultiDirectory.__init__(self, name, **kwargs)
        JobBase.__init__(self, name, enabled)
        self.channel_thresholds = channel_thresholds
        self.blur_size = blur_size
        self.file_name = file_name if file_name != '' else _DEFAULT_NOISE_MAP_FILENAME
        self.plot_range = plot_range
        self.plot_histograms = plot_histograms

    def hot_map(self, ch, th):
        return cv2.threshold(ch, th, 255, cv2.THRESH_BINARY)[1]

    def run_core(self):
        self.print_message(colored("map noisy pixels from frames in " + self.folder_list_str(), "blue"))
        files = self.folder_filelist()
        in_paths = [self.working_path + "/" + f for f in files]
        if not config.DISABLE_TQDM:
            bar = make_tqdm_bar(self.name, len(in_paths))
            mean_img = mean_image(
                file_paths=in_paths,
                message_callback=lambda path: self.print_message_r(colored(f"reading frame: {path.split('/')[-1]}", "blue")),
                progress_callback=lambda: bar.update(1),
            )
            bar.close()
        else:
            mean_img = mean_image(
                file_paths=in_paths,
                message_callback=lambda path: self.print_message_r(colored(f"reading frame: {path.split('/')[-1]}", "blue")),
            )
        blurred = cv2.GaussianBlur(mean_img, (self.blur_size, self.blur_size), 0)
        diff = cv2.absdiff(mean_img, blurred)
        channels = cv2.split(diff)
        hot_px = [self.hot_map(ch, self.channel_thresholds[i]) for i, ch in enumerate(channels)]
        hot_rgb = cv2.bitwise_or(hot_px[0], cv2.bitwise_or(hot_px[1], hot_px[2]))
        msg = []
        for ch, hot in zip(['rgb', 'r', 'g', 'b', ], [hot_rgb] + hot_px):
            msg.append("{}: {}".format(ch, np.count_nonzero(hot > 0)))
        self.print_message("hot pixels: " + ", ".join(msg))
        path = "/".join(self.file_name.split("/")[:-1])
        if not os.path.exists(self.working_path + '/' + path):
            self.print_message("create directory: " + path)
            os.mkdir(self.working_path + '/' + path)
        self.print_message("writing hot pixels map file: " + self.file_name)
        cv2.imwrite(self.working_path + '/' + self.file_name, hot)
        th_range = range(*self.plot_range)
        if self.plot_histograms:
            plt.figure(figsize=(10, 5))
            x = np.array(list(th_range))
            ys = [[np.count_nonzero(self.hot_map(ch, th) > 0) for th in th_range] for ch in channels]
            for i, ch, y in zip(range(3), ['r', 'g', 'b'], ys):
                plt.plot(x, y, c=ch, label=ch)
                plt.plot([self.channel_thresholds[i], self.channel_thresholds[i]],
                         [0, y[self.channel_thresholds[i] - int(x[0])]], c=ch, linestyle="--")
            plt.xlabel('threshold')
            plt.ylabel('# of hot pixels')
            plt.legend()
            plt.xlim(x[0], x[-1])
            plt.ylim(0)
            save_plot(self.working_path + "/" + self.plot_path + "/" + self.name + "-hot-pixels.pdf")
            plt.close('all')


class MaskNoise(SubAction):
    def __init__(self, noise_mask=_DEFAULT_NOISE_MAP_FILENAME, kernel_size=3, method=INTERPOLATE_MEAN, **kwargs):
        super().__init__(**kwargs)
        self.noise_mask = noise_mask
        self.kernel_size = kernel_size
        self.ks2 = self.kernel_size // 2
        self.ks2_1 = self.ks2 + 1
        self.method = method
        self.noise_mask = noise_mask

    def begin(self, process):
        self.process = process
        path = process.working_path + "/" + self.noise_mask
        if os.path.exists(path):
            self.noise_mask = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        else:
            raise ImageLoadError(path, "file not found.")

    def end(self):
        pass

    def run_frame(self, idx, ref_idx, image):
        self.process.sub_message_r(': mask noisy pixels')
        if len(image.shape) == 3:
            corrected = image.copy()
            for c in range(3):
                corrected[:, :, c] = self.correct_channel(image[:, :, c])
        else:
            corrected = self.correct_channel(image)
        return corrected

    def correct_channel(self, channel):
        corrected = channel.copy()
        noise_coords = np.argwhere(self.noise_mask > 0)
        for y, x in noise_coords:
            neighborhood = channel[
                max(0, y - self.ks2):min(channel.shape[0], y + self.ks2_1),
                max(0, x - self.ks2):min(channel.shape[1], x + self.ks2_1)
            ]
            valid_pixels = neighborhood[neighborhood != 0]
            if len(valid_pixels) > 0:
                if self.method == INTERPOLATE_MEAN:
                    corrected[y, x] = np.mean(valid_pixels)
                elif self.method == INTERPOLATE_MEDIAN:
                    corrected[y, x] = np.median(valid_pixels)
        return corrected
