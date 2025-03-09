import numpy as np
import cv2
import math
import matplotlib.pyplot as plt
from scipy.optimize import bisect
from focus_stack.utils import read_img, write_img, img_8bit
from focus_stack.stack_framework import *
from termcolor import colored, cprint

default_img_scale = 8

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
            else: image_adj = np.take(lut, chans[c])
        else:
            image_adj = chans[c]
        ch_out.append(image_adj)
    return cv2.merge(ch_out)

def histo_plot(ax, histo, x_label, color, two_n):
    ax.set_ylabel("# of Pixels")
    ax.set_xlabel(x_label)
    ax.set_xlim([0, two_n])
    ax.set_yscale('log')
    ax.plot(histo, color=color)

class BalanceLayers:
    def __init__(self, mask_size=None, i_min=0, i_max=-1, img_scale=default_img_scale, plot_histograms=False):
        self.mask_size = mask_size
        self.i_min = i_min
        self.i_max = i_max
        self.i_end = self.i_max + 1 if self.i_max >=0 else 65536
        self.plot_histograms = plot_histograms
        self.img_scale = img_scale
    def begin(self, process):
        self.process = process
        self.image_ref = self.preprocess(read_img(self.process.input_dir + "/" + self.process.filenames[process.ref_idx]))
        self.mean_ref, self.hist_ref = self.get_histos(self.image_ref)
    def end(self):
        self.process.print_message('                                                                                 ')
    def run_frame(self, idx, ref_idx, image):
        if(idx != self.process.ref_idx):
            self.process.sub_message(colored('- preprocess image    ', 'light_blue'), end='\r')
            image = self.preprocess(image)
            self.process.sub_message(colored('- balance image     ', 'light_blue'), end='\r')
            image = self.adjust_gamma(image, idx)
            self.process.sub_message(colored('- postprocess image      ', 'light_blue'), end='\r')
            image = self.postprocess(image)
        return image
    def preprocess(self, image):
        return image
    def postprocess(self, image):
        return image
    def get_histos(self, image):
        assert(False), 'abstract method'
    def adjust_gamma(self, image, idx):
        assert(False), 'abstract method'
    def lumi_expect(self, hist, gamma, dtype):
        return np.average(gamma_lut(gamma, dtype)[self.i_min:self.i_end], weights=hist.flatten()[self.i_min:self.i_end])
    def calc_hist_1ch(self, image):
        two_n = 256 if image.dtype == np.uint8 else 65536
        if self.mask_size is None:
            image_sel = image
        else:
            height, width = image.shape[:2]
            xv, yv = np.meshgrid(np.linspace(0, width - 1, width), np.linspace(0, height - 1, height))
            image_sel = image[(xv - width//2)**2 + (yv - height//2)**2 <= (min(width, height)*self.mask_size/2)**2]
        hist, bins = np.histogram((image_sel if self.img_scale==1 else image_sel[::self.img_scale][::self.img_scale]), bins=np.linspace(-0.5, two_n - 0.5, two_n + 1))
        return hist
    def calc_hist_rgb(self, image):
        return self.calc_hist_1ch(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))

class BalanceLayersLumi(BalanceLayers):
    def __init__(self, mask_size=-1, i_min=0, i_max=-1, img_scale=default_img_scale, plot_histograms=False):
        BalanceLayers.__init__(self, mask_size, i_min, i_max, img_scale, plot_histograms)
    def get_histos(self, image):
        two_n = 256 if image.dtype == np.uint8 else 65536
        hist_lumi = self.calc_hist_rgb(image)
        if self.plot_histograms:
            chans = cv2.split(image)
            colors = ("r", "g", "b")
            fig, axs = plt.subplots(1, 2, figsize=(6, 2), sharey=True)
            histo_plot(axs[0], hist_lumi, "pixel luminosity", 'black', two_n)
            for (chan, color) in zip(chans, colors):
                hist_col = self.calc_hist_1ch(chan)
                histo_plot(axs[1], hist_col, "r,g,b luminosity", color, two_n)
            plt.show()
        mean_lumi = np.average(list(range(two_n))[self.i_min:self.i_end], weights=hist_lumi.flatten()[self.i_min:self.i_end])
        return mean_lumi, hist_lumi
    def adjust_gamma(self, image, idx):
        mean, hist = self.get_histos(image)
        f = lambda x: self.lumi_expect(hist, x, image.dtype) - self.mean_ref
        gamma = bisect(f, 0.1, 5)
        self.gamma[idx] = gamma
        return adjust_gamma(image, gamma)
    def begin(self, process):
        BalanceLayers.begin(self, process)
        self.gamma = np.ones(self.process.counts)
    def end(self):
        BalanceLayers.end(self)
        plt.figure(figsize=(10, 5))
        x = np.arange(1, len(self.gamma) + 1, dtype=int)
        y = self.gamma
        plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1], [0, 1], color='cornflowerblue', linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--', label='no correction')
        plt.plot(x, y, color='navy', label='luminosity gamma correction')
        plt.xlabel('frame')
        plt.ylabel('gamma correction')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(0)
        plt.show()

class BalanceLayersRGB(BalanceLayers):
    def __init__(self, mask_size=None, i_min=0, i_max=-1, img_scale=default_img_scale, plot_histograms=False):
        BalanceLayers.__init__(self, mask_size, i_min, i_max, img_scale, plot_histograms)
    def get_histos(self, image):
        two_n = 256 if image.dtype == np.uint8 else 65536
        hist = []
        mean = []
        chans = cv2.split(image)
        colors = ("r", "g", "b")
        for (chan, color) in zip(chans, colors):
            hist.append(self.calc_hist_1ch(chan))
            mean.append(np.average(list(range(two_n))[self.i_min:self.i_end], weights=hist[-1].flatten()[self.i_min:self.i_end]))
        if self.plot_histograms:
            fig, axs = plt.subplots(1, 3, figsize=(6, 2), sharey=True)
            for c in [2, 1, 0]:
                histo_plot(axs[c], hist[c], colors[c] + " luminosity", colors[c], two_n)
            plt.show()
        return mean, hist
    def adjust_gamma(self, image, idx):
        mean, hist = self.get_histos(image)
        gamma = []
        ch_range = [0, 1, 2]
        for c in range(3):
            f = lambda x: self.lumi_expect(hist[c], x, image.dtype) - self.mean_ref[c]
            gamma.append(bisect(f, 0.1, 5))
        self.gamma[idx] = gamma
        return adjust_gamma_ch3(image, gamma, ch_range)
    def begin(self, process):
        BalanceLayers.begin(self, process)
        self.gamma = np.ones((self.process.counts, 3))
    def end(self):
        BalanceLayers.end(self)
        plt.figure(figsize=(10, 5))
        x = np.arange(1, len(self.gamma) + 1, dtype=int)
        y = self.gamma
        plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1], [0, 1], color='cornflowerblue', linestyle='--', label='reference frame')
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
    def __init__(self, mask_size=None, i_min=0, i_max=-1, img_scale=default_img_scale, plot_histograms=False):
        BalanceLayers.__init__(self, mask_size, i_min, i_max, img_scale, plot_histograms)
    def preprocess(self, image):
        assert(False), 'abstract method'
    def get_labels(self):
        assert(False), 'abstract method'
    def get_histos(self, image):
        two_n = 256 if image.dtype == np.uint8 else 65536
        hist = []
        mean = []
        chans = cv2.split(image)
        for (chan, color) in zip(chans, self.colors):
            hist.append(self.calc_hist_1ch(chan))
            mean.append(np.average(list(range(two_n))[self.i_min:self.i_end], weights=hist[-1].flatten()[self.i_min:self.i_end]))
        if self.plot_histograms:
            fig, axs = plt.subplots(1, 3, figsize=(6, 2), sharey=True)
            for c in range(3):
                histo_plot(axs[c], hist[c], self.labels[c], colors[c], two_n)
            plt.show()
        return mean, hist
    def adjust_gamma(self, image, idx):
        mean, hist = self.get_histos(image)
        gamma = [1, 1, 1]
        ch_range = [1, 2]
        for c in ch_range:
            f = lambda x: self.lumi_expect(hist[c], x, image.dtype) - self.mean_ref[c]
            gamma[c] = bisect(f, 0.1, 5)
        self.gamma[idx] = gamma[1:]
        return adjust_gamma_ch3(image, gamma, ch_range)
    def begin(self, process):
        BalanceLayers.begin(self, process)
        self.gamma = np.ones((process.counts, 2))
    def end(self):
        BalanceLayers.end(self)
        plt.figure(figsize=(10, 5))
        x = np.arange(1, len(self.gamma) + 1, dtype=int)
        y = self.gamma
        plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1], [0, 1], color='cornflowerblue', linestyle='--', label='reference frame')
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
    def __init__(self, mask_size=None, i_min=0, i_max=-1, img_scale=default_img_scale, plot_histograms=False):
        BalanceLayersCh2.__init__(self, mask_size, i_min, i_max, img_scale, plot_histograms)
        self.labels = ("H", "S", "V")
        self.colors = ("hotpink", "forestgreen", "navy")
    def preprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    def postprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_HSV2BGR)
    
class BalanceLayersLS(BalanceLayersCh2):
    def __init__(self, mask_size=None, i_min=0, i_max=-1, img_scale=default_img_scale, plot_histograms=False):
        BalanceLayersCh2.__init__(self,mask_size, i_min, i_max, img_scale, plot_histograms)
        self.labels = ("H", "L", "S")
        self.colors = ("hotpink", "navy", "forestgreen")
    def preprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_BGR2HLS)
    def postprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_HLS2BGR)