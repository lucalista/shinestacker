# pylint: disable=E0611, W0221, R0902, R0914, R0913, R0917
from .. algorithms.sharpen import unsharp_mask
from .base_filter import BaseFilter


class UnsharpMaskFilter(BaseFilter):
    def __init__(self, name, parent, image_viewer, layer_collection, undo_manager):
        super().__init__(name, parent, image_viewer, layer_collection, undo_manager,
                         preview_at_startup=True)
        self.min_radius = 0.0
        self.max_radius = 4.0
        self.min_amount = 0.0
        self.max_amount = 3.0
        self.min_threshold = 0.0
        self.max_threshold = 64.0
        self.initial_radius = 1.0
        self.initial_amount = 0.5
        self.initial_threshold = 0.0
        self.radius_slider = None
        self.amount_slider = None
        self.threshold_slider = None

    def setup_ui(self, dlg, layout, do_preview, restore_original, **kwargs):
        dlg.setWindowTitle("Unsharp Mask")
        dlg.setMinimumWidth(600)
        params = {
            "Radius": (self.min_radius, self.max_radius, self.initial_radius, "{:.2f} px"),
            "Amount": (self.min_amount, self.max_amount, self.initial_amount, "{:.1%}"),
            "Threshold": (self.min_threshold, self.max_threshold, self.initial_threshold, "{:.2f}")
        }

        def set_slider(name, slider):
            if name == "Radius":
                self.radius_slider = slider
            elif name == "Amount":
                self.amount_slider = slider
            elif name == "Threshold":
                self.threshold_slider = slider

        self.value_labels = self.create_sliders(params, dlg, layout, set_slider)

        self.radius_slider.valueChanged.connect(
            lambda v: self.update_value("Radius", v, self.max_radius, params["Radius"][3]))
        self.amount_slider.valueChanged.connect(
            lambda v: self.update_value("Amount", v, self.max_amount, params["Amount"][3]))
        self.threshold_slider.valueChanged.connect(
            lambda v: self.update_value("Threshold", v, self.max_threshold, params["Threshold"][3]))
        self.set_timer(do_preview, restore_original, dlg)

    def get_params(self):
        return (
            max(0.01, self.max_radius * self.radius_slider.value() / self.max_range),
            self.max_amount * self.amount_slider.value() / self.max_range,
            self.max_threshold * self.threshold_slider.value() / self.max_range
        )

    def apply(self, image, radius, amount, threshold):
        return unsharp_mask(image, radius, amount, threshold)
