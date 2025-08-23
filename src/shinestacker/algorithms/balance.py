# pylint: disable=C0114, C0115, C0116, E1101, R0902, E1128, E0606, W0640, R0913, R0917
import numpy as np
import cv2
import matplotlib.pyplot as plt
from scipy.optimize import bisect
from scipy.interpolate import interp1d
from .. config.constants import constants
from .. core.exceptions import InvalidOptionError
from .. core.colors import color_str
from .utils import read_img, save_plot, img_subsample
from .stack_framework import SubAction


class CorrectionMapBase:
    def __init__(self, dtype, ref_hist, intensity_interval=None):
        intensity_interval = {**constants.DEFAULT_INTENSITY_INTERVAL, **(intensity_interval or {})}
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
                correction[c - 1],
                self.reference[c - 1], chans[c]
            ) for c in range(1, 3)]
        elif self.channels == 3:
            ch_out = [self.apply_lut(
                correction[c],
                self.reference[c], chans[c]
            ) for c in range(3)]
        return cv2.merge(ch_out)

    def correction_size(self, correction):
        return correction


class MatchHist(CorrectionMapBase):
    def __init__(self, dtype, ref_hist, intensity_interval=None):
        CorrectionMapBase.__init__(self, dtype, ref_hist, intensity_interval)
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
        CorrectionMapBase.__init__(self, dtype, ref_hist, intensity_interval)
        self.reference = [self.mid_val(self.id_lut, h) for h in ref_hist]

    def mid_val(self, lut, h):
        return np.average(lut[self.i_min:self.i_end], weights=h.flatten()[self.i_min:self.i_end])


class GammaMap(CorrectionMap):
    def __init__(self, dtype, ref_hist, intensity_interval=None):
        CorrectionMap.__init__(self, dtype, ref_hist, intensity_interval)

    def correction(self, hist):
        return [bisect(lambda x: self.mid_val(self.lut(x), h) - r, 0.1, 5)
                for h, r in zip(hist, self.reference)]

    def lut(self, correction, _reference=None):
        gamma_inv = 1.0 / correction
        ar = np.arange(0, self.num_pixel_values)
        corr_lut = ((ar / self.max_pixel_value) ** gamma_inv) * self.max_pixel_value
        return corr_lut.astype(self.dtype)


class LinearMap(CorrectionMap):
    def __init__(self, dtype, ref_hist, intensity_interval=None):
        CorrectionMap.__init__(self, dtype, ref_hist, intensity_interval)

    def lut(self, correction, _reference=None):
        ar = np.arange(0, self.num_pixel_values)
        return np.clip(ar * correction, 0, self.max_pixel_value).astype(self.dtype)

    def correction(self, hist):
        return [r / self.mid_val(self.id_lut, h) for h, r in zip(hist, self.reference)]


class Correction:
    def __init__(self, channels, mask_size=0, intensity_interval=None,
                 subsample=-1, fast_subsampling=constants.DEFAULT_BALANCE_FAST_SUBSAMPLING,
                 corr_map=constants.DEFAULT_CORR_MAP,
                 plot_histograms=False, plot_summary=False):
        self.mask_size = mask_size
        self.intensity_interval = intensity_interval
        self.plot_histograms = plot_histograms
        self.plot_summary = plot_summary
        self.subsample = constants.DEFAULT_BALANCE_SUBSAMPLE if subsample == -1 else subsample
        self.fast_subsampling = fast_subsampling
        self.corr_map = corr_map
        self.channels = channels
        self.dtype = None
        self.num_pixel_values = None
        self. max_pixel_value = None
        self.corrections = None
        self.process = None

    def begin(self, ref_image, size, ref_idx):
        self.dtype = ref_image.dtype
        self.num_pixel_values = constants.NUM_UINT8 if ref_image.dtype == np.uint8 \
            else constants.NUM_UINT16
        self.max_pixel_value = self.num_pixel_values - 1
        hist = self.get_hist(self.preprocess(ref_image), ref_idx)
        if self.corr_map == constants.BALANCE_LINEAR:
            self.corr_map = LinearMap(self.dtype, hist, self.intensity_interval)
        elif self.corr_map == constants.BALANCE_GAMMA:
            self.corr_map = GammaMap(self.dtype, hist, self.intensity_interval)
        elif self.corr_map == constants.BALANCE_MATCH_HIST:
            self.corr_map = MatchHist(self.dtype, hist, self.intensity_interval)
        else:
            raise InvalidOptionError("corr_map", self.corr_map)
        self.corrections = np.ones((size, self.channels))

    def calc_hist_1ch(self, image):
        img_sub = image if self.subsample == 1 \
            else img_subsample(image, self.subsample, self.fast_subsampling)
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
        hist, _bins = np.histogram(
            image_sel,
            bins=np.linspace(-0.5, self.num_pixel_values - 0.5,
                             self.num_pixel_values + 1)
        )
        return hist

    def balance(self, image, idx):
        correction = self.corr_map.correction(self.get_hist(image, idx))
        return correction, self.corr_map.adjust(image, correction)

    def get_hist(self, _image, _idx):
        return None

    def end(self, _ref_idx):
        pass

    def apply_correction(self, idx, image):
        image = self.preprocess(image)
        correction, image = self.balance(image, idx)
        image = self.postprocess(image)
        self.corrections[idx] = self.corr_map.correction_size(correction)
        return image

    def preprocess(self, image):
        return image

    def postprocess(self, image):
        return image

    def histo_plot(self, ax, hist, x_label, color, alpha=1):
        ax.set_ylabel("# of pixels")
        ax.set_xlabel(x_label)
        ax.set_xlim([0, self.num_pixel_values])
        ax.set_yscale('log')
        ax.plot(hist, color=color, alpha=alpha)

    def save_plot(self, idx):
        idx_str = f"{idx:04d}"
        plot_path = f"{self.process.working_path}/" \
            f"{self.process.plot_path}/{self.process.name}-hist-{idx_str}.pdf"
        save_plot(plot_path)
        plt.close('all')
        self.process.callback(
            'save_plot',
            self.process.id, f"{self.process.name}: balance\nframe {idx_str}",
            plot_path
        )

    def save_summary_plot(self, name='balance'):
        plot_path = f"{self.process.working_path}/" \
            f"{self.process.plot_path}/{self.process.name}-{name}.pdf"
        save_plot(plot_path)
        plt.close('all')
        self.process.callback(
            'save_plot', self.process.id,
            f"{self.process.name}: {name}", plot_path
        )


class LumiCorrection(Correction):
    def __init__(self, **kwargs):
        Correction.__init__(self, 1, **kwargs)

    def get_hist(self, image, idx):
        hist = self.calc_hist_1ch(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        chans = cv2.split(image)
        colors = ("r", "g", "b")
        if self.plot_histograms:
            _fig, axs = plt.subplots(1, 2, figsize=(10, 5), sharey=True)
            self.histo_plot(axs[0], hist, "pixel luminosity", 'black')
            for (chan, color) in zip(chans, colors):
                hist_col = self.calc_hist_1ch(chan)
                self.histo_plot(axs[1], hist_col, "r,g,b luminosity", color, alpha=0.5)
            plt.xlim(0, self.max_pixel_value)
            self.save_plot(idx)
        return [hist]

    def end(self, ref_idx):
        if self.plot_summary:
            plt.figure(figsize=(10, 5))
            x = np.arange(1, len(self.corrections) + 1, dtype=int)
            y = self.corrections
            plt.plot([ref_idx + 1, ref_idx + 1], [0, 1], color='cornflowerblue',
                     linestyle='--', label='reference frame')
            plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--',
                     label='no correction')
            plt.plot(x, y, color='navy', label='luminosity correction')
            plt.xlabel('frame')
            plt.ylabel('correction')
            plt.legend()
            plt.xlim(x[0], x[-1])
            plt.ylim(0)
            self.save_summary_plot()


class RGBCorrection(Correction):
    def __init__(self, **kwargs):
        Correction.__init__(self, 3, **kwargs)

    def get_hist(self, image, idx):
        hist = [self.calc_hist_1ch(chan) for chan in cv2.split(image)]
        colors = ("r", "g", "b")
        if self.plot_histograms:
            _fig, axs = plt.subplots(1, 3, figsize=(10, 5), sharey=True)
            for c in [2, 1, 0]:
                self.histo_plot(axs[c], hist[c], colors[c] + " luminosity", colors[c])
            plt.xlim(0, self.max_pixel_value)
            self.save_plot(idx)
        return hist

    def end(self, ref_idx):
        if self.plot_summary:
            plt.figure(figsize=(10, 5))
            x = np.arange(1, len(self.corrections) + 1, dtype=int)
            y = self.corrections
            plt.plot([ref_idx + 1, ref_idx + 1], [0, 1], color='cornflowerblue',
                     linestyle='--', label='reference frame')
            plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--',
                     label='no correction')
            plt.plot(x, y[:, 0], color='r', label='R correction')
            plt.plot(x, y[:, 1], color='g', label='G correction')
            plt.plot(x, y[:, 2], color='b', label='B correction')
            plt.xlabel('frame')
            plt.ylabel('correction')
            plt.legend()
            plt.xlim(x[0], x[-1])
            plt.ylim(0)
            self.save_summary_plot()


class Ch2Correction(Correction):
    def __init__(self, **kwargs):
        Correction.__init__(self, 2, **kwargs)

    def preprocess(self, image):
        assert False, 'abstract method'

    def get_hist(self, image, idx):
        hist = [self.calc_hist_1ch(chan) for chan in cv2.split(image)]
        if self.plot_histograms:
            _fig, axs = plt.subplots(1, 3, figsize=(10, 5), sharey=True)
            for c in range(3):
                self.histo_plot(axs[c], hist[c], self.labels[c], self.colors[c])
            plt.xlim(0, self.max_pixel_value)
            self.save_plot(idx)
        return hist[1:]

    def end(self, ref_idx):
        if self.plot_summary:
            plt.figure(figsize=(10, 5))
            x = np.arange(1, len(self.corrections) + 1, dtype=int)
            y = self.corrections
            plt.plot([ref_idx + 1, ref_idx + 1], [0, 1], color='cornflowerblue',
                     linestyle='--', label='reference frame')
            plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--',
                     label='no correction')
            plt.plot(x, y[:, 0], color=self.colors[1], label=self.labels[1] + ' correction')
            plt.plot(x, y[:, 1], color=self.colors[2], label=self.labels[2] + ' correction')
            plt.xlabel('frame')
            plt.ylabel('correction')
            plt.legend()
            plt.xlim(x[0], x[-1])
            plt.ylim(0)
            self.save_summary_plot()


class SVCorrection(Ch2Correction):
    def __init__(self, **kwargs):
        Ch2Correction.__init__(self, **kwargs)
        self.labels = ("H", "S", "V")
        self.colors = ("hotpink", "orange", "navy")

    def preprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    def postprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_HSV2BGR)


class LSCorrection(Ch2Correction):
    def __init__(self, **kwargs):
        Ch2Correction.__init__(self, **kwargs)
        self.labels = ("H", "L", "S")
        self.colors = ("hotpink", "navy", "orange")

    def preprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_BGR2HLS)

    def postprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_HLS2BGR)


class BalanceFrames(SubAction):
    def __init__(self, enabled=True, **kwargs):
        super().__init__(enabled=enabled)
        self.process = None
        self.shape = None
        corr_map = kwargs.get('corr_map', constants.DEFAULT_CORR_MAP)
        subsample = kwargs.get('subsample', constants.DEFAULT_BALANCE_SUBSAMPLE)
        self.fast_subsampling = kwargs.get(
            'fast_subsampling', constants.DEFAULT_BALANCE_FAST_SUBSAMPLING)
        channel = kwargs.pop('channel', constants.DEFAULT_CHANNEL)
        kwargs['subsample'] = (
            1 if corr_map == constants.BALANCE_MATCH_HIST
            else constants.DEFAULT_BALANCE_SUBSAMPLE) if subsample == -1 else subsample
        self.mask_size = kwargs.get('mask_size', 0)
        self.plot_summary = kwargs.get('plot_summary', False)
        if channel == constants.BALANCE_LUMI:
            self.correction = LumiCorrection(**kwargs)
        elif channel == constants.BALANCE_RGB:
            self.correction = RGBCorrection(**kwargs)
        elif channel == constants.BALANCE_HSV:
            self.correction = SVCorrection(**kwargs)
        elif channel == constants.BALANCE_HLS:
            self.correction = LSCorrection(**kwargs)
        else:
            raise InvalidOptionError("channel", channel)

    def begin(self, process):
        self.process = process
        self.correction.process = process
        img = read_img(self.process.input_full_path + "/" + self.process.filenames[process.ref_idx])
        self.shape = img.shape
        self.correction.begin(img, self.process.counts, process.ref_idx)

    def end(self):
        self.process.print_message(' ' * 60)
        self.correction.end(self.process.ref_idx)
        if self.plot_summary and self.mask_size > 0:
            shape = self.shape[:2]
            img = np.zeros(shape)
            mask_radius = int(min(*shape) * self.mask_size / 2)
            cv2.circle(img, (shape[1] // 2, shape[0] // 2), mask_radius, 255, -1)
            plt.figure(figsize=(10, 5))
            plt.title('Mask')
            plt.imshow(img, 'gray')
            self.correction.save_summary_plot("mask")

    def run_frame(self, idx, _ref_idx, image):
        if idx != self.process.ref_idx:
            self.process.sub_message_r(color_str(': balance image', constants.LOG_COLOR_LEVEL_3))
            image = self.correction.apply_correction(idx, image)
        return image
