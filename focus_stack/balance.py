import numpy as np
import cv2
import math
import matplotlib.pyplot as plt
from scipy.optimize import bisect
from focus_stack.utils import read_img, write_img, img_8bit
from focus_stack.stack_framework import *

class CorrectionMap:
    def __init__(self, dtype, ref_hist, i_min=0, i_max=-1):
        self.dtype = dtype
        self.two_n = 256 if dtype == np.uint8 else 65536
        self.i_min = i_min
        self.i_end = i_max + 1 if i_max >=0 else self.two_n
        self.channels = len(ref_hist) 
        self.id_lut = list(range(self.two_n))
        self.reference = [self.mid_val(self.id_lut, h) for h in ref_hist]
    def mid_val(self, lut, h):
        return np.average(lut[self.i_min:self.i_end], weights=h.flatten()[self.i_min:self.i_end])
    def apply_lut(self, correction, img):
        lut = self.lut(correction)
        return cv2.LUT(img, lut) if self.dtype==np.uint8 else np.take(lut, img)
    def adjust(self, image, correction):
        if self.channels == 1:
            return self.apply_lut(correction[0], image)
        else:
            chans = cv2.split(image)
            if self.channels == 2:
                ch_out = [chans[0]] + [self.apply_lut(correction[c - 1], chans[c]) for c in range(1, 3)]
            elif self.channels == 3:
                ch_out = [self.apply_lut(correction[c], chans[c]) for c in range(3)]
            return cv2.merge(ch_out)

class GammaMap(CorrectionMap):
    def __init__(self, dtype, ref_hist, i_min=0, i_max=-1):
        CorrectionMap.__init__(self, dtype, ref_hist, i_min, i_max)
        self.two_n_1 = self.two_n - 1
    def correction(self, hist):
        return [bisect(lambda x: self.mid_val(self.lut(x), h) - r, 0.1, 5) for h, r in zip(hist, self.reference)]
    def lut(self, gamma):
        gamma_inv = 1.0/gamma
        return (((np.arange(0, self.two_n) / self.two_n_1) ** gamma_inv) * self.two_n_1).astype(self.dtype)   

class LinearMap(CorrectionMap):
    def __init__(self, dtype, ref_hist, i_min=0, i_max=-1):
        CorrectionMap.__init__(self, dtype, ref_hist, i_min, i_max)
    def lut(self, scale):
        return (np.arange(0, self.two_n) * scale).astype(self.dtype)
    def correction(self, hist):
        return [r/self.mid_val(self.id_lut, h) for h, r in zip(hist, self.reference)]

LINEAR = "LINEAR"
GAMMA = "GAMMA"
default_img_scale = 8

class Correction:
    def __init__(self, channels, mask_size=None, i_min=0, i_max=-1, img_scale=default_img_scale, corr_map=LINEAR, plot_histograms=False):
        self.mask_size = mask_size
        self.i_min = i_min
        self.i_max = i_max
        self.plot_histograms = plot_histograms
        self.img_scale = img_scale
        self.corr_map = corr_map
        self.channels = channels
    def begin(self, ref_image, size):
        self.dtype = ref_image.dtype
        self.two_n = 256 if ref_image.dtype == np.uint8 else 65536
        hist = self.get_hist(self.preprocess(ref_image))
        if self.corr_map == LINEAR:
            self.corr_map = LinearMap(self.dtype, hist, self.i_min, self.i_max)
        elif self.corr_map == GAMMA:
            self.corr_map = GammaMap(self.dtype, hist, self.i_min, self.i_max)
        else:
            raise Exception("Invalid correction map type: " + self.corr_map)
        self.corrections = np.ones((size, self.channels))
    def calc_hist_1ch(self, image):
        if self.mask_size is None:
            image_sel = image
        else:
            height, width = image.shape[:2]
            xv, yv = np.meshgrid(np.linspace(0, width - 1, width), np.linspace(0, height - 1, height))
            image_sel = image[(xv - width//2)**2 + (yv - height//2)**2 <= (min(width, height)*self.mask_size/2)**2]
        hist, bins = np.histogram((image_sel if self.img_scale==1 else image_sel[::self.img_scale][::self.img_scale]), bins=np.linspace(-0.5, self.two_n - 0.5, self.two_n + 1))
        return hist
    def correction(self, hist):
        return bisect(lambda x: self.lumi_expect(hist, x, self.dtype) - self.reference, 0.1, 5)
    def balance(self, image):
        correction = self.corr_map.correction(self.get_hist(image))
        return correction, self.corr_map.adjust(image, correction)
    def get_hist(self, image):
        assert(False), 'abstract method'
    def end(self):
        assert(False), 'abstract method'
    def process(self, idx, image):
        image = self.preprocess(image)
        correction, image = self.balance(image)
        image = self.postprocess(image)
        self.corrections[idx] = correction
        return image
    def preprocess(self, image):
        return image
    def postprocess(self, image):
        return image
    def histo_plot(self, ax, hist, x_label, color, alpha=1):
        ax.set_ylabel("# of Pixels")
        ax.set_xlabel(x_label)
        ax.set_xlim([0, self.two_n])
        ax.set_yscale('log')
        ax.plot(hist, color=color, alpha=alpha)
    
class LumiCorrection(Correction):
    def __init__(self, mask_size=None, i_min=0, i_max=-1, img_scale=default_img_scale, corr_map=LINEAR, plot_histograms=False):
        Correction.__init__(self, 1, mask_size, i_min, i_max, img_scale, corr_map, plot_histograms)
    def get_hist(self, image):
        if self.dtype != image.dtype: raise Exception("Images must be all of 8 bit or 16 bit")
        hist = self.calc_hist_1ch(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        if self.plot_histograms:
            chans = cv2.split(image)
            colors = ("r", "g", "b")
            fig, axs = plt.subplots(1, 2, figsize=(6, 2), sharey=True)
            self.histo_plot(axs[0], hist, "pixel luminosity", 'black')
            for (chan, color) in zip(chans, colors):
                hist_col = self.calc_hist_1ch(chan)
                self.histo_plot(axs[1], hist_col, "r,g,b luminosity", color, alpha=0.5)
            plt.xlim(0, self.two_n)
            plt.show()
        return [hist]
    def end(self, ref_idx):
        plt.figure(figsize=(10, 5))
        x = np.arange(1, len(self.corrections) + 1, dtype=int)
        y = self.corrections
        plt.plot([ref_idx + 1, ref_idx + 1], [0, 1], color='cornflowerblue', linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--', label='no correction')
        plt.plot(x, y, color='navy', label='luminosity correction')
        plt.xlabel('frame')
        plt.ylabel('correction')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(0)
        plt.show()

class RGBCorrection(Correction):
    def __init__(self, mask_size=None, i_min=0, i_max=-1, img_scale=default_img_scale, corr_map=LINEAR, plot_histograms=False):
        Correction.__init__(self, 3, mask_size, i_min, i_max, img_scale, corr_map, plot_histograms)
    def get_hist(self, image):
        if self.dtype != image.dtype: raise Exception("Images must be all of 8 bit or 16 bit")
        hist = [self.calc_hist_1ch(chan) for chan in cv2.split(image)]
        colors = ("r", "g", "b")
        if self.plot_histograms:
            fig, axs = plt.subplots(1, 3, figsize=(6, 2), sharey=True)
            for c in [2, 1, 0]:
                self.histo_plot(axs[c], hist[c], colors[c] + " luminosity", colors[c])
            plt.xlim(0, self.two_n)
            plt.show()
        return hist
    def end(self, ref_idx):
        plt.figure(figsize=(10, 5))
        x = np.arange(1, len(self.corrections) + 1, dtype=int)
        y = self.corrections
        plt.plot([ref_idx + 1, ref_idx + 1], [0, 1], color='cornflowerblue', linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--', label='no correction')
        plt.plot(x, y[:, 0], color='r', label='R correction')
        plt.plot(x, y[:, 1], color='g', label='G correction')
        plt.plot(x, y[:, 2], color='b', label='B correction')
        plt.xlabel('frame')
        plt.ylabel('correction')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(0)
        plt.show()

class Ch2Correction(Correction):
    def __init__(self, mask_size=None, i_min=0, i_max=-1, img_scale=default_img_scale, corr_map=LINEAR, plot_histograms=False):
        Correction.__init__(self, 2, mask_size, i_min, i_max, img_scale, corr_map, plot_histograms)
    def preprocess(self, image):
        assert(False), 'abstract method'
    def get_labels(self):
        assert(False), 'abstract method'
    def get_hist(self, image):
        if self.dtype != image.dtype: raise Exception("Images must be all of 8 bit or 16 bit")
        hist = [self.calc_hist_1ch(chan) for chan in cv2.split(image)]
        if self.plot_histograms:
            fig, axs = plt.subplots(1, 3, figsize=(6, 2), sharey=True)
            for c in range(3):
                self.histo_plot(axs[c], hist[c], self.labels[c], self.colors[c])
            plt.xlim(0, self.two_n)
            plt.show()
        return hist[1:]
    def end(self, ref_idx):
        plt.figure(figsize=(10, 5))
        x = np.arange(1, len(self.corrections) + 1, dtype=int)
        y = self.corrections
        plt.plot([ref_idx + 1, ref_idx + 1], [0, 1], color='cornflowerblue', linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--', label='no correction')
        plt.plot(x, y[:, 0], color=self.colors[1], label=self.labels[1] + ' correction')
        plt.plot(x, y[:, 1], color=self.colors[2], label=self.labels[2] + ' correction')
        plt.xlabel('frame')
        plt.ylabel('correction')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(0)
        plt.show()
        
class SVCorrection(Ch2Correction):
    def __init__(self, mask_size=None, i_min=0, i_max=-1, img_scale=default_img_scale, corr_map=LINEAR, plot_histograms=False):
        Ch2Correction.__init__(self, mask_size, i_min, i_max, img_scale, corr_map, plot_histograms)
        self.labels = ("H", "S", "V")
        self.colors = ("hotpink", "orange", "navy")
    def preprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    def postprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_HSV2BGR)
    
class LSCorrection(Ch2Correction):
    def __init__(self, mask_size=None, i_min=0, i_max=-1, img_scale=default_img_scale, corr_map=LINEAR, plot_histograms=False):
        Ch2Correction.__init__(self,mask_size, i_min, i_max, img_scale, corr_map, plot_histograms)
        self.labels = ("H", "L", "S")
        self.colors = ("hotpink", "navy", "orange")
    def preprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_BGR2HLS)
    def postprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_HLS2BGR)

class Balance:
    def __init__(self, corrector):
        self.corrector = corrector
    def begin(self, process):
        self.process = process
        self.corrector.begin(read_img(self.process.input_dir + "/" + self.process.filenames[process.ref_idx]), self.process.counts)
    def end(self):
        self.process.print_message('                                                                                 ')
        self.corrector.end(self.process.ref_idx)
    def run_frame(self, idx, ref_idx, image):
        if(idx != self.process.ref_idx):
            self.process.sub_message('- balance image    ', end='\r')
            image = self.corrector.process(idx, image)
        return image