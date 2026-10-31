# pylint: disable=E0611, W0221, R0902, R0914, R0913, R0917
from .. algorithms.tonemapping import local_tonemapping
from .base_filter import BaseFilter


class LocalTonemappingFilter(BaseFilter):
    def __init__(self, name, parent, image_viewer, layer_collection, undo_manager):
        super().__init__(name, parent, image_viewer, layer_collection, undo_manager,
                         preview_at_startup=True)
        self.min_amount = 0.0
        self.max_amount = 1.0
        self.initial_amount = 1.0
        self.min_clip_limit = 0.0
        self.max_clip_limit = 5.0
        self.initial_clip_limit = 1.0
        self.min_tile_size = 1
        self.max_tile_size = 64
        self.initial_tile_size = 8
        self.amount_slider = None
        self.clip_limit_slider = None
        self.tile_size_slider = None

    def setup_ui(self, dlg, layout, do_preview, restore_original, **kwargs):
        dlg.setWindowTitle("Local Tonemapping")
        dlg.setMinimumWidth(600)
        params = {
            "Amount": (
                self.min_amount, self.max_amount, self.initial_amount, "{:.1%}"),
            "Clip limit": (
                self.min_clip_limit, self.max_clip_limit, self.initial_clip_limit, "{:.2f}"),
            "Tile size": (
                self.min_tile_size, self.max_tile_size, self.initial_tile_size, "{:.0f}")
        }

        def set_slider(name, slider):
            if name == "Amount":
                self.amount_slider = slider
            elif name == "Clip limit":
                self.clip_limit_slider = slider
            elif name == "Tile size":
                self.tile_size_slider = slider

        self.value_labels = self.create_sliders(params, dlg, layout, set_slider)

        self.amount_slider.valueChanged.connect(
            lambda v: self.update_value("Amount", v, self.max_amount, params["Amount"][3]))
        self.clip_limit_slider.valueChanged.connect(
            lambda v: self.update_value("Clip limit", v, self.max_clip_limit,
                                        params["Clip limit"][3]))
        self.tile_size_slider.valueChanged.connect(
            lambda v: self.update_value("Tile size", v, self.max_tile_size, params["Tile size"][3]))

        self.set_timer(do_preview, restore_original, dlg)

    def get_params(self):
        return (
            self.max_amount * self.amount_slider.value() / self.max_range,
            self.max_clip_limit * self.clip_limit_slider.value() / self.max_range,
            self.min_tile_size + (self.max_tile_size - self.min_tile_size) *
            self.tile_size_slider.value() / self.max_range,
        )

    def apply(self, image, amount, clip_limit, tile_size):
        return local_tonemapping(image, amount, clip_limit, int(tile_size))
