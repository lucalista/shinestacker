import numpy as np
import cv2
import matplotlib.pyplot as plt
from scipy.optimize import bisect
from focus_stack.utils import read_img, write_img, img_8bit
from focus_stack.stack_framework import *
from termcolor import colored, cprint

# Issues:
#
# LUT as an issue with 16 bits images
# 16 bit masks have an ussue
#

def gamma_lut(gamma, dtype):
    gamma_inv = 1.0/gamma
    two_n = 256 if dtype == np.uint8 else 65536
    two_n_1 = 255 if dtype == np.uint8 else 65535
    return (((np.arange(0, two_n) / two_n_1) ** gamma_inv) * two_n_1).astype(dtype)

def adjust_gamma(image, gamma):
    lut =  gamma_lut(gamma, image.dtype)
    if image.dtype==np.uint8: image_adj = cv2.LUT(image, lut)
    else: image_adj = np.take(lut, image)
    return image_adj;
    
def adjust_gamma_ch3(image, gamma, ch_range):
    chans = cv2.split(image)
    ch_out = []
    for c in range(3):
        if c in ch_range:
            lut = gamma_lut(gamma[c], image.dtype)
            if image.dtype==np.uint8: image_adj = cv2.LUT(chans[c], lut)
            else: image_adj = np.take(lut, image)
        else:
            image_adj = chans[c]
        ch_out.append(image_adj)
    return cv2.merge(ch_out)

def lumi_expect(hist, gamma, dtype, i_min, i_max):
    if i_max == -1: i_max = 255 if dtype==np.uint8 else 65535
    return np.average(gamma_lut(gamma, dtype)[i_min:i_max+1], weights=hist.flatten()[i_min:i_max+1])

def lumi_mask(image, mask_size):
    two_n_1 = 255 if image.dtype == np.uint8 else 65535
    if mask_size > 0:
        height, width, channels = image.shape
        mask = np.zeros(image.shape[:2], dtype=image.dtype)
        cv2.circle(mask, (width//2, height//2), int(min(width, height)*mask_size/2),  (two_n_1, two_n_1, two_n_1), -1)
    else:
        mask = None
    return mask

def histo_plot(ax, histo, x_label, color, two_n):
    ax.set_ylabel("# of Pixels")
    ax.set_xlabel(x_label)
    ax.set_xlim([0, two_n])
    ax.set_yscale('log')
    ax.plot(histo, color=color)

class BalanceLayers(FramesRefActions):
    def __init__(self, name, input_path=None, output_path=None, working_directory=None, ref_idx=-1, mask_size=-1, i_min=0, i_max=-1, plot_histograms=False):
        FramesRefActions.__init__(self, name, input_path, output_path, working_directory, ref_idx, step_process=False)
        self.mask_size = mask_size
        self.i_min = i_min
        self.i_max = i_max
        self.plot_histograms = plot_histograms
    def run_frame(self, idx, ref_idx):
        print("balancing frame: {}, file: {}                    ".format(self.count, idx, self.filenames[idx]), end='\r')
        self.balance(idx)
    def begin(self):
        FramesRefActions.begin(self)
        self.image_ref = self.preprocess(read_img(self.input_dir + "/" + self.filenames[self.ref_idx]))
        self.mean_ref, self.hist_ref = self.get_histos(self.image_ref)
    def end(self):
        print("                                 ")
    def balance(self, idx):
        image = read_img(self.input_dir + "/" + self.filenames[idx])
        if(idx != self.ref_idx):
            image = self.preprocess(image)
            image = self.adjust_gamma(image)
            image = self.postprocess(image)
        write_img(self.output_dir + "/" + self.filenames[idx], image)
    def preprocess(self, image):
        return image
    def postprocess(self, image):
        return image
    def get_histos(self, image):
        assert(False), 'abstract method'
    def adjust_gamma(self, image):
        assert(False), 'abstract method'
    
class BalanceLayersLumi(BalanceLayers):
    def __init__(self, name, input_path=None, output_path=None, working_directory=None, ref_idx=-1, mask_size=-1, i_min=0, i_max=-1, plot_histograms=False):
        BalanceLayers.__init__(self, name, input_path, output_path, working_directory, ref_idx, mask_size, i_min, i_max, plot_histograms)
    def get_histos(self, image):
        two_n = 256 if image.dtype == np.uint8 else 65536
        mask = lumi_mask(image, self.mask_size)
        hist_lumi = cv2.calcHist([cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)], [0], mask, [two_n], [0, two_n])
        if self.plot_histograms:
            chans = cv2.split(image)
            colors = ("r", "g", "b")
            fig, axs = plt.subplots(1, 2, figsize=(6, 2), sharey=True)
            histo_plot(axs[0], hist_lumi, "pixel luminosity", 'black', two_n)
            for (chan, color) in zip(chans, colors):
                hist_col = cv2.calcHist([chan], [0], mask, [two_n], [0, two_n])
                histo_plot(axs[1], hist_col, "r,g,b luminosity", color, two_n)
            plt.show()
        i_end = self.i_max + 1 if self.i_max >=0 else 65536 
        mean_lumi = np.average(list(range(two_n))[self.i_min:i_end], weights=hist_lumi.flatten()[self.i_min:i_end])
        return mean_lumi, hist_lumi
    def adjust_gamma(self, image):
        mean, hist = self.get_histos(image)
        f = lambda x: lumi_expect(hist, x, image.dtype, self.i_min, self.i_max) - self.mean_ref
        gamma = bisect(f, 0.1, 5)
        self.gamma[self.count - 1] = gamma
        return adjust_gamma(image, gamma)
    def begin(self):
        BalanceLayers.begin(self)
        self.gamma = np.ones(self.counts)
    def end(self):
        BalanceLayers.end(self)
        plt.figure(figsize=(10, 5))
        x = np.arange(1, len(self.gamma) + 1, dtype=int)
        y = self.gamma
        plt.plot([self.ref_idx + 1, self.ref_idx + 1], [0, 1], color='cornflowerblue', linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--', label='no correction')
        plt.plot(x, y, color='navy', label='luminosity gamma correction')
        plt.xlabel('frame')
        plt.ylabel('gamma correction')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(0)
        plt.show()
        
class BalanceLayersRGB(BalanceLayers):
    def __init__(self, name, input_path=None, output_path=None, working_directory=None, ref_idx=-1, mask_size=-1, i_min=0, i_max=-1, plot_histograms=False):
        BalanceLayers.__init__(self, name, input_path, output_path, working_directory, ref_idx, mask_size, i_min, i_max, plot_histograms)
    def get_histos(self, image):
        two_n = 256 if image.dtype == np.uint8 else 65536
        mask = lumi_mask(image, self.mask_size)
        hist = []
        mean = []
        chans = cv2.split(image)
        colors = ("r", "g", "b")
        for (chan, color) in zip(chans, colors):
            hist.append(cv2.calcHist([chan], [0], mask, [two_n], [0, two_n]))
            i_end = self.i_max + 1 if self.i_max >=0 else 65536 
            mean.append(np.average(list(range(two_n))[self.i_min:i_end], weights=hist[-1].flatten()[self.i_min:i_end]))
        if self.plot_histograms:
            fig, axs = plt.subplots(1, 3, figsize=(6, 2), sharey=True)
            for c in [2, 1, 0]:
                histo_plot(axs[c], hist[c], colors[c] + " luminosity", colors[c], two_n)
            plt.show()
        return mean, hist
    def adjust_gamma(self, image):
        mean, hist = self.get_histos(image)
        gamma = []
        ch_range = [0, 1, 2]
        i_end = self.i_max + 1 if self.i_max >=0 else 65536 
        for c in range(3):
            f = lambda x: lumi_expect(hist[c], x, image.dtype, self.i_min,i_end) - self.mean_ref[c]
            gamma.append(bisect(f, 0.1, 5))
        self.gamma[self.count - 1] = gamma
        return adjust_gamma_ch3(image, gamma, ch_range)
    def begin(self):
        BalanceLayers.begin(self)
        self.gamma = np.ones((self.counts, 3))
    def end(self):
        BalanceLayers.end(self)
        plt.figure(figsize=(10, 5))
        x = np.arange(1, len(self.gamma) + 1, dtype=int)
        y = self.gamma
        plt.plot([self.ref_idx + 1, self.ref_idx + 1], [0, 1], color='cornflowerblue', linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--', label='no correction')
        plt.plot(x, y[:, 0], color='r', label='R gamma correction')
        plt.plot(x, y[:, 1], color='g', label='G gamma correction')
        plt.plot(x, y[:, 2], color='b', label='B gamma correction')
        plt.xlabel('frame')
        plt.ylabel('gamma correction')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(0)
        plt.show()
    
class BalanceLayersCh2(BalanceLayers):
    def __init__(self, name, input_path=None, output_path=None, working_directory=None, ref_idx=-1, mask_size=-1, i_min=0, i_max=-1, plot_histograms=False):
        BalanceLayers.__init__(self, name, input_path, output_path, working_directory, ref_idx, mask_size, i_min, i_max, plot_histograms)
    def preprocess(self, image):
        assert(False), 'abstract method'
    def get_labels(self):
        assert(False), 'abstract method'
    def get_histos(self, image):
        two_n = 256 if image.dtype == np.uint8 else 65536
        mask = lumi_mask(image, self.mask_size)
        hist = []
        mean = []
        chans = cv2.split(image)
        i_end = self.i_max + 1 if self.i_max >=0 else 65536 
        for (chan, color) in zip(chans, self.colors):
            hist.append(cv2.calcHist([chan], [0], mask, [two_n], [0, two_n]))
            mean.append(np.average(list(range(two_n))[self.i_min:i_end], weights=hist[-1].flatten()[self.i_min:i_end1]))
        if self.plot_histograms:
            fig, axs = plt.subplots(1, 3, figsize=(6, 2), sharey=True)
            for c in range(3):
                histo_plot(axs[c], hist[c], self.labels[c], colors[c], two_n)
            plt.show()
        return mean, hist
    def adjust_gamma(self, image):
        mean, hist = self.get_histos(image)
        gamma = [1, 1, 1]
        ch_range = [1, 2]
        for c in ch_range:
            f = lambda x: lumi_expect(hist[c], x, image.dtype, self. i_min, self.i_max) - self.mean_ref[c]
            gamma[c] = bisect(f, 0.1, 5)
        self.gamma[self.count - 1] = gamma[1:]
        return adjust_gamma_ch3(image, gamma, ch_range)
    def begin(self):
        BalanceLayers.begin(self)
        self.gamma = np.ones((self.counts, 2))
    def end(self):
        BalanceLayers.end(self)
        plt.figure(figsize=(10, 5))
        x = np.arange(1, len(self.gamma) + 1, dtype=int)
        y = self.gamma
        plt.plot([self.ref_idx + 1, self.ref_idx + 1], [0, 1], color='cornflowerblue', linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--', label='no correction')
        plt.plot(x, y[:, 0], color=self.colors[1], label=self.labels[1] + ' gamma correction')
        plt.plot(x, y[:, 1], color=self.colors[2], label=self.labels[2] + ' gamma correction')
        plt.xlabel('frame')
        plt.ylabel('gamma correction')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(0)
        plt.show()
        
class BalanceLayersSV(BalanceLayersCh2):
    def __init__(self, name, input_path=None, output_path=None, working_directory=None, ref_idx=-1, mask_size=-1, i_min=0, i_max=-1, plot_histograms=False):
        BalanceLayersCh2.__init__(self, name, input_path, output_path, working_directory, ref_idx, mask_size, i_min, i_max, plot_histograms)
        self.labels = ("H", "S", "V")
        self.colors = ("hotpink", "forestgreen", "navy")
    def preprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    def postprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_HSV2BGR)
    
class BalanceLayersLS(BalanceLayersCh2):
    def __init__(self, name, input_path=None, output_path=None, working_directory=None, ref_idx=-1, mask_size=-1, i_min=0, i_max=-1, plot_histograms=False):
        BalanceLayersCh2.__init__(self, name, input_path, output_path, working_directory, ref_idx, mask_size, i_min, i_max, plot_histograms)
        self.labels = ("H", "L", "S")
        self.colors = ("hotpink", "navy", "forestgreen")
    def preprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_BGR2HLS)
    def postprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_HLS2BGR)