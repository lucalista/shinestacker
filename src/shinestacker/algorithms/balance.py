# pylint: disable=C0114, C0115, C0116, E1101, R0902, E1128, E0606, W0640, R0913, R0917, R0914
import math
import numpy as np
import cv2
import matplotlib.pyplot as plt
from scipy.optimize import bisect
from scipy.interpolate import interp1d
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. config.app_config import AppConfig
from .. core.exceptions import InvalidOptionError
from .. core.colors import color_str
from .. core.core_utils import setup_matplotlib_mode
from .utils import (read_img, img_subsample, bgr_to_hsv, bgr_to_hls,
                    hsv_to_bgr, hls_to_bgr, bgr_to_lab, lab_to_bgr,
                    split_alpha, merge_alpha, drop_alpha)
from .stack_framework import SubAction
setup_matplotlib_mode()


class BaseHistogrammer:
    def __init__(self, name, dtype, num_pixel_values, max_pixel_value, channels,
                 plot_histograms, plot_summary, process=None):
        self.name = name
        self.dtype = dtype
        self.num_pixel_values = num_pixel_values
        self.max_pixel_value = max_pixel_value
        self.channels = channels
        self.plot_histograms = plot_histograms
        self.plot_summary = plot_summary
        self.process = process
        self.corrections = None

    def begin(self, size):
        self.corrections = np.ones((size, self.channels))

    def add_correction(self, idx, correction):
        if idx != self.process.ref_idx:
            self.corrections[idx] = correction

    def histo_plot(self, ax, hist, x_label, color, alpha=1):
        ax.set_ylabel("# of pixels")
        ax.set_xlabel(x_label)
        ax.set_xlim([0, self.max_pixel_value])
        ax.set_yscale('log')
        x_values = np.linspace(0, self.max_pixel_value, len(hist))
        ax.plot(x_values, hist, color=color, alpha=alpha)

    def save_plot(self, fig, idx, tag="_default"):
        idx_str = f"{idx:04d}"
        plots_ext = AppConfig.get('plots_format')
        plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                    f"{self.process.name}-hist-{idx_str}.{plots_ext}"
        self.process.plot_manager.save_plot(plot_path, fig, tag)
        save_plot_name = self.process.output_path if self.name == '' else self.name
        self.process.callback(
            'save_plot', self.process.id, save_plot_name,
            f"{self.process.name}: balance\nframe {idx_str}",
            plot_path, "balance")

    def save_summary_plot(self, fig, name='balance'):
        plots_ext = AppConfig.get('plots_format')
        plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                    f"{self.process.name}-{name}.{plots_ext}"
        self.process.plot_manager.save_plot(plot_path, fig)
        save_plot_name = self.process.output_path if self.name == '' else self.name
        self.process.callback(
            'save_plot', self.process.id, save_plot_name,
            f"{self.process.name}: {name}", plot_path)


class LumiHistogrammer(BaseHistogrammer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.colors = ("r", "g", "b")

    def generate_frame_plot(self, idx, hist, chans, calc_hist_func):
        fig, axs = plt.subplots(1, 2, figsize=constants.PLT_FIG_SIZE, sharey=True)
        self.histo_plot(axs[0], hist, "pixel luminosity", 'black')
        for (chan, color) in zip(chans, self.colors):
            hist_col = calc_hist_func(chan)
            self.histo_plot(axs[1], hist_col, "R, G, B intensity", color, alpha=0.5)
        fig.suptitle("Image histograms")
        plt.xlim(0, self.max_pixel_value)
        self.save_plot(fig, idx)

    def generate_summary_plot(self, ref_idx):
        fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
        x = np.arange(0, len(self.corrections), dtype=int)
        y = self.corrections
        plt.plot([ref_idx, ref_idx], [0, np.max(y)], color='cornflowerblue',
                 linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--',
                 label='no correction')
        plt.plot(x, y, color='navy', label='luminosity correction')
        plt.title("Image balance correction")
        plt.xlabel('frame')
        plt.ylabel('correction')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(0, np.max(y) * 1.1)
        self.save_summary_plot(fig)


class RGBHistogrammer(BaseHistogrammer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.colors = ("r", "g", "b")

    def generate_frame_plot(self, idx, hists):
        fig, axs = plt.subplots(1, 3, figsize=constants.PLT_FIG_SIZE, sharey=True)
        for c in [2, 1, 0]:
            self.histo_plot(axs[c], hists[c], self.colors[c] + " luminosity", self.colors[c])
        fig.suptitle("Image histograms")
        plt.xlim(0, self.max_pixel_value)
        self.save_plot(fig, idx)

    def generate_summary_plot(self, ref_idx):
        fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
        x = np.arange(0, len(self.corrections), dtype=int)
        y = self.corrections
        max_val = np.max(y) if np.any(y) else 1.0
        plt.plot([ref_idx, ref_idx], [0, max_val], color='cornflowerblue',
                 linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--',
                 label='no correction')
        plt.plot(x, y[:, 0], color='r', label='R correction')
        plt.plot(x, y[:, 1], color='g', label='G correction')
        plt.plot(x, y[:, 2], color='b', label='B correction')
        plt.title("Image balance correction")
        plt.xlabel('frame')
        plt.ylabel('correction')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(0, max_val * 1.1)
        self.save_summary_plot(fig)


class Ch1Histogrammer(BaseHistogrammer):
    def __init__(self, labels, colors, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.labels = labels
        self.colors = colors

    def generate_frame_plot(self, idx, hists):
        fig, axs = plt.subplots(1, 3, figsize=constants.PLT_FIG_SIZE, sharey=True)
        for c in range(3):
            self.histo_plot(axs[c], hists[c], self.labels[c], self.colors[c])
        fig.suptitle("Image histograms")
        for ax in axs:
            ax.set_xlim(0, self.max_pixel_value)
        self.save_plot(fig, idx)

    def generate_summary_plot(self, ref_idx):
        fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
        x = np.arange(0, len(self.corrections), dtype=int)
        y = self.corrections
        max_val = np.max(y) if np.any(y) else 1.0
        plt.plot([ref_idx, ref_idx], [0, max_val], color='cornflowerblue',
                 linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--',
                 label='no correction')
        plt.plot(x, y[:, 0], color=self.colors[0], label=self.labels[0] + ' correction')
        plt.title("Image balance correction")
        plt.xlabel('frame')
        plt.ylabel('correction')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(0, max_val * 1.1)
        self.save_summary_plot(fig)


class Ch2Histogrammer(BaseHistogrammer):
    def __init__(self, labels, colors, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.labels = labels
        self.colors = colors

    def generate_frame_plot(self, idx, hists):
        fig, axs = plt.subplots(1, 3, figsize=constants.PLT_FIG_SIZE, sharey=True)
        for c in range(3):
            self.histo_plot(axs[c], hists[c], self.labels[c], self.colors[c])
        fig.suptitle("Image histograms")
        for ax in axs:
            ax.set_xlim(0, self.max_pixel_value)
        self.save_plot(fig, idx)

    def generate_summary_plot(self, ref_idx):
        fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
        x = np.arange(0, len(self.corrections), dtype=int)
        y = self.corrections
        max_val = np.max(y) if np.any(y) else 1.0
        plt.plot([ref_idx, ref_idx], [0, max_val], color='cornflowerblue',
                 linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--',
                 label='no correction')
        plt.plot(x, y[:, 0], color=self.colors[1], label=self.labels[1] + ' correction')
        plt.plot(x, y[:, 1], color=self.colors[2], label=self.labels[2] + ' correction')
        plt.title("Image balance correction")
        plt.xlabel('frame')
        plt.ylabel('correction')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(0, max_val * 1.1)
        self.save_summary_plot(fig)


class CorrectionMapBase:
    def __init__(self, dtype, ref_hist, intensity_interval=None):
        intensity_interval = {
            **DEFAULTS['balance_frames_params']['intensity_interval'],
            **(intensity_interval or {})
        }
        self.dtype = dtype
        self.num_pixel_values = constants.NUM_UINT8 if dtype == np.uint8 else constants.NUM_UINT16
        self.max_pixel_value = self.num_pixel_values - 1
        self.id_lut = np.array(list(range(self.num_pixel_values)))
        i_min, i_max = intensity_interval['min'], intensity_interval['max']
        self.i_min = i_min
        self.i_end = i_max + 1 if i_max >= 0 else self.num_pixel_values
        self.channels = len(ref_hist)
        self.reference = None

    def lut(self, _correction, _reference):
        return None

    def apply_lut(self, correction, reference, img):
        lut = self.lut(correction, reference)
        return cv2.LUT(img, lut) if self.dtype == np.uint8 else np.take(lut, img)

    def adjust(self, image, correction):
        if self.channels == 1:
            return self.apply_lut(correction[0], self.reference[0], image)
        chans = cv2.split(image)
        if self.channels == 2:
            ch_out = [chans[0]] + [self.apply_lut(
                correction[c - 1], self.reference[c - 1], chans[c]
            ) for c in range(1, 3)]
        elif self.channels == 3:
            ch_out = [self.apply_lut(
                correction[c], self.reference[c], chans[c]
            ) for c in range(3)]
        return cv2.merge(ch_out)

    def correction_size(self, correction):
        return correction


class MatchHist(CorrectionMapBase):
    def __init__(self, dtype, ref_hist, intensity_interval=None):
        super().__init__(dtype, ref_hist, intensity_interval)
        self.reference = self.cumsum(ref_hist)
        self.reference_mean = [r.mean() for r in self.reference]
        self.values = [*range(self.num_pixel_values)]

    def cumsum(self, hist):
        return [np.cumsum(h) / h.sum() * self.max_pixel_value for h in hist]

    def lut(self, correction, reference):
        interp = interp1d(reference, self.values)
        lut = np.array([interp(v) for v in np.clip(correction, reference.min(), reference.max())])
        l0, l1 = lut[0], lut[-1]
        ll = lut[(lut != l0) & (lut != l1)]
        if ll.size > 0:
            l_min, l_max = ll.min(), ll.max()
            i0, i1 = self.id_lut[lut == l0], self.id_lut[lut == l1]
            i0_max = i0.max()
            lut[lut == l0] = (i0 / i0_max * l_min) if i0_max > 0 else 0
            lut[lut == l1] = i1 + \
                (i1 - self.max_pixel_value) * \
                (self.max_pixel_value - l_max) / \
                float(i1.size) if i1.size > 0 else self.max_pixel_value
        return lut.astype(self.dtype)

    def correction(self, hist):
        return self.cumsum(hist)

    def correction_size(self, correction):
        return [c.mean() / m for c, m in zip(correction, self.reference_mean)]


class CorrectionMap(CorrectionMapBase):
    def __init__(self, dtype, ref_hist, intensity_interval=None):
        super().__init__(dtype, ref_hist, intensity_interval)
        self.reference = [self.mid_val(self.id_lut, h) for h in ref_hist]

    def mid_val(self, lut, h):
        return np.average(lut[self.i_min:self.i_end], weights=h.flatten()[self.i_min:self.i_end])


class GammaMap(CorrectionMap):
    def correction(self, hist):
        return [bisect(lambda x: self.mid_val(self.lut(x), h) - r, 0.1, 5)
                for h, r in zip(hist, self.reference)]

    def lut(self, correction, _reference=None):
        gamma_inv = 1.0 / correction
        ar = np.arange(0, self.num_pixel_values)
        corr_lut = ((ar / self.max_pixel_value) ** gamma_inv) * self.max_pixel_value
        return corr_lut.astype(self.dtype)


class LinearMap(CorrectionMap):
    def lut(self, correction, _reference=None):
        ar = np.arange(0, self.num_pixel_values)
        return np.clip(ar * correction, 0, self.max_pixel_value).astype(self.dtype)

    def correction(self, hist):
        return [r / self.mid_val(self.id_lut, h) for h, r in zip(hist, self.reference)]


class Correction:
    def __init__(self, name, channels, mask_size=0, intensity_interval=None,
                 subsample=DEFAULTS['balance_frames_params']['subsample'],
                 fast_subsampling=DEFAULTS['balance_frames_params']['fast_subsampling'],
                 corr_map=DEFAULTS['balance_frames_params']['corr_map'],
                 plot_histograms=False, plot_summary=False):
        self.name = name
        self.mask_size = mask_size
        self.intensity_interval = intensity_interval
        self.subsample = subsample
        self.fast_subsampling = fast_subsampling
        self.corr_map = corr_map
        self.channels = channels
        self.plot_histograms = plot_histograms
        self.plot_summary = plot_summary
        self.dtype = None
        self.num_pixel_values = None
        self.max_pixel_value = None
        self.corr_map_obj = None
        self.process = None
        self.histogrammer = None

    def begin(self, ref_image, size, ref_idx):
        self.dtype = ref_image.dtype
        self.num_pixel_values = constants.NUM_UINT8 \
            if ref_image.dtype == np.uint8 else constants.NUM_UINT16
        self.max_pixel_value = self.num_pixel_values - 1
        self._create_histogrammer()
        self.histogrammer.process = self.process
        hist = self.get_hist(self.preprocess(ref_image), ref_idx)
        if self.corr_map == constants.BALANCE_LINEAR:
            self.corr_map_obj = LinearMap(self.dtype, hist, self.intensity_interval)
        elif self.corr_map == constants.BALANCE_GAMMA:
            self.corr_map_obj = GammaMap(self.dtype, hist, self.intensity_interval)
        elif self.corr_map == constants.BALANCE_MATCH_HIST:
            self.corr_map_obj = MatchHist(self.dtype, hist, self.intensity_interval)
        else:
            raise InvalidOptionError("corr_map", self.corr_map)
        self.histogrammer.begin(size)

    def _create_histogrammer(self):
        raise NotImplementedError("Subclasses must implement _create_histogrammer")

    def calc_hist_1ch(self, image):
        if self.subsample > 0:
            subsample = self.subsample
        else:
            h, w = image.shape[:2]
            img_res = float(h) * float(w) / constants.ONE_MEGA
            target_res = DEFAULTS['balance_frames_params']['resolution_target']
            subsample = int(1 + math.floor(img_res / target_res))
        img_sub = image if self.subsample == 1 \
            else img_subsample(image, subsample, self.fast_subsampling)
        if self.mask_size == 0:
            image_sel = img_sub
        else:
            height, width = img_sub.shape[:2]
            xv, yv = np.meshgrid(
                np.linspace(0, width - 1, width),
                np.linspace(0, height - 1, height)
            )
            mask_radius = min(width, height) * self.mask_size / 2
            image_sel = img_sub[
                (xv - width / 2) ** 2 + (yv - height / 2) ** 2 <= mask_radius ** 2
            ]
        bins = np.linspace(-0.5, self.num_pixel_values - 0.5, self.num_pixel_values + 1)
        hist, _bins = np.histogram(image_sel, bins=bins)
        return hist

    def balance(self, image, idx):
        correction = self.corr_map_obj.correction(self.get_hist(image, idx))
        return correction, self.corr_map_obj.adjust(image, correction)

    def get_hist(self, _image, _idx):
        return None

    def end(self, _ref_idx):
        pass

    def apply_correction(self, idx, image):
        if idx == self.process.ref_idx:
            return image
        image = self.preprocess(image)
        correction, image = self.balance(image, idx)
        image = self.postprocess(image)
        self.histogrammer.add_correction(idx, self.corr_map_obj.correction_size(correction))
        return image

    def preprocess(self, image):
        return image

    def postprocess(self, image):
        return image


class LumiCorrection(Correction):
    def __init__(self, name, **kwargs):
        super().__init__(name, 1, **kwargs)

    def _create_histogrammer(self):
        self.histogrammer = LumiHistogrammer(
            name=self.name,
            dtype=self.dtype,
            num_pixel_values=self.num_pixel_values,
            max_pixel_value=self.max_pixel_value,
            channels=1,
            plot_histograms=self.plot_histograms,
            plot_summary=self.plot_summary
        )

    def get_hist(self, image, idx):
        hist = self.calc_hist_1ch(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        if self.histogrammer.plot_histograms:
            chans = cv2.split(image)
            self.histogrammer.generate_frame_plot(idx, hist, chans, self.calc_hist_1ch)
        return [hist]

    def end(self, ref_idx):
        if self.histogrammer and self.histogrammer.plot_summary:
            self.histogrammer.generate_summary_plot(ref_idx)


class RGBCorrection(Correction):
    def __init__(self, name, **kwargs):
        super().__init__(name, 3, **kwargs)

    def _create_histogrammer(self):
        self.histogrammer = RGBHistogrammer(
            name=self.name,
            dtype=self.dtype,
            num_pixel_values=self.num_pixel_values,
            max_pixel_value=self.max_pixel_value,
            channels=3,
            plot_histograms=self.plot_histograms,
            plot_summary=self.plot_summary
        )

    def get_hist(self, image, idx):
        hist = [self.calc_hist_1ch(chan) for chan in cv2.split(image)]
        if self.histogrammer.plot_histograms:
            self.histogrammer.generate_frame_plot(idx, hist)
        return hist

    def end(self, ref_idx):
        if self.histogrammer.plot_summary:
            self.histogrammer.generate_summary_plot(ref_idx)


class Ch1Correction(Correction):
    def __init__(self, name, **kwargs):
        super().__init__(name, 1, **kwargs)
        self.labels = None
        self.colors = None

    def preprocess(self, image):
        raise NotImplementedError('abstract method')

    def get_hist(self, image, idx):
        hist = [self.calc_hist_1ch(chan) for chan in cv2.split(image)]
        if self.histogrammer.plot_histograms:
            self.histogrammer.generate_frame_plot(idx, hist)
        return [hist[0]]

    def end(self, ref_idx):
        if self.histogrammer.plot_summary:
            self.histogrammer.generate_summary_plot(ref_idx)


class Ch2Correction(Correction):
    def __init__(self, name, **kwargs):
        super().__init__(name, 2, **kwargs)
        self.labels = None
        self.colors = None

    def preprocess(self, image):
        raise NotImplementedError('abstract method')

    def get_hist(self, image, idx):
        hist = [self.calc_hist_1ch(chan) for chan in cv2.split(image)]
        if self.histogrammer.plot_histograms:
            self.histogrammer.generate_frame_plot(idx, hist)
        return hist[1:]

    def end(self, ref_idx):
        if self.histogrammer.plot_summary:
            self.histogrammer.generate_summary_plot(ref_idx)


class SVCorrection(Ch2Correction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.labels = ("H", "S", "V")
        self.colors = ("hotpink", "orange", "navy")

    def _create_histogrammer(self):
        self.histogrammer = Ch2Histogrammer(
            name=self.name,
            dtype=self.dtype,
            num_pixel_values=self.num_pixel_values,
            max_pixel_value=self.max_pixel_value,
            channels=2,
            plot_histograms=self.plot_histograms,
            plot_summary=self.plot_summary,
            labels=self.labels,
            colors=self.colors
        )

    def preprocess(self, image):
        return bgr_to_hsv(image)

    def postprocess(self, image):
        return hsv_to_bgr(image)


class LSCorrection(Ch2Correction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.labels = ("H", "L", "S")
        self.colors = ("hotpink", "navy", "orange")

    def _create_histogrammer(self):
        self.histogrammer = Ch2Histogrammer(
            name=self.name,
            dtype=self.dtype,
            num_pixel_values=self.num_pixel_values,
            max_pixel_value=self.max_pixel_value,
            channels=2,
            plot_histograms=self.plot_histograms,
            plot_summary=self.plot_summary,
            labels=self.labels,
            colors=self.colors
        )

    def preprocess(self, image):
        return bgr_to_hls(image)

    def postprocess(self, image):
        return hls_to_bgr(image)


class LABCorrection(Ch1Correction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.labels = ("L", "A", "B")
        self.colors = ("black", "yellow", "red")

    def _create_histogrammer(self):
        self.histogrammer = Ch1Histogrammer(
            name=self.name,
            dtype=self.dtype,
            num_pixel_values=self.num_pixel_values,
            max_pixel_value=self.max_pixel_value,
            channels=2,
            plot_histograms=self.plot_histograms,
            plot_summary=self.plot_summary,
            labels=self.labels,
            colors=self.colors
        )

    def preprocess(self, image):
        return bgr_to_lab(image)

    def postprocess(self, image):
        return lab_to_bgr(image)


class BalanceFrames(SubAction):
    def __init__(self, name='', enabled=True, **kwargs):
        super().__init__(name, enabled)
        self.process = None
        self.shape = None
        default_params = DEFAULTS['balance_frames_params']
        self.corr_map = kwargs.get('corr_map', default_params['corr_map'])
        self.subsample = kwargs.get('subsample', default_params['subsample'])
        self.fast_subsampling = kwargs.get('fast_subsampling', default_params['fast_subsampling'])
        self.channel = kwargs.get('channel', default_params['channel'])
        self.mask_size = kwargs.get('mask_size', default_params['mask_size'])
        self.plot_summary = kwargs.get('plot_summary', False)
        self.plot_histograms = kwargs.get('plot_histograms', False)
        if self.subsample == -1:
            self.subsample = (1 if self.corr_map == constants.BALANCE_MATCH_HIST
                              else DEFAULTS['balance_frames_params']['subsample'])
        correction_class = {
            constants.BALANCE_LUMI: LumiCorrection,
            constants.BALANCE_RGB: RGBCorrection,
            constants.BALANCE_HSV: SVCorrection,
            constants.BALANCE_HLS: LSCorrection,
            constants.BALANCE_LAB: LABCorrection,
        }.get(self.channel, None)
        if correction_class is None:
            raise InvalidOptionError("channel", self.channel)
        self.correction = correction_class(
            name=self.name,
            mask_size=self.mask_size,
            subsample=self.subsample,
            fast_subsampling=self.fast_subsampling,
            corr_map=self.corr_map,
            plot_histograms=self.plot_histograms,
            plot_summary=self.plot_summary
        )

    def begin(self, process):
        self.process = process
        self.correction.process = process
        if self.process.num_input_filepaths() == 0:
            return
        img = read_img(self.process.input_filepath(process.ref_idx))
        self.shape = img.shape
        # colour balance operates on RGB only; the alpha channel (if any) is
        # carried through untouched by run_frame().
        self.correction.begin(drop_alpha(img), self.process.total_action_counts,
                              process.ref_idx)

    def end(self):
        self.process.print_message(' ' * 60)
        self.correction.end(self.process.ref_idx)
        if self.plot_summary and self.mask_size > 0:
            shape = self.shape[:2]
            img = np.zeros(shape)
            mask_radius = int(min(*shape) * self.mask_size / 2)
            cv2.circle(img, (shape[1] // 2, shape[0] // 2), mask_radius, 255, -1)
            fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
            plt.title('Image balance mask')
            plt.imshow(img, 'gray')
            self.correction.histogrammer.save_summary_plot(fig, "mask")

    def run_frame(self, idx, _ref_idx, image):
        if idx != self.process.ref_idx:
            self.process.print_message(
                color_str(f'{self.process.frame_str(idx)}: balance image',
                          constants.LOG_COLOR_LEVEL_3))
        color, alpha = split_alpha(image)
        color = self.correction.apply_correction(idx, color)
        return merge_alpha(color, alpha)
