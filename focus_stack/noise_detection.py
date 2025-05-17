from focus_stack.stack_framework import FrameMultiDirectory, JobBase
from focus_stack.utils import save_plot
from termcolor import colored
import cv2
import numpy as np
from tqdm.notebook import tqdm_notebook
import matplotlib.pyplot as plt
import logging

class NoiseDetection(FrameMultiDirectory, JobBase):
    def __init__(self, name="noise-map", input_path=None, output_path=None, working_path=None, plot_path='plots', channel_thresholds=(13, 13, 13), blur_size = 5, file_name= "hot"):
        FrameMultiDirectory.__init__(self, name, input_path, output_path, working_path, plot_path, 1, False)
        JobBase.__init__(self, name)
        self.channel_thresholds = channel_thresholds
        self.blur_size = blur_size
        self.file_name = file_name
    def hot_map(self, ch, th):
        return cv2.threshold(ch, th, 255, cv2.THRESH_BINARY)[1]
    def run_core(self):
        self.print_message('')
        self.print_message(colored(": map noisy pixels, frames in " + self.folder_list_str(), "blue"))
        files = self.folder_filelist()
        in_paths = [self.working_path + "/" + f for f in files]
        mean_img = None
        bar = tqdm_notebook(desc=self.name, total=len(in_paths))
        for path in in_paths:
            self.print_message(colored("reading frame: " + path.split("/")[-1], "blue"), end='\r')
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if mean_img is None: mean_img = img.astype(np.float64)
            else: mean_img += img
            bar.update(1)
        bar.close()
        mean_img = (mean_img/len(in_paths)).astype(np.uint8)
        blurred = cv2.GaussianBlur(mean_img, (self.blur_size, self.blur_size), 0)
        diff = cv2.absdiff(mean_img, blurred)
        channels = cv2.split(diff)
        hot_px = [self.hot_map(ch, self.channel_thresholds[i]) for i, ch in enumerate(channels)]
        hot_rgb = cv2.bitwise_or(hot_px[0], cv2.bitwise_or(hot_px[1], hot_px[2]))
        for ch, hot in zip(['r', 'g', 'b', 'rgb'], hot_px + [hot_rgb]):
            self.print_message("hot pixels, {}: {}".format(ch, np.count_nonzero(hot > 0)))
            cv2.imwrite(self.working_path + '/' + self.output_path + "/" + self.file_name + "-" + ch + ".png", hot)
        th_range = range(5, 30)
        plt.figure(figsize=(10, 5))
        x = np.array(list(th_range))
        ys = [[np.count_nonzero(self.hot_map(ch, th) > 0) for th in th_range] for ch in channels]
        for i, ch, y in zip(range(3), ['r', 'g', 'b'], ys):
            plt.plot(x, y, c=ch, label=ch)
            plt.plot([self.channel_thresholds[i], self.channel_thresholds[i]], [0, y[self.channel_thresholds[i] - int(x[0])]], c=ch, linestyle="--")
        plt.xlabel('threshold')
        plt.ylabel('# of hot pixels')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(0)
        save_plot(self.plot_path + "/" + self.name + "-hot-pixels.pdf")
        
MEAN = 'MEAN'
MEDIAN = 'MEDIAN'

class MaskNoise:
    def __init__(self, noise_mask="noise-map/hot_rgb.png", kernel_size=3, method=MEAN):
        self.noise_mask = noise_mask
        self.kernel_size = kernel_size
        self.method = method
        self.noise_mask = noise_mask
    def begin(self, process):
        self.process = process
        self.noise_mask =  cv2.imread(process.working_path + "/" + self.noise_mask, cv2.IMREAD_GRAYSCALE)
    def end(self):
        pass
    def run_frame(self, idx, ref_idx, image):
        self.process.sub_message('- mask noisy pixels', end='\r')
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
                max(0, y - self.kernel_size//2):min(channel.shape[0], y + self.kernel_size//2 + 1),
                max(0, x - self.kernel_size//2):min(channel.shape[1], x + self.kernel_size//2 + 1)
            ]        
            valid_pixels = neighborhood[neighborhood != 0]
            if len(valid_pixels) > 0:
                if self.method == MEAN:
                    corrected[y, x] = np.mean(valid_pixels)
                elif self.method == MEDIAN:
                    corrected[y, x] = np.median(valid_pixels)
        return corrected
