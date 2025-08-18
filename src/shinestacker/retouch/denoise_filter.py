# pylint: disable=C0114, C0115, C0116, E0611, W0221
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QDialogButtonBox
from PySide6.QtCore import Qt
from .base_filter import BaseFilter
from .. algorithms.denoise import denoise


class DenoiseFilter(BaseFilter):
    def __init__(self, editor):
        super().__init__(editor)
        self.max_range = 500.0
        self.max_value = 10.00
        self.initial_value = 2.5
        self.slider = None

    def setup_ui(self, dlg, layout, do_preview, restore_original, **kwargs):
        dlg.setWindowTitle("Denoise")
        dlg.setMinimumWidth(600)
        slider_layout = QHBoxLayout()
        slider_local = QSlider(Qt.Horizontal)
        slider_local.setRange(0, self.max_range)
        slider_local.setValue(int(self.initial_value / self.max_value * self.max_range))
        slider_layout.addWidget(slider_local)
        value_label = QLabel(f"{self.max_value:.2f}")
        slider_layout.addWidget(value_label)
        layout.addLayout(slider_layout)
        preview_check, preview_timer, button_box = self.create_base_widgets(
            layout, QDialogButtonBox.Ok | QDialogButtonBox.Cancel, 200)

        def do_preview_delayed():
            preview_timer.start()

        preview_timer.timeout.connect(do_preview)

        def slider_changed(val):
            float_val = self.max_value * float(val) / self.max_range
            value_label.setText(f"{float_val:.2f}")
            if preview_check.isChecked():
                do_preview_delayed()

        slider_local.valueChanged.connect(slider_changed)
        self.editor.connect_preview_toggle(preview_check, do_preview_delayed, restore_original)
        button_box.accepted.connect(dlg.accept)
        button_box.rejected.connect(dlg.reject)
        self.slider = slider_local

    def get_params(self):
        return (self.max_value * self.slider.value() / self.max_range,)

    def apply(self, image, strength):
        return denoise(image, strength)
