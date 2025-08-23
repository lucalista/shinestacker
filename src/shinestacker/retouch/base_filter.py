# pylint: disable=C0114, C0115, C0116, E0611, W0718, R0915, R0903, R0913, R0917
import traceback
from abc import ABC, abstractmethod
import numpy as np
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QSlider, QDialog, QVBoxLayout, QCheckBox, QDialogButtonBox)
from PySide6.QtCore import Qt, Signal, QThread, QTimer


class BaseFilter(ABC):
    def __init__(self, name, editor):
        self.editor = editor
        self.name = name

    @abstractmethod
    def setup_ui(self, dlg, layout, do_preview, restore_original, **kwargs):
        pass

    @abstractmethod
    def get_params(self):
        pass

    @abstractmethod
    def apply(self, image, *params):
        pass

    def run_with_preview(self, **kwargs):
        if self.editor.has_no_master_layer():
            return

        self.editor.copy_master_layer()
        dlg = QDialog(self.editor)
        layout = QVBoxLayout(dlg)
        active_worker = None
        last_request_id = 0

        def set_preview(img, request_id, expected_id):
            if request_id != expected_id:
                return
            self.editor.set_master_layer(img)
            self.editor.display_manager.display_master_layer()
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
            params = tuple(self.get_params() or ())
            worker = self.PreviewWorker(
                self.apply,
                args=(self.editor.master_layer_copy(), *params),
                request_id=current_id
            )
            active_worker = worker
            active_worker.finished.connect(lambda img, rid: set_preview(img, rid, current_id))
            active_worker.start()

        def restore_original():
            self.editor.restore_master_layer()
            self.editor.display_manager.display_master_layer()
            try:
                dlg.activateWindow()
            except Exception:
                pass

        self.setup_ui(dlg, layout, do_preview, restore_original, **kwargs)
        QTimer.singleShot(0, do_preview)
        accepted = dlg.exec_() == QDialog.Accepted
        if accepted:
            params = tuple(self.get_params() or ())
            try:
                h, w = self.editor.master_layer().shape[:2]
            except Exception:
                h, w = self.editor.master_layer_copy().shape[:2]
            if hasattr(self.editor, "undo_manager"):
                try:
                    self.editor.undo_manager.extend_undo_area(0, 0, w, h)
                    self.editor.undo_manager.save_undo_state(
                        self.editor.master_layer_copy(),
                        self.name
                    )
                except Exception:
                    pass
            final_img = self.apply(self.editor.master_layer_copy(), *params)
            self.editor.set_master_layer(final_img)
            self.editor.copy_master_layer()
            self.editor.display_manager.display_master_layer()
            self.editor.display_manager.update_master_thumbnail()
            self.editor.mark_as_modified()
        else:
            restore_original()

    def create_base_widgets(self, layout, buttons, preview_latency):
        preview_check = QCheckBox("Preview")
        preview_check.setChecked(True)
        layout.addWidget(preview_check)
        button_box = QDialogButtonBox(buttons)
        layout.addWidget(button_box)
        preview_timer = QTimer()
        preview_timer.setSingleShot(True)
        preview_timer.setInterval(preview_latency)
        return preview_check, preview_timer, button_box

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
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                raise RuntimeError("Filter preview failed") from e
            self.finished.emit(result, self.request_id)


class OneSliderBaseFilter(BaseFilter):
    def __init__(self, name, editor, max_value, initial_value, title):
        super().__init__(name, editor)
        self.max_range = 500.0
        self.max_value = max_value
        self.initial_value = initial_value
        self.slider = None
        self.title = title

    def setup_ui(self, dlg, layout, do_preview, restore_original, **kwargs):
        dlg.setWindowTitle(self.title)
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

    def apply(self, image, *params):
        assert False
