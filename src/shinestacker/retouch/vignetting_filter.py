# pylint: disable=W0221, R0902, R0913, R0917
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSpinBox, QCheckBox, QLabel, QHBoxLayout, QSlider, QComboBox
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. algorithms.vignetting import correct_vignetting
from .base_filter import OneSliderBaseFilter


class VignettingFilter(OneSliderBaseFilter):
    def __init__(self, name, parent, image_viewer, layer_collection, undo_manager):
        super().__init__(name, parent, image_viewer, layer_collection, undo_manager,
                         0.0, 1.0, 0.90, "Vignetting correction",
                         allow_partial_preview=False, preview_at_startup=False)
        self.subsample_box = None
        self.fast_subsampling_check = None
        self.r_steps_box = None
        self.threshold_slider = None
        self.threshold_label = None
        self.threshold_max_range = 500
        self.threshold_max_value = 128.0
        self.threshold_initial_value = DEFAULTS['vignetting_params']['black_threshold']
        self.threshold_format = "{:.1f}"

    def get_subsample_factor(self):
        return constants.FIELD_SUBSAMPLE_VALUES[
            constants.FIELD_SUBSAMPLE_OPTIONS.index(self.subsample_box.currentText())]

    def apply(self, image, strength):
        return correct_vignetting(image, max_correction=strength,
                                  black_threshold=self.threshold_value(
                                      self.threshold_slider.value()),
                                  r_steps=self.r_steps_box.value(),
                                  subsample=self.get_subsample_factor(),
                                  fast_subsampling=True)

    def add_widgets(self, layout, dlg):
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Threshold:"))
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(0, self.threshold_max_range)
        self.threshold_slider.setValue(
            int(self.threshold_initial_value /
                self.threshold_max_value * self.threshold_max_range))
        self.threshold_slider.valueChanged.connect(self.threshold_changed)
        self.threshold_label = QLabel(self.threshold_format.format(self.threshold_initial_value))
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_label)
        layout.addLayout(threshold_layout)
        subsample_layout = QHBoxLayout()
        subsample_label = QLabel("Subsample:")
        self.subsample_box = QComboBox()
        self.subsample_box.addItems(constants.FIELD_SUBSAMPLE_OPTIONS)
        self.subsample_box.setFixedWidth(150)
        self.subsample_box.currentTextChanged.connect(self.threshold_changed)
        self.fast_subsampling_check = QCheckBox("Fast subsampling")
        self.fast_subsampling_check.setChecked(DEFAULTS['vignetting_params']['fast_subsampling'])
        r_steps_label = QLabel("Radial steps:")
        self.r_steps_box = QSpinBox()
        self.r_steps_box.setFixedWidth(50)
        self.r_steps_box.setRange(1, 200)
        self.r_steps_box.setValue(DEFAULTS['vignetting_params']['r_steps'])
        self.r_steps_box.valueChanged.connect(self.param_changed)
        subsample_layout.addWidget(subsample_label)
        subsample_layout.addWidget(self.subsample_box)
        subsample_layout.addWidget(r_steps_label)
        subsample_layout.addWidget(self.r_steps_box)
        subsample_layout.addStretch(1)
        layout.addLayout(subsample_layout)
        layout.addWidget(self.fast_subsampling_check)

    def threshold_value(self, val):
        return float(val) / self.threshold_max_range * self.threshold_max_value

    def threshold_changed(self, val):
        float_val = self.threshold_value(val)
        self.threshold_label.setText(self.threshold_format.format(float_val))
        self.param_changed(val)
