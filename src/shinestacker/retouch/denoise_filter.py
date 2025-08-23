# pylint: disable=C0114, C0115, C0116, E0611, W0221
from .base_filter import OneSliderBaseFilter
from .. algorithms.denoise import denoise


class DenoiseFilter(OneSliderBaseFilter):
    def __init__(self, name, editor):
        super().__init__(name, editor, 10.0, 2.5, "Denoise",
                         allow_partial_preview=True, preview_at_startup=False)

    def apply(self, image, strength):
        return denoise(image, strength)
