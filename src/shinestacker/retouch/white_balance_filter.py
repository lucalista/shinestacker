# pylint: disable=E0611, W0221, R0913, R0914, R0917, R0902
import numpy as np
from PySide6.QtWidgets import (QHBoxLayout, QPushButton, QFrame, QVBoxLayout, QLabel, QDialog,
                               QApplication, QDialogButtonBox, QLineEdit)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor
from .. algorithms.white_balance import white_balance_from_rgb
from .base_filter import BaseFilter
from .reset_slider import ResetSlider


class WhiteBalanceFilter(BaseFilter):
    def __init__(self, name, parent, image_viewer, layer_collection, undo_manager):
        super().__init__(name, parent, image_viewer, layer_collection, undo_manager,
                         preview_at_startup=True)
        self.max_range = 255
        self.initial_val = (128, 128, 128)
        self.sliders = {}
        self.value_labels = {}
        self.rgb_hex = None
        self.color_preview = None
        self.preview_timer = None
        self.original_mouse_press = None
        self.original_cursor_style = None

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
            init_val = self.initial_val[["R", "G", "B"].index(name)]
            slider = ResetSlider(init_val, Qt.Horizontal)
            slider.setRange(0, self.max_range)
            slider.setValue(self.initial_val[["R", "G", "B"].index(name)])
            row.addWidget(slider)
            val_label = QLabel(str(init_val))
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
        self.connect_preview_toggle(self.preview_check, do_preview, restore_original)
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
        self.original_cursor_style = self.image_viewer.get_cursor_style()
        self.image_viewer.set_cursor_style('outline')
        self.image_viewer.hide_brush_cursor()
        self.image_viewer.hide_brush_preview()
        QApplication.setOverrideCursor(QCursor(Qt.CrossCursor))
        self.image_viewer.strategy.setCursor(Qt.CrossCursor)
        self.original_mouse_press = self.image_viewer.strategy.get_mouse_callbacks()
        self.image_viewer.strategy.set_mouse_callbacks(self.pick_color_from_click)
        self.filter_gui_set_enabled_requested.emit(False)

    def pick_color_from_click(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            bgr = self.get_pixel_color_at(
                pos, radius=int(self.image_viewer.get_brush().size))
            rgb = (bgr[2], bgr[1], bgr[0])
            QApplication.restoreOverrideCursor()
            self.image_viewer.unsetCursor()
            self.image_viewer.strategy.set_mouse_callbacks(self.original_mouse_press)
            self.filter_gui_set_enabled_requested.emit(True)
            self.image_viewer.hide_brush_preview()
            new_filter = WhiteBalanceFilter(
                self.name, self.parent(), self.image_viewer, self.layer_collection,
                self.undo_manager)
            new_filter.run_with_preview(init_val=rgb)
            self.image_viewer.set_cursor_style(self.original_cursor_style)
            self.image_viewer.show_brush_cursor()
            self.image_viewer.show_brush_preview()

    def reset_rgb(self):
        for name, slider in self.sliders.items():
            slider.setValue(self.initial_val[["R", "G", "B"].index(name)])

    def get_params(self):
        return tuple(self.sliders[n].value() for n in ("R", "G", "B"))

    def apply(self, image, r, g, b):
        return white_balance_from_rgb(image, (r, g, b))

    def get_pixel_color_at(self, pos, radius=None):
        item_pos = self.image_viewer.strategy.position_on_image(pos)
        x = int(item_pos.x())
        y = int(item_pos.y())
        master_layer = self.master_layer()
        if (0 <= x < self.master_layer().shape[1]) and \
           (0 <= y < self.master_layer().shape[0]):
            if radius is None:
                radius = int(self.brush.size)
            if radius > 0:
                y_indices, x_indices = np.ogrid[-radius:radius + 1, -radius:radius + 1]
                mask = x_indices**2 + y_indices**2 <= radius**2
                x0 = max(0, x - radius)
                x1 = min(master_layer.shape[1], x + radius + 1)
                y0 = max(0, y - radius)
                y1 = min(master_layer.shape[0], y + radius + 1)
                mask = mask[radius - (y - y0): radius + (y1 - y),
                            radius - (x - x0): radius + (x1 - x)]
                region = master_layer[y0:y1, x0:x1]
                if region.size == 0:
                    pixel = master_layer[y, x]
                else:
                    if region.ndim == 3:
                        pixel = [region[:, :, c][mask].mean() for c in range(region.shape[2])]
                    else:
                        pixel = region[mask].mean()
            else:
                pixel = self.master_layer()[y, x]
            if np.isscalar(pixel):
                pixel = [pixel, pixel, pixel]
            pixel = [np.float32(x) for x in pixel]
            if master_layer.dtype == np.uint16:
                pixel = [x / 256.0 for x in pixel]
            return tuple(int(v) for v in pixel)
        return (0, 0, 0)
