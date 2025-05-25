import matplotlib.pyplot as plt
import cv2
import numpy as np
from focus_stack.utils import img_8bit, save_plot
from scipy.optimize import curve_fit, fsolve
from termcolor import colored
import logging

CLIP_EXP=10

class Vignetting:
    def __init__(self, r_steps=100, black_threshold=1, percentiles=(0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95),
                 apply_correction=True, plot_histograms=False):
        self.r_steps = r_steps
        self.black_threshold = black_threshold
        self.apply_correction = apply_correction
        self.plot_histograms = plot_histograms
        self.percentiles = np.sort(percentiles)

    def radial_mean_intensity(self, image):
        if len(image.shape) > 2:
            raise ValueError("The image must be grayscale")
        h, w = image.shape
        self.w_2, self.h_2 = w / 2, h / 2
        self.r_max = np.sqrt((w / 2)**2 + (h / 2)**2)
        radii = np.linspace(0, self.r_max, self.r_steps + 1)
        mean_intensities = np.zeros(self.r_steps)
        y, x = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((x - self.w_2)**2 + (y - self.h_2)**2)
        for i in range(self.r_steps):
            mask = (dist_from_center >= radii[i]) & (dist_from_center < radii[i + 1])
            if np.any(mask):
                mean_intensities[i] = np.mean(image[mask])
            else:
                mean_intensities[i] = np.nan
        return (radii[1:] + radii[:-1]) / 2, mean_intensities

    def sigmoid(r, i0, k, r0):
        return i0 / (1 + np.exp(np.minimum(CLIP_EXP, np.exp(np.clip(k * (np.float64(r) - r0), -CLIP_EXP, CLIP_EXP)))))

    def fit_sigmoid(self, radii, intensities):
        valid_mask = ~np.isnan(intensities)
        i_valid, r_valid = intensities[valid_mask], radii[valid_mask]
        try:
            res =  curve_fit(Vignetting.sigmoid, r_valid, i_valid,
                             p0=[np.max(i_valid), 0.01, np.median(r_valid)])[0]
        except Exception:
            self.process.sub_message(colored(": could not find vignetting model", "red"), level=logging.ERROR)
            res = None
        return res

    def correct_vignetting(self, image, params):
        h, w = image.shape[:2]
        y, x = np.ogrid[:h, :w]
        r = np.sqrt((x - w / 2)**2 + (y - h / 2)**2)
        vignette = np.clip(Vignetting.sigmoid(r, *params) / self.v0, 1e-6, 1)
        if len(image.shape) == 3:
            vignette = vignette[:, :, np.newaxis]
            vignette[np.min(image, axis=2) < self.black_threshold, :] = 1
        else:
            vignette[image < self.black_threshold] = 1
        return np.clip(image / vignette, 0, 255 if image.dtype == np.uint8 else 65535).astype(image.dtype)

    def run_frame(self, idx, ref_idx, img_0):
        self.process.sub_message_r(colored(": compute vignetting", "light_blue"))
        img = cv2.cvtColor(img_8bit(img_0), cv2.COLOR_BGR2GRAY)
        radii, intensities = self.radial_mean_intensity(img)
        pars = self.fit_sigmoid(radii, intensities)
        if pars is None:
            return img_0
        self.v0 = Vignetting.sigmoid(0, *pars)
        i0_fit, k_fit, r0_fit = pars
        self.process.sub_message(f": fit parameters: i0={i0_fit:.4f}, k={k_fit:.4f}, r0={r0_fit:.4f}",
                                 level=logging.DEBUG)
        plt.figure(figsize=(10, 5))
        plt.plot(radii, intensities, label="image mean intensity")
        plt.plot(radii, Vignetting.sigmoid(radii, *pars), label="sigmoid fit")
        plt.xlabel('radius (pixels)')
        plt.ylabel('mean intensity')
        plt.legend()
        plt.xlim(radii[0], radii[-1])
        plt.ylim(0)
        save_plot(self.process.plot_path + "/" + self.process.name + "-radial-intensity-{:04d}.pdf".format(idx),
                  show=self.plot_histograms)
        for i, p in enumerate(self.percentiles):
            self.corrections[i][idx] = fsolve(lambda x: Vignetting.sigmoid(x, *pars)/self.v0 - p, r0_fit)[0]
        if self.apply_correction:
            self.process.sub_message_r(colored(": correct vignetting", "light_blue"))
            return self.correct_vignetting(img_0, pars)
        else:
            return img_0

    def begin(self, process):
        self.process = process
        self.corrections = [np.full(self.process.counts, None, dtype=float) for p in self.percentiles]

    def end(self):
        plt.figure(figsize=(10, 5))
        xs = np.arange(1, len(self.corrections[0]) + 1, dtype=int)
        for i, p in enumerate(self.percentiles):
            linestyle = 'solid'
            if p == 0.5:
                linestyle = '-.'
            elif i == 0 or i == len(self.percentiles) - 1:
                linestyle = 'dotted'
            plt.plot(xs, self.corrections[i], label=f"{p:.0%} correction",
                     linestyle=linestyle, color="blue")
        plt.fill_between(xs, self.corrections[-1], self.corrections[0], color="#0000ff10")
        iis = np.where(self.percentiles == 0.5)
        if len(iis) > 0:
            i = iis[0][0]
            if i >= 1 and i < len(self.percentiles) - 1:
                plt.fill_between(xs, self.corrections[i - 1], self.corrections[i + 1], color="#0000ff20")
        plt.plot(xs[[0, -1]], [self.r_max]*2, linestyle="--", label="max. radius", color="darkred")
        plt.plot(xs[[0, -1]], [self.w_2]*2, linestyle="--", label="half width", color="limegreen")
        plt.plot(xs[[0, -1]], [self.h_2]*2, linestyle="--", label="half height", color="darkgreen")
        plt.xlabel('frame')
        plt.ylabel('$r_0$ (pixels)')
        plt.legend(ncols=2)
        plt.xlim(xs[0], xs[-1])
        plt.ylim(0, self.r_max*1.05)
        save_plot(self.process.plot_path + "/" + self.process.name + "-r0.pdf")