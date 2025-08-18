# pylint: disable=C0114, C0115, C0116, E0611, W0221, R0913, R0914, R0917
from PySide6.QtWidgets import (QHBoxLayout, QPushButton, QFrame, QVBoxLayout, QLabel, QDialog,
                               QApplication, QSlider, QDialogButtonBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor
from .. algorithms.white_balance import white_balance_from_rgb
from .base_filter import BaseFilter


class WhiteBalanceFilter(BaseFilter):
    def __init__(self, editor):
        super().__init__(editor)
        self.max_range = 255
        self.initial_val = (128, 128, 128)
        self.sliders = {}
        self.value_labels = {}
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
        pick_button = QPushButton("Pick Color")
        layout.addWidget(pick_button)
        preview_check, self.preview_timer, button_box = self.create_base_widgets(
            layout,
            QDialogButtonBox.Ok | QDialogButtonBox.Reset | QDialogButtonBox.Cancel,
            200)
        for slider in self.sliders.values():
            slider.valueChanged.connect(self.on_slider_change)
        self.preview_timer.timeout.connect(do_preview)
        self.editor.connect_preview_toggle(preview_check, do_preview, restore_original)
        pick_button.clicked.connect(self.start_color_pick)
        button_box.accepted.connect(dlg.accept)
        button_box.rejected.connect(dlg.reject)
        button_box.button(QDialogButtonBox.Reset).clicked.connect(self.reset_rgb)
        QTimer.singleShot(0, do_preview)

    def on_slider_change(self):
        for name in ("R", "G", "B"):
            self.value_labels[name].setText(str(self.sliders[name].value()))
        rgb = tuple(self.sliders[n].value() for n in ("R", "G", "B"))
        self.color_preview.setStyleSheet(f"background-color: rgb{rgb};")
        if self.preview_timer:
            self.preview_timer.start()

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
            new_filter = WhiteBalanceFilter(self.editor)
            new_filter.run_with_preview(init_val=rgb)

    def reset_rgb(self):
        for name, slider in self.sliders.items():
            slider.setValue(self.initial_val[["R", "G", "B"].index(name)])

    def get_params(self):
        return tuple(self.sliders[n].value() for n in ("R", "G", "B"))

    def apply(self, image, r, g, b):
        return white_balance_from_rgb(image, (r, g, b))
