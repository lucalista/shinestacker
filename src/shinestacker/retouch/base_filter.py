# pylint: disable=E0611, W0718, R0915, R0903, R0913, R0917, R0902, R0914
import traceback
from abc import abstractmethod
import numpy as np
from PySide6.QtCore import Qt, QThread, QTimer, QObject, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QSlider, QDialog, QVBoxLayout, QCheckBox, QDialogButtonBox)
from .layer_collection import LayerCollectionHandler


class BaseFilter(QObject, LayerCollectionHandler):
    update_master_thumbnail_requested = Signal()
    mark_as_modified_requested = Signal()
    filter_gui_set_enabled_requested = Signal(bool)

    def __init__(self, name, parent, image_viewer, layer_collection, undo_manager,
                 allow_partial_preview=True,
                 partial_preview_threshold=0.75, preview_at_startup=False):
        QObject.__init__(self, parent)
        LayerCollectionHandler.__init__(self, layer_collection)
        self.image_viewer = image_viewer
        self.undo_manager = undo_manager
        self.name = name
        self.allow_partial_preview = allow_partial_preview
        self.partial_preview_threshold = partial_preview_threshold
        self.preview_at_startup = preview_at_startup
        self.preview_check = None
        self.button_box = None
        self.preview_timer = None
        self.max_range = 500
        self.value_labels = None

    def update_value(self, name, value, max_val, fmt):
        self.value_labels[name].setText(fmt.format(max_val * value / self.max_range))
        if self.preview_check.isChecked():
            self.preview_timer.start()

    @abstractmethod
    def setup_ui(self, dlg, layout, do_preview, restore_original, **kwargs):
        pass

    @abstractmethod
    def get_params(self):
        pass

    @abstractmethod
    def apply(self, image, *params):
        pass

    def slider_from_value(self, value, min_val, max_val):
        return (value - min_val) / (max_val - min_val) * self.max_range

    def value_from_slider(self, slider_value, min_val, max_val):
        return min_val + (max_val - min_val) * float(slider_value) / self.max_range

    def create_sliders(self, params, dlg, layout, set_slider):
        value_labels = {}
        font_metrics = QFontMetrics(dlg.font())
        max_name_width = 0
        max_value_width = 0
        for name, (min_val, max_val, init_val, fmt) in params.items():
            name_width = font_metrics.horizontalAdvance(f"{name}:")
            max_name_width = max(max_name_width, name_width)
            sample_values = [min_val, max_val, init_val]
            for val in sample_values:
                value_width = font_metrics.horizontalAdvance(fmt.format(val))
                max_value_width = max(max_value_width, value_width)
        max_name_width += 10
        max_value_width += 10
        for name, (min_val, max_val, init_val, fmt) in params.items():
            param_layout = QHBoxLayout()
            name_label = QLabel(f"{name}:")
            name_label.setFixedWidth(max_name_width)
            name_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            param_layout.addWidget(name_label)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, self.max_range)
            slider.setValue(self.slider_from_value(init_val, min_val, max_val))
            param_layout.addWidget(slider, 1)
            value_label = QLabel(fmt.format(init_val))
            value_label.setFixedWidth(max_value_width)
            value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            param_layout.addWidget(value_label)
            layout.addLayout(param_layout)
            set_slider(name, slider)
            value_labels[name] = value_label
        self.create_base_widgets(
            layout, QDialogButtonBox.Ok | QDialogButtonBox.Cancel, 200, dlg)
        return value_labels

    def connect_signals(self, update_master_thumbnail, mark_as_modified, filter_gui_set_enabled):
        self.update_master_thumbnail_requested.connect(update_master_thumbnail)
        self.mark_as_modified_requested.connect(mark_as_modified)
        self.filter_gui_set_enabled_requested.connect(filter_gui_set_enabled)

    def run_with_preview(self, **kwargs):
        if self.has_no_master_layer():
            return
        self.copy_master_layer()
        dlg = QDialog(self.parent())
        layout = QVBoxLayout(dlg)
        active_worker = None
        last_request_id = 0
        initial_timer = QTimer(dlg)
        initial_timer.setSingleShot(True)
        dialog_closed = False

        def cleanup():
            nonlocal active_worker, dialog_closed  # noqa
            dialog_closed = True
            self.restore_master_layer()
            self.image_viewer.update_master_display()
            if active_worker and active_worker.isRunning():
                active_worker.wait()
            initial_timer.stop()

        dlg.finished.connect(cleanup)

        def set_preview(img, request_id, expected_id, region=None):
            if dialog_closed or request_id != expected_id:
                return
            if region:
                current_region = self.image_viewer.get_visible_image_portion()[1]
                if current_region == region:
                    self.set_master_layer(img)
                    self.image_viewer.update_master_display()
            else:
                self.set_master_layer(img)
                self.image_viewer.update_master_display()
            try:
                dlg.activateWindow()
            except Exception:
                pass

        def do_preview():
            nonlocal active_worker, last_request_id
            if not dlg.isVisible():
                return
            if active_worker and active_worker.isRunning():
                try:
                    active_worker.quit()
                    active_worker.wait()
                except Exception:
                    pass
            last_request_id += 1
            current_id = last_request_id
            visible_region = None
            if kwargs.get('partial_preview', self.allow_partial_preview):
                visible_data = self.image_viewer.get_visible_image_portion()
                if visible_data:
                    visible_img, visible_region = visible_data
                    master_img = self.master_layer_copy()
                    if visible_img.size < master_img.size * self.partial_preview_threshold:
                        params = tuple(self.get_params() or ())
                        worker = self.PreviewWorker(
                            self.apply,
                            args=(master_img, *params),
                            request_id=current_id,
                            region=visible_region
                        )
                    else:
                        params = tuple(self.get_params() or ())
                        worker = self.PreviewWorker(
                            self.apply,
                            args=(master_img, *params),
                            request_id=current_id
                        )
                else:
                    params = tuple(self.get_params() or ())
                    worker = self.PreviewWorker(
                        self.apply,
                        args=(self.master_layer_copy(), *params),
                        request_id=current_id
                    )
            else:
                params = tuple(self.get_params() or ())
                worker = self.PreviewWorker(
                    self.apply,
                    args=(self.master_layer_copy(), *params),
                    request_id=current_id
                )
            active_worker = worker
            active_worker.finished.connect(
                lambda img, rid, region: set_preview(img, rid, current_id, region))
            active_worker.start()

        def restore_original():
            self.restore_master_layer()
            self.image_viewer.update_master_display()
            try:
                dlg.activateWindow()
            except Exception:
                pass

        self.setup_ui(dlg, layout, do_preview, restore_original, **kwargs)
        if self.preview_check.isChecked():
            initial_timer.timeout.connect(do_preview)
            initial_timer.start(0)
        accepted = dlg.exec_() == QDialog.Accepted
        cleanup()
        if accepted:
            params = tuple(self.get_params() or ())
            try:
                h, w = self.master_layer().shape[:2]
            except Exception:
                h, w = self.master_layer_copy().shape[:2]
            try:
                self.undo_manager.set_paint_area(0, 0, w, h)
                self.undo_manager.save_undo_state(
                    self.master_layer_copy(),
                    self.name
                )
            except Exception:
                pass
            final_img = self.apply(self.master_layer_copy(), *params)
            self.set_master_layer(final_img)
            self.copy_master_layer()
            self.image_viewer.update_master_display()
            self.update_master_thumbnail_requested.emit()
            self.mark_as_modified_requested.emit()
        else:
            restore_original()

    def connect_preview_toggle(self, preview_check, do_preview, restore_original):
        def on_toggled(checked):
            if checked:
                do_preview()
            else:
                restore_original()
        preview_check.toggled.connect(on_toggled)

    def create_base_widgets(self, layout, buttons, preview_latency, parent):
        self.preview_check = QCheckBox("Preview")
        self.preview_check.setChecked(self.preview_at_startup)
        layout.addWidget(self.preview_check)
        self.button_box = QDialogButtonBox(buttons)
        layout.addWidget(self.button_box)
        self.preview_timer = QTimer(parent)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(preview_latency)

    def set_timer(self, do_preview, restore_original, dlg):
        self.preview_timer.timeout.connect(do_preview)
        self.connect_preview_toggle(self.preview_check, do_preview, restore_original)
        self.button_box.accepted.connect(dlg.accept)
        self.button_box.rejected.connect(dlg.reject)
        QTimer.singleShot(0, do_preview)

    class PreviewWorker(QThread):
        finished = Signal(np.ndarray, int, tuple)

        def __init__(self, func, args=(), kwargs=None, request_id=0, region=None):
            super().__init__()
            self.func = func
            self.args = args
            self.kwargs = kwargs or {}
            self.request_id = request_id
            self.region = region

        def run(self):
            try:
                if self.region:
                    x, y, w, h = self.region
                    image = self.args[0]
                    region_img = image[y:y + h, x:x + w]
                    region_args = (region_img,) + self.args[1:]
                    region_result = self.func(*region_args, **self.kwargs)
                    result = image.copy()
                    result[y:y + h, x:x + w] = region_result
                else:
                    result = self.func(*self.args, **self.kwargs)
                self.finished.emit(result, self.request_id, self.region)
            except Exception as e:
                traceback.print_exc()
                raise RuntimeError("Filter preview failed") from e


class OneSliderBaseFilter(BaseFilter):
    def __init__(self, name, parent, image_viewer, layer_collection, undo_manager,
                 min_value, max_value, initial_value, title,
                 allow_partial_preview=True, partial_preview_threshold=0.5,
                 preview_at_startup=True):
        super().__init__(name, parent, image_viewer, layer_collection, undo_manager,
                         allow_partial_preview,
                         partial_preview_threshold, preview_at_startup)
        self.max_value = max_value
        self.min_value = min_value
        self.initial_value = initial_value
        self.slider = None
        self.value_label = None
        self.title = title
        self.format = "{:.2f}"

    def add_widgets(self, layout, dlg):
        pass

    def slider_from_value_1(self, value):
        return int((value - self.min_value) / (self.max_value - self.min_value) * self.max_range)

    def value_from_slider_1(self, slider_value):
        return self.min_value + \
            (self.max_value - self.min_value) * float(slider_value) / self.max_range

    def setup_ui(self, dlg, layout, do_preview, restore_original, **kwargs):
        dlg.setWindowTitle(self.title)
        dlg.setMinimumWidth(600)
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Amount:"))
        slider_local = QSlider(Qt.Horizontal)
        slider_local.setRange(0, self.max_range)
        slider_local.setValue(self.slider_from_value_1(self.initial_value))
        slider_layout.addWidget(slider_local)
        self.value_label = QLabel(self.format.format(self.initial_value))
        slider_layout.addWidget(self.value_label)
        layout.addLayout(slider_layout)
        self.add_widgets(layout, dlg)
        self.create_base_widgets(
            layout, QDialogButtonBox.Ok | QDialogButtonBox.Cancel, 200, dlg)
        self.preview_timer.timeout.connect(do_preview)
        slider_local.valueChanged.connect(self.config_changed)
        self.connect_preview_toggle(
            self.preview_check, self.do_preview_delayed, restore_original)
        self.button_box.accepted.connect(dlg.accept)
        self.button_box.rejected.connect(dlg.reject)
        self.slider = slider_local

    def param_changed(self, _val):
        if self.preview_check.isChecked():
            self.do_preview_delayed()

    def config_changed(self, val):
        float_val = self.value_from_slider_1(val)
        self.value_label.setText(self.format.format(float_val))
        self.param_changed(val)

    def do_preview_delayed(self):
        self.preview_timer.start()

    def get_params(self):
        return (self.value_from_slider_1(self.slider.value()),)

    def apply(self, image, *params):
        assert False
