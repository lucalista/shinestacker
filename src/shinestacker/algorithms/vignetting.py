# pylint: disable=C0114, C0115, C0116, R0902, E1101, W0718, W0640
import logging
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit, fsolve
import cv2
from .. core.colors import color_str
from .. config.constants import constants
from .utils import img_8bit, save_plot
from .stack_framework import SubAction

CLIP_EXP = 10


class Vignetting(SubAction):
    def __init__(self, enabled=True, percentiles=(0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95), **kwargs):
        super().__init__(enabled)
        self.r_steps = kwargs.get('r_steps', constants.DEFAULT_R_STEPS)
        self.black_threshold = kwargs.get('black_threshold', constants.DEFAULT_BLACK_THRESHOLD)
        self.apply_correction = kwargs.get('apply_correction', True)
        self.plot_correction = kwargs.get('plot_correction', False)
        self.plot_summary = kwargs.get('plot_summary', False)
        self.max_correction = kwargs.get('max_correction', constants.DEFAULT_MAX_CORRECTION)
        self.percentiles = np.sort(percentiles)
        self.w_2 = None
        self.h_2 = None
        self.v0 = None
        self.r_max = None
        self.process = None
        self.corrections = None

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

    @staticmethod
    def sigmoid(r, i0, k, r0):
        return i0 / (1.0 +
                     np.exp(np.minimum(CLIP_EXP,
                                       np.exp(np.clip(k * (r - r0),
                                              -CLIP_EXP, CLIP_EXP)))))

    def fit_sigmoid(self, radii, intensities):
        valid_mask = ~np.isnan(intensities)
        i_valid, r_valid = intensities[valid_mask], radii[valid_mask]
        try:
            res = curve_fit(Vignetting.sigmoid, r_valid, i_valid,
                            p0=[np.max(i_valid), 0.01, np.median(r_valid)],
                            bounds=([0, 0, 0], ['inf', 'inf', 'inf']))[0]
        except Exception:
            self.process.sub_message(
                color_str(": could not find vignetting model", "red"),
                level=logging.WARNING)
            res = None
        return res

    def correct_vignetting(self, image, params):
        h, w = image.shape[:2]
        y, x = np.ogrid[:h, :w]
        r = np.sqrt((x - w / 2)**2 + (y - h / 2)**2)
        vignette = np.clip(Vignetting.sigmoid(r, *params) / self.v0, 1e-6, 1)
        if self.max_correction < 1:
            vignette = (1.0 - self.max_correction) + vignette * self.max_correction
        if len(image.shape) == 3:
            vignette = vignette[:, :, np.newaxis]
            vignette[np.min(image, axis=2) < self.black_threshold, :] = 1
        else:
            vignette[image < self.black_threshold] = 1
        return np.clip(image / vignette, 0, 255
                       if image.dtype == np.uint8 else 65535).astype(image.dtype)

    def run_frame(self, idx, _ref_idx, img_0):
        self.process.sub_message_r(": compute vignetting")
        img = cv2.cvtColor(img_8bit(img_0), cv2.COLOR_BGR2GRAY)
        radii, intensities = self.radial_mean_intensity(img)
        pars = self.fit_sigmoid(radii, intensities)
        if pars is None:
            return img_0
        self.v0 = Vignetting.sigmoid(0, *pars)
        i0_fit, k_fit, r0_fit = pars
        self.process.sub_message(
            f": vignetting model parameters: i0={i0_fit:.4f}, k={k_fit:.4f}, r0={r0_fit:.4f}",
            level=logging.DEBUG)
        if self.plot_correction:
            plt.figure(figsize=(10, 5))
            plt.plot(radii, intensities, label="image mean intensity")
            plt.plot(radii, Vignetting.sigmoid(radii, *pars), label="sigmoid fit")
            plt.xlabel('radius (pixels)')
            plt.ylabel('mean intensity')
            plt.legend()
            plt.xlim(radii[0], radii[-1])
            plt.ylim(0)
            idx_str = f"{idx:04d}"
            plot_path = f"{self.process.working_path}/" \
                f"{self.process.plot_path}/{self.process.name}-" \
                f"radial-intensity-{idx_str}.pdf"
            save_plot(plot_path)
            plt.close('all')
            self.process.callback(
                'save_plot', self.process.id,
                f"{self.process.name}: intensity\nframe {idx_str}", plot_path)
        for i, p in enumerate(self.percentiles):
            self.corrections[i][idx] = fsolve(lambda x: Vignetting.sigmoid(x, *pars) /
                                              self.v0 - p, r0_fit)[0]
        if self.apply_correction:
            self.process.sub_message_r(": correct vignetting")
            return self.correct_vignetting(img_0, pars)
        return img_0

    def begin(self, process):
        self.process = process
        self.corrections = [np.full(self.process.counts, None, dtype=float)
                            for p in self.percentiles]

    def end(self):
        if self.plot_summary:
            plt.figure(figsize=(10, 5))
            xs = np.arange(1, len(self.corrections[0]) + 1, dtype=int)
            for i, p in enumerate(self.percentiles):
                linestyle = 'solid'
                if p == 0.5:
                    linestyle = '-.'
                elif i in (0, len(self.percentiles) - 1):
                    linestyle = 'dotted'
                plt.plot(xs, self.corrections[i], label=f"{p:.0%} correction",
                         linestyle=linestyle, color="blue")
            plt.fill_between(xs, self.corrections[-1], self.corrections[0], color="#0000ff20")
            iis = np.where(self.percentiles == 0.5)
            if len(iis) > 0:
                i = iis[0][0]
                if 1 <= i < len(self.percentiles) - 1:
                    plt.fill_between(xs, self.corrections[i - 1], self.corrections[i + 1],
                                     color="#0000ff20")
            plt.plot(xs[[0, -1]], [self.r_max] * 2,
                     linestyle="--", label="max. radius", color="darkred")
            plt.plot(xs[[0, -1]], [self.w_2] * 2,
                     linestyle="--", label="half width", color="limegreen")
            plt.plot(xs[[0, -1]], [self.h_2] * 2,
                     linestyle="--", label="half height", color="darkgreen")
            plt.xlabel('frame')
            plt.ylabel('distance from center (pixels)')
            plt.legend(ncols=2)
            plt.xlim(xs[0], xs[-1])
            plt.ylim(0, self.r_max * 1.05)
            plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                        f"{self.process.name}-r0.pdf"
            save_plot(plot_path)
            plt.close('all')
            self.process.callback('save_plot', self.process.id,
                                  f"{self.process.name}: vignetting", plot_path)
