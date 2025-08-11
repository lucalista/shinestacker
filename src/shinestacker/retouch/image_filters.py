import numpy as np
from PySide6.QtWidgets import (QHBoxLayout,
                               QPushButton, QFrame, QVBoxLayout, QLabel, QDialog, QApplication, QSlider,
                               QCheckBox, QDialogButtonBox)
from PySide6.QtGui import QCursor
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from .. algorithms.denoise import denoise
from .. algorithms.sharpen import unsharp_mask
from .. algorithms.white_balance import white_balance_from_rgb
from .image_editor import ImageEditor


class ImageFilters(ImageEditor):
    def __init__(self):
        super().__init__()

    def denoise(self):
        max_range = 500.0
        max_value = 5.00
        initial_value = 2.5
        self.master_layer_copy = self.master_layer.copy()
        dlg = QDialog(self)
        dlg.setWindowTitle("Denoise")
        dlg.setMinimumWidth(600)
        layout = QVBoxLayout(dlg)
        slider_layout = QHBoxLayout()
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, max_range)
        slider.setValue(initial_value / max_value * max_range)
        slider_layout.addWidget(slider)
        value_label = QLabel(f"{max_value:.2f}")
        slider_layout.addWidget(value_label)
        layout.addLayout(slider_layout)
        preview_check = QCheckBox("Preview")
        preview_check.setChecked(True)
        layout.addWidget(preview_check)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)
        last_preview_strength = None
        preview_timer = QTimer()
        preview_timer.setSingleShot(True)
        preview_timer.setInterval(200)
        active_worker = None
        last_request_id = 0

        class PreviewWorker(QThread):
            finished = Signal(np.ndarray, int)

            def __init__(self, image, strength, request_id):
                super().__init__()
                self.image = image
                self.strength = strength
                self.request_id = request_id

            def run(self):
                result = denoise(self.image, self.strength)
                self.finished.emit(result, self.request_id)

        def slider_changed(value):
            float_value = max_value * value / max_range
            value_label.setText(f"{float_value:.2f}")
            if preview_check.isChecked():
                nonlocal last_preview_strength
                last_preview_strength = float_value
                preview_timer.start()

        def do_preview():
            nonlocal active_worker, last_request_id
            if last_preview_strength is None:
                return
            if active_worker and active_worker.isRunning():
                active_worker.quit()
                active_worker.wait()
            last_request_id += 1
            current_request_id = last_request_id
            active_worker = PreviewWorker(
                self.master_layer_copy.copy(),
                last_preview_strength,
                current_request_id
            )
            active_worker.finished.connect(
                lambda img, rid: set_preview(img, rid, current_request_id)
            )
            active_worker.start()

        def set_preview(img, request_id, expected_id):
            if request_id != expected_id:
                return
            self.master_layer = img
            self.display_master_layer()
            dlg.activateWindow()
            slider.setFocus()

        def on_preview_toggled(checked):
            nonlocal last_preview_strength
            if checked:
                last_preview_strength = max_value * slider.value() / max_range
                do_preview()
            else:
                self.master_layer = self.master_layer_copy.copy()
                self.display_master_layer()
                dlg.activateWindow()
                slider.setFocus()
                button_box.setFocus()

        slider.valueChanged.connect(slider_changed)
        preview_timer.timeout.connect(do_preview)
        preview_check.stateChanged.connect(on_preview_toggled)
        button_box.accepted.connect(dlg.accept)
        button_box.rejected.connect(dlg.reject)

        def run_initial_preview():
            slider_changed(slider.value())

        QTimer.singleShot(0, run_initial_preview)
        slider.setFocus()
        if dlg.exec_() == QDialog.Accepted:
            strength = max_value * float(slider.value()) / max_range
            h, w = self.master_layer.shape[:2]
            self.undo_manager.extend_undo_area(0, 0, w, h)
            self.undo_manager.save_undo_state(self.master_layer_copy, 'Denoise')
            self.master_layer = denoise(self.master_layer_copy, strength)
            self.master_layer_copy = self.master_layer.copy()
            self.display_master_layer()
            self.update_master_thumbnail()
            self.mark_as_modified()
        else:
            self.master_layer = self.master_layer_copy.copy()
            self.display_master_layer()

    def unsharp_mask(self):
        max_range = 500.0
        max_radius = 4.0
        max_amount = 3.0
        max_threshold = 100.0
        initial_radius = 1.0
        initial_amount = 0.5
        initial_threshold = 0.0
        self.master_layer_copy = self.master_layer.copy()
        dlg = QDialog(self)
        dlg.setWindowTitle("Unsharp Mask")
        dlg.setMinimumWidth(600)
        layout = QVBoxLayout(dlg)
        params = {
            "Radius": (max_radius, initial_radius, "{:.2f}"),
            "Amount": (max_amount, initial_amount, "{:.2%}"),
            "Threshold": (max_threshold, initial_threshold, "{:.2f}")
        }
        sliders = {}
        value_labels = {}
        for name, (max_val, init_val, fmt) in params.items():
            param_layout = QHBoxLayout()
            name_label = QLabel(f"{name}:")
            param_layout.addWidget(name_label)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, max_range)
            slider.setValue(init_val / max_val * max_range)
            param_layout.addWidget(slider)
            value_label = QLabel(fmt.format(init_val))
            param_layout.addWidget(value_label)
            layout.addLayout(param_layout)
            sliders[name] = slider
            value_labels[name] = value_label
        preview_check = QCheckBox("Preview")
        preview_check.setChecked(True)
        layout.addWidget(preview_check)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)
        last_preview_params = None
        preview_timer = QTimer()
        preview_timer.setSingleShot(True)
        preview_timer.setInterval(200)
        active_worker = None
        last_request_id = 0

        class UnsharpWorker(QThread):
            finished = Signal(np.ndarray, int)

            def __init__(self, image, radius, amount, threshold, request_id):
                super().__init__()
                self.image = image
                self.radius = radius
                self.amount = amount
                self.threshold = threshold
                self.request_id = request_id

            def run(self):
                result = unsharp_mask(self.image, max(0.01, self.radius), self.amount, self.threshold)
                self.finished.emit(result, self.request_id)

        def update_param_value(name, value, max_val, fmt):
            float_value = max_val * value / max_range
            value_labels[name].setText(fmt.format(float_value))
            if preview_check.isChecked():
                nonlocal last_preview_params
                last_preview_params = (
                    max_radius * sliders["Radius"].value() / max_range,
                    max_amount * sliders["Amount"].value() / max_range,
                    max_threshold * sliders["Threshold"].value() / max_range
                )
                preview_timer.start()
        sliders["Radius"].valueChanged.connect(
            lambda v: update_param_value("Radius", v, params["Radius"][0], params["Radius"][2]))
        sliders["Amount"].valueChanged.connect(
            lambda v: update_param_value("Amount", v, params["Amount"][0], params["Amount"][2]))
        sliders["Threshold"].valueChanged.connect(
            lambda v: update_param_value("Threshold", v, params["Threshold"][0], params["Threshold"][2]))

        def do_preview():
            nonlocal active_worker, last_request_id
            if last_preview_params is None:
                return
            if active_worker and active_worker.isRunning():
                active_worker.quit()
                active_worker.wait()
            last_request_id += 1
            current_request_id = last_request_id
            radius, amount, threshold = last_preview_params
            active_worker = UnsharpWorker(
                self.master_layer_copy.copy(),
                radius,
                amount,
                threshold,
                current_request_id
            )
            active_worker.finished.connect(lambda img, rid: set_preview(img, rid, current_request_id))
            active_worker.start()

        def set_preview(img, request_id, expected_id):
            if request_id != expected_id:
                return
            self.master_layer = img
            self.display_master_layer()
            dlg.activateWindow()
            sliders["Radius"].setFocus()

        def on_preview_toggled(checked):
            nonlocal last_preview_params
            if checked:
                last_preview_params = (
                    max_radius * sliders["Radius"].value() / max_range,
                    max_amount * sliders["Amount"].value() / max_range,
                    max_threshold * sliders["Threshold"].value() / max_range
                )
                do_preview()
            else:
                self.master_layer = self.master_layer_copy.copy()
                self.display_master_layer()
                dlg.activateWindow()
                sliders["Radius"].setFocus()

        preview_timer.timeout.connect(do_preview)
        preview_check.stateChanged.connect(on_preview_toggled)
        button_box.accepted.connect(dlg.accept)
        button_box.rejected.connect(dlg.reject)

        def run_initial_preview():
            nonlocal last_preview_params
            last_preview_params = (
                initial_radius,
                initial_amount,
                initial_threshold
            )
            do_preview()

        QTimer.singleShot(0, run_initial_preview)
        sliders["Radius"].setFocus()
        if dlg.exec_() == QDialog.Accepted:
            radius = max_radius * sliders["Radius"].value() / max_range
            amount = max_amount * sliders["Amount"].value() / max_range
            threshold = max_threshold * sliders["Threshold"].value() / max_range
            h, w = self.master_layer.shape[:2]
            self.undo_manager.extend_undo_area(0, 0, w, h)
            self.undo_manager.save_undo_state(self.master_layer_copy, 'Unsharp Mask')
            self.master_layer = unsharp_mask(self.master_layer_copy, max(0.01, radius), amount, threshold)
            self.master_layer_copy = self.master_layer.copy()
            self.display_master_layer()
            self.update_master_thumbnail()
            self.mark_as_modified()
        else:
            self.master_layer = self.master_layer_copy.copy()
            self.display_master_layer()

    def white_balance(self):
        if hasattr(self, 'wb_dialog') and self.wb_dialog:
            self.wb_dialog.activateWindow()
            self.wb_dialog.raise_()
            return
        max_range = 255
        initial_val = 128
        initial_rgb = (initial_val, initial_val, initial_val)
        cursor_style = self.image_viewer.cursor_style
        self.image_viewer.set_cursor_style('outline')
        if self.image_viewer.brush_cursor:
            self.image_viewer.brush_cursor.hide()
        self.master_layer_copy = self.master_layer.copy()
        self.brush_preview.hide()
        self.wb_dialog = dlg = QDialog(self)
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowStaysOnTopHint)
        dlg.setFocusPolicy(Qt.StrongFocus)
        dlg.setWindowTitle("White Balance")
        dlg.setMinimumWidth(600)
        layout = QVBoxLayout(dlg)
        row_layout = QHBoxLayout()
        color_preview = QFrame()
        color_preview.setFixedHeight(80)
        color_preview.setFixedWidth(80)
        color_preview.setStyleSheet("background-color: rgb(128,128,128);")
        row_layout.addWidget(color_preview)
        sliders_layout = QVBoxLayout()
        sliders = {}
        value_labels = {}
        rgb_layouts = {}
        for name, init_val in zip(("R", "G", "B"), initial_rgb):
            row = QHBoxLayout()
            label = QLabel(f"{name}:")
            row.addWidget(label)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, max_range)
            slider.setValue(init_val)
            row.addWidget(slider)
            val_label = QLabel(str(init_val))
            row.addWidget(val_label)
            sliders_layout.addLayout(row)
            sliders[name] = slider
            value_labels[name] = val_label
            rgb_layouts[name] = row
        row_layout.addLayout(sliders_layout)
        layout.addLayout(row_layout)
        pick_button = QPushButton("Pick Color")
        layout.addWidget(pick_button)

        def update_preview_color():
            rgb = tuple(sliders[n].value() for n in ("R", "G", "B"))
            color_preview.setStyleSheet(f"background-color: rgb{rgb};")

        def schedule_preview():
            nonlocal last_preview_rgb
            rgb = tuple(sliders[n].value() for n in ("R", "G", "B"))
            for n in ("R", "G", "B"):
                value_labels[n].setText(str(sliders[n].value()))
            update_preview_color()
            if preview_check.isChecked() and rgb != last_preview_rgb:
                last_preview_rgb = rgb
                preview_timer.start(100)

        def apply_preview():
            rgb = tuple(sliders[n].value() for n in ("R", "G", "B"))
            processed = white_balance_from_rgb(self.master_layer_copy, rgb)
            self.master_layer = processed
            self.display_master_layer()
            dlg.activateWindow()

        def on_preview_toggled(checked):
            nonlocal last_preview_rgb
            if checked:
                last_preview_rgb = tuple(sliders[n].value() for n in ("R", "G", "B"))
                preview_timer.start(100)
            else:
                self.master_layer = self.master_layer_copy.copy()
                self.display_master_layer()
                dlg.activateWindow()

        preview_check = QCheckBox("Preview")
        preview_check.setChecked(True)
        preview_check.stateChanged.connect(on_preview_toggled)
        layout.addWidget(preview_check)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Reset | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)
        last_preview_rgb = None
        preview_timer = QTimer()
        preview_timer.setSingleShot(True)
        preview_timer.timeout.connect(apply_preview)
        for slider in sliders.values():
            slider.valueChanged.connect(schedule_preview)

        def start_color_pick():
            dlg.hide()
            QApplication.setOverrideCursor(QCursor(Qt.CrossCursor))
            self.image_viewer.setCursor(Qt.CrossCursor)
            self.master_layer = self.master_layer_copy
            self.display_master_layer()
            self._original_mouse_press = self.image_viewer.mousePressEvent
            self.image_viewer.mousePressEvent = pick_color_from_click

        def pick_color_from_click(event):
            if event.button() == Qt.LeftButton:
                pos = event.pos()
                bgr = self.get_pixel_color_at(pos)
                rgb = (bgr[2], bgr[1], bgr[0])
                for name, val in zip(("R", "G", "B"), rgb):
                    sliders[name].setValue(val)
                QApplication.restoreOverrideCursor()
                self.image_viewer.unsetCursor()
                if hasattr(self, "_original_mouse_press"):
                    self.image_viewer.mousePressEvent = self._original_mouse_press
                dlg.show()
                dlg.activateWindow()
                dlg.raise_()

        pick_button.clicked.connect(start_color_pick)
        button_box.accepted.connect(dlg.accept)

        def cancel_changes():
            self.master_layer = self.master_layer_copy
            self.display_master_layer()
            dlg.reject()

        def reset_rgb():
            for k, s in sliders.items():
                s.setValue(initial_val)

        button_box.rejected.connect(cancel_changes)
        button_box.button(QDialogButtonBox.Reset).clicked.connect(reset_rgb)

        def finish_white_balance(result):
            if result == QDialog.Accepted:
                apply_preview()
                h, w = self.master_layer.shape[:2]
                self.undo_manager.extend_undo_area(0, 0, w, h)
                self.undo_manager.save_undo_state(self.master_layer_copy, 'White Balance')
                self.master_layer_copy = self.master_layer.copy()
                self.display_master_layer()
                self.update_master_thumbnail()
                self.mark_as_modified()
            self.image_viewer.set_cursor_style(cursor_style)
            self.wb_dialog = None

        dlg.finished.connect(finish_white_balance)
        dlg.show()
        dlg.activateWindow()
        dlg.raise_()

    def get_pixel_color_at(self, pos, radius=None):
        scene_pos = self.image_viewer.mapToScene(pos)
        item_pos = self.image_viewer.pixmap_item.mapFromScene(scene_pos)
        x = int(item_pos.x())
        y = int(item_pos.y())
        if (0 <= x < self.master_layer.shape[1]) and (0 <= y < self.master_layer.shape[0]):
            if radius is None:
                radius = int(self.brush.size)
            if radius > 0:
                y_indices, x_indices = np.ogrid[-radius:radius + 1, -radius:radius + 1]
                mask = x_indices**2 + y_indices**2 <= radius**2
                x0 = max(0, x - radius)
                x1 = min(self.master_layer.shape[1], x + radius + 1)
                y0 = max(0, y - radius)
                y1 = min(self.master_layer.shape[0], y + radius + 1)
                mask = mask[radius - (y - y0): radius + (y1 - y), radius - (x - x0): radius + (x1 - x)]
                region = self.master_layer[y0:y1, x0:x1]
                if region.size == 0:
                    pixel = self.master_layer[y, x]
                else:
                    if region.ndim == 3:
                        pixel = [region[:, :, c][mask].mean() for c in range(region.shape[2])]
                    else:
                        pixel = region[mask].mean()
            else:
                pixel = self.master_layer[y, x]
            if np.isscalar(pixel):
                pixel = [pixel, pixel, pixel]
            pixel = [np.float32(x) for x in pixel]
            if self.master_layer.dtype == np.uint16:
                pixel = [x / 256.0 for x in pixel]
            return tuple(int(v) for v in pixel)
        else:
            return (0, 0, 0)
