# pylint: disable=C0114, C0115, C0116, E0611, W0221
from .base_filter import OneSliderBaseFilter
from .. algorithms.vignetting import correct_vignetting


class VignettingFilter(OneSliderBaseFilter):
    def __init__(self, name, editor):
        super().__init__(name, editor, 1.0, 0.95, "Vignetting correction")

    def apply(self, image, strength):
        return correct_vignetting(image, max_correction=strength)
