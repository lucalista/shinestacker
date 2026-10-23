# pylint: disable=C0114, C0115, C0116, R0902, E1101, W0718, W0640, R0913, R0917, R0914
import math
import traceback
import logging
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit, bisect
import cv2
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. config.app_config import AppConfig
from .. core.colors import color_str
from .. core.core_utils import setup_matplotlib_mode
from .utils import img_8bit, img_subsample
from .stack_framework import SubAction
setup_matplotlib_mode()

CLIP_EXP = 10


def sigmoid_model(r, i0, k, r0):
    return i0 / (1.0 +
                 np.exp(np.minimum(CLIP_EXP,
                                   np.exp(np.clip(k * (r - r0),
                                          -CLIP_EXP, CLIP_EXP)))))


def radial_mean_intensity(image, r_steps):
    if len(image.shape) > 2:
        raise ValueError("The image must be grayscale")
    h, w = image.shape
    w_2, h_2 = w / 2, h / 2
    r_max = np.sqrt((w / 2)**2 + (h / 2)**2)
    radii = np.linspace(0, r_max, r_steps + 1)
    y, x = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((x - w_2)**2 + (y - h_2)**2)
    bin_indices = np.digitize(dist_from_center, radii) - 1
    valid_mask = (bin_indices >= 0) & (bin_indices < r_steps)
    bin_indices_valid = bin_indices[valid_mask]
    image_valid = image[valid_mask]
    bin_sums = np.bincount(
        bin_indices_valid.ravel(), weights=image_valid.ravel(), minlength=r_steps)
    bin_counts = np.bincount(
        bin_indices_valid.ravel(), minlength=r_steps)
    mean_intensities = np.full(r_steps, np.nan)
    valid_bins = bin_counts > 0
    mean_intensities[valid_bins] = bin_sums[valid_bins] / bin_counts[valid_bins]
    return (radii[1:] + radii[:-1]) / 2, mean_intensities


def fit_sigmoid(radii, intensities):
    valid_mask = ~np.isnan(intensities)
    i_valid, r_valid = intensities[valid_mask], radii[valid_mask]
    r_max = radii.max()
    res = curve_fit(sigmoid_model, r_valid, i_valid,
                    p0=[2 * np.max(i_valid), 10 / r_max, 0.8 * r_max],
                    bounds=([0, 0, 0], ['inf', 'inf', 'inf']))[0]
    return res


def subsample_factor(subsample, image):
    if subsample == 0:
        h, w = image.shape[:2]
        img_res = (float(h) / 1000) * (float(w) / 1000)
        target_res = DEFAULTS['balance_frames_params']['resolution_target']
        subsample = int(1 + math.floor(img_res / target_res))
    return subsample


def img_subsampled(image, subsample=DEFAULTS['vignetting_params']['subsample'],
                   fast_subsampling=DEFAULTS['vignetting_params']['fast_subsampling']):
    image_bw = cv2.cvtColor(img_8bit(image), cv2.COLOR_BGR2GRAY)
    if subsample == 0:
        subsample = subsample_factor(subsample, image)
    img_sub = image_bw if subsample == 1 else img_subsample(image_bw, subsample, fast_subsampling)
    return img_sub


def compute_fit_parameters(
        image, r_steps, radii=None, intensities=None,
        subsample=DEFAULTS['vignetting_params']['subsample'],
        fast_subsampling=DEFAULTS['vignetting_params']['fast_subsampling']):
    if subsample == 0:
        subsample = subsample_factor(subsample, image)
    image_sub = img_subsampled(image, subsample, fast_subsampling)
    if radii is None and intensities is None:
        radii, intensities = radial_mean_intensity(image_sub, r_steps)
    params = fit_sigmoid(radii, intensities)
    params[1] /= subsample  # k
    params[2] *= subsample  # r0
    return params


def correct_vignetting(
        image, max_correction=DEFAULTS['vignetting_params']['max_correction'],
        black_threshold=DEFAULTS['vignetting_params']['black_threshold'],
        r_steps=DEFAULTS['vignetting_params']['r_steps'],
        params=None, v0=None,
        subsample=DEFAULTS['vignetting_params']['subsample'],
        fast_subsampling=DEFAULTS['vignetting_params']['fast_subsampling']):
    if params is None:
        if r_steps is None:
            raise RuntimeError("Either r_steps or pars must not be None")
        if subsample == 0:
            subsample = subsample_factor(subsample, image)
        params = compute_fit_parameters(
            image, r_steps, subsample=subsample, fast_subsampling=fast_subsampling)
    if v0 is None:
        v0 = sigmoid_model(0, *params)
    h, w = image.shape[:2]
    y, x = np.ogrid[:h, :w]
    r = np.sqrt((x - w / 2)**2 + (y - h / 2)**2)
    vignette = np.clip(sigmoid_model(r, *params) / v0, 1e-6, 1)
    if max_correction < 1:
        vignette = (1.0 - max_correction) + vignette * max_correction
    threshold = black_threshold if image.dtype == np.uint8 else black_threshold * 256
    if len(image.shape) == 3:
        vignette = vignette[:, :, np.newaxis]
        vignette[np.min(image, axis=2) < threshold, :] = 1
    else:
        vignette[image < black_threshold] = 1
    return np.clip(np.rint(image / vignette), 0, 255
                   if image.dtype == np.uint8 else 65535).astype(image.dtype)


class Vignetting(SubAction):
    def __init__(self, name='', enabled=True,
                 percentiles=(0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95), **kwargs):
        super().__init__(name, enabled)
        self.r_steps = kwargs.get(
            'r_steps', DEFAULTS['vignetting_params']['r_steps'])
        self.black_threshold = kwargs.get(
            'black_threshold', DEFAULTS['vignetting_params']['black_threshold'])
        self.plot_correction = kwargs.get(
            'plot_correction', False)
        self.plot_summary = kwargs.get(
            'plot_summary', False)
        self.max_correction = kwargs.get(
            'max_correction', DEFAULTS['vignetting_params']['max_correction'])
        self.percentiles = np.sort(percentiles)
        self.subsample = kwargs.get(
            'subsample', DEFAULTS['vignetting_params']['subsample'])
        self.fast_subsampling = kwargs.get(
            'fast_subsampling', DEFAULTS['vignetting_params']['fast_subsampling'])
        self.w_2 = None
        self.h_2 = None
        self.v0 = None
        self.r_max = None
        self.process = None
        self.corrections = None

    def run_frame(self, idx, _ref_idx, img_0):
        self.process.print_message(
            color_str(f"{self.process.frame_str(idx)}: compute vignetting", "cyan"))
        h, w = img_0.shape[:2]
        self.w_2, self.h_2 = w / 2, h / 2
        self.r_max = np.sqrt((w / 2)**2 + (h / 2)**2)
        subsample = subsample_factor(self.subsample, img_0)
        image_sub = img_subsampled(img_0, subsample, self.fast_subsampling)
        radii, intensities = radial_mean_intensity(image_sub, self.r_steps)
        try:
            params = compute_fit_parameters(
                img_0, self.r_steps, radii, intensities, subsample, self.fast_subsampling)
        except Exception:
            traceback.print_exc()
            self.process.sub_message(
                color_str(": could not find vignetting model", "red"), level=logging.WARNING)
            params = None
        if params is None:
            return img_0
        self.v0 = sigmoid_model(0, *params)
        # i0_fit, k_fit, r0_fit = params
        # self.process.print_message(
        #     color_str(f"{self.process.frame_str(idx)}: vignetting model parameters: ", "cyan") +
        #     color_str(f"i0={i0_fit / 2:.4f}, "
        #               f"k={k_fit * self.r_max:.4f}, "
        #               f"r0={r0_fit / self.r_max:.4f}",
        #               "light_blue"),
        #     level=logging.DEBUG)
        if self.plot_correction:
            fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
            plt.plot(radii, intensities, label="image mean intensity")
            plt.plot(radii, sigmoid_model(radii * subsample, *params), label="sigmoid fit")
            plt.xlabel('radius (pixels)')
            plt.ylabel('mean intensity')
            plt.legend()
            plt.xlim(radii[0], radii[-1])
            plt.ylim(0)
            idx_str = f"{idx:04d}"
            plots_ext = AppConfig.get('plots_format')
            plot_path = f"{self.process.working_path}/" \
                f"{self.process.plot_path}/{self.process.name}-" \
                f"radial-intensity-{idx_str}.{plots_ext}"
            self.process.plot_manager.save_plot(plot_path, fig)
            save_plot_name = self.process.output_path if self.name == '' else self.name
            self.process.callback(
                constants.CALLBACK_SAVE_PLOT, self.process.id, save_plot_name,
                f"{self.process.name}: intensity\nframe {idx_str}", plot_path, "vignette")

        for i, p in enumerate(self.percentiles):
            s1 = sigmoid_model(0, *params) / self.v0
            s2 = sigmoid_model(self.r_max, *params) / self.v0
            if s1 > p > s2:
                try:
                    c = bisect(lambda x: sigmoid_model(x, *params) / self.v0 - p, 0, self.r_max)
                except Exception as e:
                    traceback.print_exc()
                    self.process.sub_message(color_str(f": {str(e).lower()}", "yellow"),
                                             level=logging.WARNING)
            elif s1 <= p:
                c = 0
            else:
                c = self.r_max
            self.corrections[i][idx] = c
        self.process.print_message(
            color_str(f"{self.process.frame_str(idx)}: correct vignetting", "cyan"))
        return correct_vignetting(
            img_0, self.max_correction, self.black_threshold, None, params, self.v0,
            subsample, self.fast_subsampling)

    def begin(self, process):
        self.process = process
        self.corrections = [np.full(self.process.total_action_counts, None, dtype=float)
                            for p in self.percentiles]

    def end(self):
        if self.plot_summary:
            fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
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
            plots_ext = AppConfig.get('plots_format')
            plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                        f"{self.process.name}-r0.{plots_ext}"
            self.process.plot_manager.save_plot(plot_path, fig)
            plt.close('all')
            save_plot_name = self.process.output_path if self.name == '' else self.name
            self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id, save_plot_name,
                                  f"{self.process.name}: vignetting", plot_path)
