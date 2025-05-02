from focus_stack.stack_framework import FrameMultiDirectory, JobBase
from termcolor import colored
import cv2
import numpy as np

class NoiseDetection(FrameMultiDirectory, JobBase):
    def __init__(self, name, input_path=None, output_path=None, working_directory=None, reverse_order=False, channel_thresholds=(15, 15, 15), blur_size = 5):
        FrameMultiDirectory.__init__(self, name, input_path, output_path, working_directory, 1, reverse_order)
        JobBase.__init__(self, name)
        self.channel_thresholds = channel_thresholds
        self.blur_size = blur_size
    def run(self):
        print(colored(self.name, "blue", attrs=["bold"]) + ": detect noisy pixels in folders: " + ", ".join([i for i in self.input_dir]))
        files = self.folder_filelist()
        in_paths = [self.working_directory + "/" + f for f in files]
        print(colored(self.name, "blue", attrs=["bold"]) + ": frames: " + ", ".join([i.split("/")[-1] for i in files]))
        print(colored(self.name, "blue", attrs=["bold"]) + ": reading files")
        first_time = True
        counter = 0
        for path in in_paths:
            print("reading: " + path.split("/")[-1])
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if first_time:
                first_time = False
                mean_img = img.astype(np.float64)
            else:
                mean_img += img
            counter += 1
        mean_img = (mean_img/counter).astype(np.uint8)
        blurred = cv2.GaussianBlur(mean_img, (self.blur_size, self.blur_size), 0)
        diff = cv2.absdiff(mean_img, blurred)
        b, g, r = cv2.split(diff)
        _, hot_r = cv2.threshold(r, self.channel_thresholds[2], 255, cv2.THRESH_BINARY)
        _, hot_g = cv2.threshold(g, self.channel_thresholds[1], 255, cv2.THRESH_BINARY)
        _, hot_b = cv2.threshold(b, self.channel_thresholds[0], 255, cv2.THRESH_BINARY)
        hot_rgb = cv2.bitwise_or(hot_r, cv2.bitwise_or(hot_g, hot_b))
        print("hot pixels, r: {}".format(hot_r[hot_r>0].size))
        print("hot pixels, g: {}".format(hot_g[hot_g>0].size))
        print("hot pixels, b: {}".format(hot_b[hot_b>0].size))
        print("hot pixels, rgb: {}".format(hot_rgb[hot_rgb>0].size))
        cv2.imwrite(self.working_directory + '/' + self.output_path + "/hot_r.png", hot_r)
        cv2.imwrite(self.working_directory + '/' + self.output_path + "/hot_g.png", hot_g)
        cv2.imwrite(self.working_directory + '/' + self.output_path + "/hot_b.png", hot_b)
        cv2.imwrite(self.working_directory + '/' + self.output_path + "/hot_rgb.png", hot_rgb)
