# pylint: disable=E0611, W0221, R0913, R0917, R0902, R0914, E1101
from abc import abstractmethod
import math
import cv2
from .base_filter import BaseFilter
from .. algorithms.utils import bgr_to_hls, hls_to_bgr
from .. algorithms.corrections import gamma_correction, contrast_correction


class GammaSCurveFilter(BaseFilter):
    def __init__(
            self, name, parent, image_viewer, layer_collection, undo_manager,
            window_title, gamma_label, scurve_label):
        super().__init__(name, parent, image_viewer, layer_collection, undo_manager,
                         preview_at_startup=True)
        self.window_title = window_title
        self.gamma_label = gamma_label
        self.scurve_label = scurve_label
        self.min_gamma = -1
        self.max_gamma = +1
        self.initial_gamma = 0
        self.min_scurve = -1
        self.max_scurve = 1
        self.initial_scurve = 0
        self.lumi_slider = None
        self.contrast_slider = None

    @abstractmethod
    def apply(self, image, *params):
        pass

    def setup_ui(self, dlg, layout, do_preview, restore_original, **kwargs):
        dlg.setWindowTitle(self.window_title)
        dlg.setMinimumWidth(600)
        params = {
            self.gamma_label: (self.min_gamma, self.max_gamma, self.initial_gamma, "{:.1%}"),
            self.scurve_label: (self.min_scurve, self.max_scurve, self.initial_scurve, "{:.1%}"),
        }

        def set_slider(name, slider):
            if name == self.gamma_label:
                self.lumi_slider = slider
            elif name == self.scurve_label:
                self.contrast_slider = slider

        value_labels = self.create_sliders(params, dlg, layout, set_slider)

        def update_value(name, slider_value, min_val, max_val, fmt):
            value = self.value_from_slider(slider_value, min_val, max_val)
            value_labels[name].setText(fmt.format(value))
            if self.preview_check.isChecked():
                self.preview_timer.start()

        self.lumi_slider.valueChanged.connect(
            lambda v: update_value(
                self.gamma_label, v, self.min_gamma,
                self.max_gamma, params[self.gamma_label][3]))
        self.contrast_slider.valueChanged.connect(
            lambda v: update_value(
                self.scurve_label, v, self.min_scurve,
                self.max_scurve, params[self.scurve_label][3]))
        self.set_timer(do_preview, restore_original, dlg)

    def get_params(self):
        return (
            self.value_from_slider(
                self.lumi_slider.value(), self.min_gamma, self.max_gamma),
            self.value_from_slider(
                self.contrast_slider.value(), self.min_scurve, self.max_scurve)
        )


class LumiContrastFilter(GammaSCurveFilter):
    def __init__(self, name, parent, image_viewer, layer_collection, undo_manager):
        super().__init__(
            name, parent, image_viewer, layer_collection, undo_manager,
            "Luminosity, Contrast", "Luminosity", "Constrat")

    def apply(self, image, luminosity, contrast):
        img_corr = contrast_correction(image, 0.5 * contrast)
        img_corr = gamma_correction(img_corr, math.exp(0.5 * luminosity))
        return img_corr


class SaturationVibranceFilter(GammaSCurveFilter):
    def __init__(self, name, parent, image_viewer, layer_collection, undo_manager):
        super().__init__(
            name, parent, image_viewer, layer_collection, undo_manager,
            "Saturation, Vibrance", "Saturation", "Vibrance")

    def apply(self, image, stauration, vibrance):
        h, l, s = cv2.split(bgr_to_hls(image))
        s = contrast_correction(s, - vibrance)
        s = gamma_correction(s, math.exp(0.5 * stauration))
        return hls_to_bgr(cv2.merge([h, l, s]))
