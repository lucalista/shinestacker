# pylint: disable=E0611, W0221, R0913, R0917
from .base_filter import OneSliderBaseFilter
from .. algorithms.denoise import denoise


class DenoiseFilter(OneSliderBaseFilter):
    def __init__(self, name, parent, image_viewer, layer_collection, undo_manager):
        super().__init__(name, parent, image_viewer, layer_collection, undo_manager,
                         0.0, 10.0, 2.5, "Denoise",
                         allow_partial_preview=True, preview_at_startup=False)

    def apply(self, image, strength):
        return denoise(image, strength)
