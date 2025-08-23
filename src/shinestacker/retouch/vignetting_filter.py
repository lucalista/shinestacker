# pylint: disable=C0114, C0115, C0116, E0611, W0221
from PySide6.QtWidgets import QSpinBox, QCheckBox, QLabel, QHBoxLayout
from .. config.constants import constants
from .. algorithms.vignetting import correct_vignetting
from .base_filter import OneSliderBaseFilter


class VignettingFilter(OneSliderBaseFilter):
    def __init__(self, name, editor):
        super().__init__(name, editor, 1.0, 0.90, "Vignetting correction",
                         allow_partial_preview=False, preview_at_startup=False)
        self.subsample_box = None
        self.fast_subsampling_check = None

    def apply(self, image, strength):
        return correct_vignetting(image, max_correction=strength,
                                  subsample=self.subsample_box.value(),
                                  fast_subsampling=True)

    def add_widgets(self, layout, dlg):
        subsample_layout = QHBoxLayout()
        subsample_label = QLabel("Subsample:")
        self.subsample_box = QSpinBox()
        self.subsample_box.setFixedWidth(50)
        self.subsample_box.setRange(1, 50)
        self.subsample_box.setValue(constants.DEFAULT_VIGN_SUBSAMPLE)
        self.subsample_box.valueChanged.connect(self.config_changed)
        self.fast_subsampling_check = QCheckBox("Fast subsampling")
        self.fast_subsampling_check.setChecked(constants.DEFAULT_VIGN_FAST_SUBSAMPLING)
        subsample_layout.addWidget(subsample_label)
        subsample_layout.addWidget(self.subsample_box)
        subsample_layout.addWidget(self.fast_subsampling_check)
        subsample_layout.addStretch(1)
        layout.addLayout(subsample_layout)
