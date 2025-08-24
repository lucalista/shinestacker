# pylint: disable=C0114, C0115, C0116, E0611, W0221, R0913, R0914, R0917, R0902
from PySide6.QtWidgets import (QHBoxLayout, QPushButton, QFrame, QVBoxLayout, QLabel, QDialog,
                               QApplication, QSlider, QDialogButtonBox, QLineEdit)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor
from .. algorithms.white_balance import white_balance_from_rgb
from .base_filter import BaseFilter


class WhiteBalanceFilter(BaseFilter):
    def __init__(self, name, editor):
        super().__init__(name, editor, preview_at_startup=True)
        self.max_range = 255
        self.initial_val = (128, 128, 128)
        self.sliders = {}
        self.value_labels = {}
        self.rgb_hex = None
        self.color_preview = None
        self.preview_timer = None
        self.original_mouse_press = None

    def setup_ui(self, dlg, layout, do_preview, restore_original, init_val=None):
        if init_val:
            self.initial_val = init_val
        dlg.setWindowTitle("White Balance")
        dlg.setMinimumWidth(600)
        row_layout = QHBoxLayout()
        self.color_preview = QFrame()
        self.color_preview.setFixedHeight(80)
        self.color_preview.setFixedWidth(80)
        self.color_preview.setStyleSheet(f"background-color: rgb{self.initial_val};")
        row_layout.addWidget(self.color_preview)
        sliders_layout = QVBoxLayout()
        for name in ("R", "G", "B"):
            row = QHBoxLayout()
            label = QLabel(f"{name}:")
            row.addWidget(label)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, self.max_range)
            slider.setValue(self.initial_val[["R", "G", "B"].index(name)])
            row.addWidget(slider)
            val_label = QLabel(str(self.initial_val[["R", "G", "B"].index(name)]))
            row.addWidget(val_label)
            sliders_layout.addLayout(row)
            self.sliders[name] = slider
            self.value_labels[name] = val_label
        row_layout.addLayout(sliders_layout)
        layout.addLayout(row_layout)

        rbg_layout = QHBoxLayout()
        rbg_layout.addWidget(QLabel("RBG hex:"))
        self.rgb_hex = QLineEdit(self.hex_color(self.initial_val))
        self.rgb_hex.setFixedWidth(60)
        self.rgb_hex.textChanged.connect(self.on_rgb_change)
        rbg_layout.addWidget(self.rgb_hex)
        rbg_layout.addStretch(1)
        layout.addLayout(rbg_layout)

        pick_button = QPushButton("Pick Color")
        layout.addWidget(pick_button)
        self.create_base_widgets(
            layout,
            QDialogButtonBox.Ok | QDialogButtonBox.Reset | QDialogButtonBox.Cancel,
            200, dlg)
        for slider in self.sliders.values():
            slider.valueChanged.connect(self.on_slider_change)
        self.preview_timer.timeout.connect(do_preview)
        self.editor.connect_preview_toggle(self.preview_check, do_preview, restore_original)
        pick_button.clicked.connect(self.start_color_pick)
        self.button_box.accepted.connect(dlg.accept)
        self.button_box.rejected.connect(dlg.reject)
        self.button_box.button(QDialogButtonBox.Reset).clicked.connect(self.reset_rgb)
        QTimer.singleShot(0, do_preview)

    def hex_color(self, val):
        return "".join([f"{int(c):0>2X}" for c in val])

    def apply_preview(self, rgb):
        self.color_preview.setStyleSheet(f"background-color: rgb{tuple(rgb)};")
        if self.preview_timer:
            self.preview_timer.start()

    def on_slider_change(self):
        for name in ("R", "G", "B"):
            self.value_labels[name].setText(str(self.sliders[name].value()))
        rgb = tuple(self.sliders[n].value() for n in ("R", "G", "B"))
        self.rgb_hex.blockSignals(True)
        self.rgb_hex.setText(self.hex_color(rgb))
        self.rgb_hex.blockSignals(False)
        self.apply_preview(rgb)

    def on_rgb_change(self):
        txt = self.rgb_hex.text()
        if len(txt) != 6:
            return
        rgb = [int(txt[i:i + 2], 16) for i in range(0, 6, 2)]
        for name, c in zip(("R", "G", "B"), rgb):
            self.sliders[name].blockSignals(True)
            self.sliders[name].setValue(c)
            self.sliders[name].blockSignals(False)
            self.value_labels[name].setText(str(c))
        self.apply_preview(rgb)

    def start_color_pick(self):
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QDialog) and widget.isVisible():
                widget.hide()
                widget.reject()
                break
        self.editor.image_viewer.set_cursor_style('outline')
        if self.editor.image_viewer.brush_cursor:
            self.editor.image_viewer.brush_cursor.hide()
        self.editor.brush_preview.hide()
        QApplication.setOverrideCursor(QCursor(Qt.CrossCursor))
        self.editor.image_viewer.setCursor(Qt.CrossCursor)
        self.original_mouse_press = self.editor.image_viewer.mousePressEvent
        self.editor.image_viewer.mousePressEvent = self.pick_color_from_click

    def pick_color_from_click(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            bgr = self.editor.get_pixel_color_at(pos, radius=int(self.editor.brush.size))
            rgb = (bgr[2], bgr[1], bgr[0])
            QApplication.restoreOverrideCursor()
            self.editor.image_viewer.unsetCursor()
            self.editor.image_viewer.mousePressEvent = self.original_mouse_press
            self.editor.image_viewer.brush_cursor.show()
            self.editor.brush_preview.show()
            new_filter = WhiteBalanceFilter(self.name, self.editor)
            new_filter.run_with_preview(init_val=rgb)

    def reset_rgb(self):
        for name, slider in self.sliders.items():
            slider.setValue(self.initial_val[["R", "G", "B"].index(name)])

    def get_params(self):
        return tuple(self.sliders[n].value() for n in ("R", "G", "B"))

    def apply(self, image, r, g, b):
        return white_balance_from_rgb(image, (r, g, b))
