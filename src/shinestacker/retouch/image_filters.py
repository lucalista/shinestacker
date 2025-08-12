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

    class PreviewWorker(QThread):
        finished = Signal(np.ndarray, int)

        def __init__(self, func, args=(), kwargs=None, request_id=0):
            super().__init__()
            self.func = func
            self.args = args
            self.kwargs = kwargs or {}
            self.request_id = request_id

        def run(self):
            try:
                result = self.func(*self.args, **self.kwargs)
            except Exception:
                raise
            self.finished.emit(result, self.request_id)

    def connect_preview_toggle(self, preview_check, do_preview, restore_original):
        def on_toggled(checked):
            if checked:
                do_preview()
            else:
                restore_original()
        preview_check.toggled.connect(on_toggled)

    def run_filter_with_preview(self, filter_func, get_params, setup_ui, undo_label):
        if self.layer_collection.master_layer is None:
            return
        self.layer_collection.copy_master_layer()
        dlg = QDialog(self)
        layout = QVBoxLayout(dlg)
        active_worker = None
        last_request_id = 0

        def set_preview(img, request_id, expected_id):
            if request_id != expected_id:
                return
            self.layer_collection.master_layer = img
            self.display_master_layer()
            try:
                dlg.activateWindow()
            except Exception:
                pass

        def do_preview():
            nonlocal active_worker, last_request_id
            if active_worker and active_worker.isRunning():
                try:
                    active_worker.quit()
                    active_worker.wait()
                except Exception:
                    pass
            last_request_id += 1
            current_id = last_request_id
            params = tuple(get_params() or ())
            worker = self.PreviewWorker(filter_func, args=(self.layer_collection.master_layer_copy, *params), request_id=current_id)
            active_worker = worker
            active_worker.finished.connect(lambda img, rid: set_preview(img, rid, current_id))
            active_worker.start()

        def restore_original():
            self.layer_collection.master_layer = self.layer_collection.master_layer_copy.copy()
            self.display_master_layer()
            try:
                dlg.activateWindow()
            except Exception:
                pass

        setup_ui(dlg, layout, do_preview, restore_original)
        QTimer.singleShot(0, do_preview)
        accepted = dlg.exec_() == QDialog.Accepted
        if accepted:
            params = tuple(get_params() or ())
            try:
                h, w = self.layer_collection.master_layer.shape[:2]
            except Exception:
                h, w = self.layer_collection.master_layer_copy.shape[:2]
            if hasattr(self, "undo_manager"):
                try:
                    self.undo_manager.extend_undo_area(0, 0, w, h)
                    self.undo_manager.save_undo_state(self.layer_collection.master_layer_copy, undo_label)
                except Exception:
                    pass
            final_img = filter_func(self.layer_collection.master_layer_copy, *params)
            self.layer_collection.master_layer = final_img
            self.layer_collection.copy_master_layer()
            self.display_master_layer()
            self.update_master_thumbnail()
            self.mark_as_modified()
        else:
            restore_original()

    def denoise(self):
        max_range = 500.0
        max_value = 10.00
        initial_value = 2.5

        def get_params():
            return (max_value * slider.value() / max_range,)

        def setup_ui(dlg, layout, do_preview, restore_original):
            nonlocal slider
            dlg.setWindowTitle("Denoise")
            dlg.setMinimumWidth(600)
            slider_layout = QHBoxLayout()
            slider_local = QSlider(Qt.Horizontal)
            slider_local.setRange(0, max_range)
            slider_local.setValue(int(initial_value / max_value * max_range))
            slider_layout.addWidget(slider_local)
            value_label = QLabel(f"{max_value:.2f}")
            slider_layout.addWidget(value_label)
            layout.addLayout(slider_layout)
            preview_check = QCheckBox("Preview")
            preview_check.setChecked(True)
            layout.addWidget(preview_check)
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            layout.addWidget(button_box)
            preview_timer = QTimer()
            preview_timer.setSingleShot(True)
            preview_timer.setInterval(200)

            def do_preview_delayed():
                preview_timer.start()

            def slider_changed(val):
                float_val = max_value * float(val) / max_range
                value_label.setText(f"{float_val:.2f}")
                if preview_check.isChecked():
                    do_preview_delayed()

            preview_timer.timeout.connect(do_preview)
            slider_local.valueChanged.connect(slider_changed)
            self.connect_preview_toggle(preview_check, do_preview_delayed, restore_original)
            button_box.accepted.connect(dlg.accept)
            button_box.rejected.connect(dlg.reject)
            slider = slider_local

        slider = None
        self.run_filter_with_preview(denoise, get_params, setup_ui, 'Denoise')

    def unsharp_mask(self):
        max_range = 500.0
        max_radius = 4.0
        max_amount = 3.0
        max_threshold = 64.0
        initial_radius = 1.0
        initial_amount = 0.5
        initial_threshold = 0.0

        def get_params():
            return (
                max(0.01, max_radius * radius_slider.value() / max_range),
                max_amount * amount_slider.value() / max_range,
                max_threshold * threshold_slider.value() / max_range
            )

        def setup_ui(dlg, layout, do_preview, restore_original):
            nonlocal radius_slider, amount_slider, threshold_slider
            dlg.setWindowTitle("Unsharp Mask")
            dlg.setMinimumWidth(600)
            params = {
                "Radius": (max_radius, initial_radius, "{:.2f}"),
                "Amount": (max_amount, initial_amount, "{:.1%}"),
                "Threshold": (max_threshold, initial_threshold, "{:.2f}")
            }
            value_labels = {}
            for name, (max_val, init_val, fmt) in params.items():
                param_layout = QHBoxLayout()
                name_label = QLabel(f"{name}:")
                param_layout.addWidget(name_label)
                slider = QSlider(Qt.Horizontal)
                slider.setRange(0, max_range)
                slider.setValue(int(init_val / max_val * max_range))
                param_layout.addWidget(slider)
                value_label = QLabel(fmt.format(init_val))
                param_layout.addWidget(value_label)
                layout.addLayout(param_layout)
                if name == "Radius":
                    radius_slider = slider
                elif name == "Amount":
                    amount_slider = slider
                elif name == "Threshold":
                    threshold_slider = slider
                value_labels[name] = value_label
            preview_check = QCheckBox("Preview")
            preview_check.setChecked(True)
            layout.addWidget(preview_check)
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            layout.addWidget(button_box)
            preview_timer = QTimer()
            preview_timer.setSingleShot(True)
            preview_timer.setInterval(200)

            def update_value(name, value, max_val, fmt):
                float_value = max_val * value / max_range
                value_labels[name].setText(fmt.format(float_value))
                if preview_check.isChecked():
                    preview_timer.start()

            radius_slider.valueChanged.connect(
                lambda v: update_value("Radius", v, max_radius, params["Radius"][2]))
            amount_slider.valueChanged.connect(
                lambda v: update_value("Amount", v, max_amount, params["Amount"][2]))
            threshold_slider.valueChanged.connect(
                lambda v: update_value("Threshold", v, max_threshold, params["Threshold"][2]))
            preview_timer.timeout.connect(do_preview)
            self.connect_preview_toggle(preview_check, do_preview, restore_original)
            button_box.accepted.connect(dlg.accept)
            button_box.rejected.connect(dlg.reject)
            QTimer.singleShot(0, do_preview)

        radius_slider = None
        amount_slider = None
        threshold_slider = None
        self.run_filter_with_preview(unsharp_mask, get_params, setup_ui, 'Unsharp Mask')

    def white_balance(self, init_val=False):
        max_range = 255
        if init_val is False:
            init_val = (128, 128, 128)
        initial_val = {k: v for k, v in zip(["R", "G", "B"], init_val)}
        cursor_style = self.image_viewer.cursor_style
        self.image_viewer.set_cursor_style('outline')
        if self.image_viewer.brush_cursor:
            self.image_viewer.brush_cursor.hide()
        self.brush_preview.hide()

        def get_params():
            return tuple(sliders[n].value() for n in ("R", "G", "B"))

        def setup_ui(dlg, layout, do_preview, restore_original):
            nonlocal sliders, value_labels, color_preview, preview_timer
            self.wb_dialog = dlg
            dlg.setWindowModality(Qt.ApplicationModal)
            dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowStaysOnTopHint)
            dlg.setFocusPolicy(Qt.StrongFocus)
            dlg.setWindowTitle("White Balance")
            dlg.setMinimumWidth(600)
            row_layout = QHBoxLayout()
            color_preview = QFrame()
            color_preview.setFixedHeight(80)
            color_preview.setFixedWidth(80)
            color_preview.setStyleSheet("background-color: rgb(128,128,128);")
            row_layout.addWidget(color_preview)
            sliders_layout = QVBoxLayout()
            sliders = {}
            value_labels = {}
            for name in ("R", "G", "B"):
                row = QHBoxLayout()
                label = QLabel(f"{name}:")
                row.addWidget(label)
                slider = QSlider(Qt.Horizontal)
                slider.setRange(0, max_range)
                init_val = initial_val[name]
                slider.setValue(init_val)
                row.addWidget(slider)
                val_label = QLabel(str(init_val))
                row.addWidget(val_label)
                sliders_layout.addLayout(row)
                sliders[name] = slider
                value_labels[name] = val_label
            row_layout.addLayout(sliders_layout)
            layout.addLayout(row_layout)
            pick_button = QPushButton("Pick Color")
            layout.addWidget(pick_button)
            preview_check = QCheckBox("Preview")
            preview_check.setChecked(True)
            layout.addWidget(preview_check)
            button_box = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Reset | QDialogButtonBox.Cancel
            )
            layout.addWidget(button_box)
            preview_timer = QTimer()
            preview_timer.setSingleShot(True)
            preview_timer.setInterval(200)

            def update_preview_color():
                rgb = tuple(sliders[n].value() for n in ("R", "G", "B"))
                color_preview.setStyleSheet(f"background-color: rgb{rgb};")

            def schedule_preview():
                if preview_check.isChecked():
                    preview_timer.start()

            def on_slider_change():
                for name in ("R", "G", "B"):
                    value_labels[name].setText(str(sliders[name].value()))
                update_preview_color()
                schedule_preview()

            for slider in sliders.values():
                slider.valueChanged.connect(on_slider_change)

            preview_timer.timeout.connect(do_preview)
            self.connect_preview_toggle(preview_check, do_preview, restore_original)

            def start_color_pick():
                restore_original()
                dlg.hide()
                dlg.reject()
                QApplication.setOverrideCursor(QCursor(Qt.CrossCursor))
                self.image_viewer.setCursor(Qt.CrossCursor)
                self._original_mouse_press = self.image_viewer.mousePressEvent
                self.image_viewer.mousePressEvent = pick_color_from_click

            def pick_color_from_click(event):
                if event.button() == Qt.LeftButton:
                    bgr = self.get_pixel_color_at(event.pos(), radius=int(self.brush.size))
                    rgb = (bgr[2], bgr[1], bgr[0])
                    QApplication.restoreOverrideCursor()
                    self.image_viewer.unsetCursor()
                    self.image_viewer.mousePressEvent = self._original_mouse_press
                    delattr(self, "_original_mouse_press")
                    self.image_viewer.set_cursor_style(cursor_style)
                    if self.image_viewer.brush_cursor:
                        self.image_viewer.brush_cursor.show()
                    self.brush_preview.show()
                    self.white_balance(rgb)

            def reset_rgb():
                for name, slider in sliders.items():
                    slider.setValue(initial_val[name])

            pick_button.clicked.connect(start_color_pick)
            button_box.accepted.connect(dlg.accept)
            button_box.rejected.connect(dlg.reject)
            button_box.button(QDialogButtonBox.Reset).clicked.connect(reset_rgb)

            def on_finished():
                self.image_viewer.set_cursor_style(cursor_style)
                self.image_viewer.brush_cursor.show()
                self.brush_preview.show()
                self.wb_dialog = None

            dlg.finished.connect(on_finished)
            QTimer.singleShot(0, do_preview)

        sliders = {}
        value_labels = {}
        color_preview = None
        preview_timer = None
        self.run_filter_with_preview(lambda img, r, g, b: white_balance_from_rgb(img, (r, g, b)),
                                     get_params, setup_ui, 'White Balance')

    def get_pixel_color_at(self, pos, radius=None):
        scene_pos = self.image_viewer.mapToScene(pos)
        item_pos = self.image_viewer.pixmap_item.mapFromScene(scene_pos)
        x = int(item_pos.x())
        y = int(item_pos.y())
        if (0 <= x < self.layer_collection.master_layer.shape[1]) and (0 <= y < self.layer_collection.master_layer.shape[0]):
            if radius is None:
                radius = int(self.brush.size)
            if radius > 0:
                y_indices, x_indices = np.ogrid[-radius:radius + 1, -radius:radius + 1]
                mask = x_indices**2 + y_indices**2 <= radius**2
                x0 = max(0, x - radius)
                x1 = min(self.layer_collection.master_layer.shape[1], x + radius + 1)
                y0 = max(0, y - radius)
                y1 = min(self.layer_collection.master_layer.shape[0], y + radius + 1)
                mask = mask[radius - (y - y0): radius + (y1 - y), radius - (x - x0): radius + (x1 - x)]
                region = self.layer_collection.master_layer[y0:y1, x0:x1]
                if region.size == 0:
                    pixel = self.layer_collection.master_layer[y, x]
                else:
                    if region.ndim == 3:
                        pixel = [region[:, :, c][mask].mean() for c in range(region.shape[2])]
                    else:
                        pixel = region[mask].mean()
            else:
                pixel = self.layer_collection.master_layer[y, x]
            if np.isscalar(pixel):
                pixel = [pixel, pixel, pixel]
            pixel = [np.float32(x) for x in pixel]
            if self.layer_collection.master_layer.dtype == np.uint16:
                pixel = [x / 256.0 for x in pixel]
            return tuple(int(v) for v in pixel)
        else:
            return (0, 0, 0)
