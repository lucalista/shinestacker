# pylint: disable=C0114, C0115, C0116, E0611, W0221, R0902, R0914
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QDialogButtonBox
from PySide6.QtCore import Qt, QTimer
from .. algorithms.sharpen import unsharp_mask
from .base_filter import BaseFilter


class UnsharpMaskFilter(BaseFilter):
    def __init__(self, name, editor):
        super().__init__(name, editor, preview_at_startup=True)
        self.max_range = 500.0
        self.max_radius = 4.0
        self.max_amount = 3.0
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
            "Radius": (self.max_radius, self.initial_radius, "{:.2f}"),
            "Amount": (self.max_amount, self.initial_amount, "{:.1%}"),
            "Threshold": (self.max_threshold, self.initial_threshold, "{:.2f}")
        }
        value_labels = {}
        for name, (max_val, init_val, fmt) in params.items():
            param_layout = QHBoxLayout()
            name_label = QLabel(f"{name}:")
            param_layout.addWidget(name_label)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, self.max_range)
            slider.setValue(int(init_val / max_val * self.max_range))
            param_layout.addWidget(slider)
            value_label = QLabel(fmt.format(init_val))
            param_layout.addWidget(value_label)
            layout.addLayout(param_layout)
            if name == "Radius":
                self.radius_slider = slider
            elif name == "Amount":
                self.amount_slider = slider
            elif name == "Threshold":
                self.threshold_slider = slider
            value_labels[name] = value_label
        self.create_base_widgets(
            layout, QDialogButtonBox.Ok | QDialogButtonBox.Cancel, 200, dlg)

        def update_value(name, value, max_val, fmt):
            float_value = max_val * value / self.max_range
            value_labels[name].setText(fmt.format(float_value))
            if self.preview_check.isChecked():
                self.preview_timer.start()

        self.radius_slider.valueChanged.connect(
            lambda v: update_value("Radius", v, self.max_radius, params["Radius"][2]))
        self.amount_slider.valueChanged.connect(
            lambda v: update_value("Amount", v, self.max_amount, params["Amount"][2]))
        self.threshold_slider.valueChanged.connect(
            lambda v: update_value("Threshold", v, self.max_threshold, params["Threshold"][2]))
        self.preview_timer.timeout.connect(do_preview)
        self.editor.connect_preview_toggle(self.preview_check, do_preview, restore_original)
        self.button_box.accepted.connect(dlg.accept)
        self.button_box.rejected.connect(dlg.reject)
        QTimer.singleShot(0, do_preview)

    def get_params(self):
        return (
            max(0.01, self.max_radius * self.radius_slider.value() / self.max_range),
            self.max_amount * self.amount_slider.value() / self.max_range,
            self.max_threshold * self.threshold_slider.value() / self.max_range
        )

    def apply(self, image, radius, amount, threshold):
        return unsharp_mask(image, radius, amount, threshold)
