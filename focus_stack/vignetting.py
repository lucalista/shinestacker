import matplotlib.pyplot as plt
import cv2
import numpy as np
from focus_stack.utils import img_8bit, save_plot
from scipy.optimize import curve_fit
import logging


class Vignetting:
    def __init__(self, r_steps=100, black_threshold=1, apply_correction=True):
        self.r_steps = r_steps
        self.black_threshold = black_threshold
        self.apply_correction = apply_correction

    def radial_mean_intensity(self, image):
        if len(image.shape) > 2:
            raise ValueError("The image must be grayscale")
        h, w = image.shape
        center = (w / 2, h / 2)
        r_max = np.sqrt((w / 2)**2 + (h / 2)**2)
        radii = np.linspace(0, r_max, self.r_steps + 1)
        mean_intensities = np.zeros(self.r_steps)
        y, x = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((x - center[0])**2 + (y - center[1])**2)
        for i in range(self.r_steps):
            mask = (dist_from_center >= radii[i]) & (dist_from_center < radii[i + 1])
            if np.any(mask):
                mean_intensities[i] = np.mean(image[mask])
            else:
                mean_intensities[i] = np.nan
        return (radii[1:] + radii[:-1]) / 2, mean_intensities

    def sigmoid(r, i0, k, r0):
        return i0 / (1 + np.exp(np.exp(np.clip(k * (np.float64(r) - r0), -6, 6))))

    def fit_sigmoid(self, radii, intensities):
        valid_mask = ~np.isnan(intensities)
        i_valid, r_valid = intensities[valid_mask], radii[valid_mask]
        return curve_fit(Vignetting.sigmoid, r_valid, i_valid,
                         p0=[np.max(i_valid), 0.01, np.median(r_valid)])[0]

    def correct_vignetting(self, image, params):
        h, w = image.shape[:2]
        y, x = np.ogrid[:h, :w]
        r = np.sqrt((x - w / 2)**2 + (y - h / 2)**2)
        vignette = np.clip(Vignetting.sigmoid(r, *params) / Vignetting.sigmoid(0, *params), 1e-6, 1)
        if len(image.shape) == 3:
            vignette = vignette[:, :, np.newaxis]
            vignette[np.min(image, axis=2) < self.black_threshold, :] = 1
        else:
            vignette[image < self.black_threshold] = 1
        print((vignette*255).astype(image.dtype).max(), (vignette*255).astype(image.dtype).min())
        return np.clip(image / vignette, 0, 255 if image.dtype == np.uint8 else 65535).astype(image.dtype)

    def run_frame(self, idx, ref_idx, img_0):
        img = cv2.cvtColor(img_8bit(img_0), cv2.COLOR_BGR2GRAY)
        radii, intensities = self.radial_mean_intensity(img)
        i0_fit, k_fit, r0_fit = self.fit_sigmoid(radii, intensities)
        self.process.sub_message(f": fit parameters: i0={i0_fit:.2f}, k={k_fit:.4f}, r0={r0_fit:.2f}",
                                 level=logging.DEBUG)
        plt.figure(figsize=(10, 5))
        plt.plot(radii, intensities, label="image mean intensity")
        plt.plot(radii, Vignetting.sigmoid(radii, i0_fit, k_fit, r0_fit), label="sigmoid fit")
        plt.xlabel('radius (pixels)')
        plt.ylabel('mean intensity')
        plt.legend()
        plt.xlim(radii[0], radii[-1])
        plt.ylim(0)
        save_plot(self.process.plot_path + "/" + self.process.name + "-radial-intensity-{:04d}.pdf".format(idx))
        return self.correct_vignetting(img_0, (i0_fit, k_fit, r0_fit)) if self.apply_correction else img_0

    def begin(self, process):
        self.process = process

    def end(self):
        pass