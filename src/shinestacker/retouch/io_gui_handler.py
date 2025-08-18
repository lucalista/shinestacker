# pylint: disable=C0114, C0115, C0116, E0611, R0902, W0718
import os
import traceback
import numpy as np
from PySide6.QtWidgets import QFileDialog, QMessageBox, QVBoxLayout, QLabel, QDialog, QApplication
from PySide6.QtGui import QGuiApplication, QCursor
from PySide6.QtCore import Qt, QObject, QTimer, Signal
from .file_loader import FileLoader
from .exif_data import ExifData
from .io_manager import IOManager
from .layer_collection import LayerCollectionHandler


class IOGuiHandler(QObject, LayerCollectionHandler):
    status_message_requested = Signal(str)
    update_title_requested = Signal()

    def __init__(self, layer_collection, undo_manager, parent):
        QObject.__init__(self, parent)
        LayerCollectionHandler.__init__(self)
        self.io_manager = IOManager(layer_collection)
        self.undo_manager = undo_manager
        self.set_layer_collection(layer_collection)
        self.loader_thread = None
        self.display_manager = None
        self.image_viewer = None
        self.blank_layer = None
        self.loading_dialog = None
        self.loading_timer = None
        self.exif_dialog = None
        self.current_file_path = ''

    def setup_ui(self, display_manager, image_viewer):
        self.display_manager = display_manager
        self.image_viewer = image_viewer

    def on_file_loaded(self, stack, labels, master_layer):
        QApplication.restoreOverrideCursor()
        self.loading_timer.stop()
        self.loading_dialog.hide()
        self.set_layer_stack(stack)
        if labels is None:
            self.set_layer_labels([f'Layer {i:03d}' for i in range(len(stack))])
        else:
            self.set_layer_labels(labels)
        self.set_master_layer(master_layer)
        self.parent().modified = False
        self.undo_manager.reset()
        self.blank_layer = np.zeros(master_layer.shape[:2])
        self.display_manager.update_thumbnails()
        self.image_viewer.setup_brush_cursor()
        self.parent().change_layer(0)
        self.image_viewer.reset_zoom()
        self.status_message_requested.emit(f"Loaded: {self.current_file_path}")
        self.parent().thumbnail_list.setFocus()
        self.update_title_requested.emit()

    def on_file_error(self, error_msg):
        QApplication.restoreOverrideCursor()
        self.loading_timer.stop()
        self.loading_dialog.accept()
        self.loading_dialog.deleteLater()
        QMessageBox.critical(self.parent(), "Error", error_msg)
        self.status_message_requested.emit(f"Error loading: {self.current_file_path}")

    def open_file(self, file_paths=None):
        if file_paths is None:
            file_paths, _ = QFileDialog.getOpenFileNames(
                self.parent(), "Open Image", "",
                "Images (*.tif *.tiff *.jpg *.jpeg);;All Files (*)")
        if not file_paths:
            return
        if self.loader_thread and self.loader_thread.isRunning():
            if not self.loader_thread.wait(10000):
                raise RuntimeError("Loading timeout error.")
        if isinstance(file_paths, list) and len(file_paths) > 1:
            self.import_frames_from_files(file_paths)
            return
        path = file_paths[0] if isinstance(file_paths, list) else file_paths
        self.current_file_path = os.path.abspath(path)
        QGuiApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
        self.loading_dialog = QDialog(self.parent())
        self.loading_dialog.setWindowTitle("Loading")
        self.loading_dialog.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.loading_dialog.setModal(True)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("File loading..."))
        self.loading_dialog.setLayout(layout)
        self.loading_timer = QTimer()
        self.loading_timer.setSingleShot(True)
        self.loading_timer.timeout.connect(self.loading_dialog.show)
        self.loading_timer.start(100)
        self.loader_thread = FileLoader(path)
        self.loader_thread.finished.connect(self.on_file_loaded)
        self.loader_thread.error.connect(self.on_file_error)
        self.loader_thread.start()

    def import_frames(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self.parent(), "Select frames", "",
            "Images Images (*.tif *.tiff *.jpg *.jpeg);;All Files (*)")
        if file_paths:
            self.import_frames_from_files(file_paths)
        self.status_message_requested.emit("Imported selected frames")

    def import_frames_from_files(self, file_paths):
        try:
            stack, labels, master = self.io_manager.import_frames(file_paths)
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Import error")
            msg.setText(str(e))
            msg.exec()
            return
        if self.layer_stack() is None and len(stack) > 0:
            self.set_layer_stack(np.array(stack))
            self.set_layer_labels(labels)
            self.set_master_layer(master)
            self.blank_layer = np.zeros(master.shape[:2])
        else:
            for img, label in zip(stack, labels):
                self.add_layer_label(label)
                self.add_layer(img)
        self.parent().mark_as_modified()
        self.parent().change_layer(0)
        self.image_viewer.reset_zoom()
        self.parent().thumbnail_list.setFocus()
        self.display_manager.update_thumbnails()

    def save_file(self):
        if self.parent().save_master_only.isChecked():
            self.save_master()
        else:
            self.save_multilayer()

    def save_file_as(self):
        if self.parent().save_master_only.isChecked():
            self.save_master_as()
        else:
            self.save_multilayer_as()

    def save_multilayer(self):
        if self.layer_stack() is None:
            return
        if self.current_file_path != '':
            extension = self.current_file_path.split('.')[-1]
            if extension in ['tif', 'tiff']:
                self.save_multilayer_to_path(self.current_file_path)
                return

    def save_multilayer_as(self):
        if self.layer_stack() is None:
            return
        path, _ = QFileDialog.getSaveFileName(self.parent(), "Save Image", "",
                                              "TIFF Files (*.tif *.tiff);;All Files (*)")
        if path:
            if not path.lower().endswith(('.tif', '.tiff')):
                path += '.tif'
            self.save_multilayer_to_path(path)

    def save_multilayer_to_path(self, path):
        try:
            self.io_manager.save_multilayer(path)
            self.current_file_path = os.path.abspath(path)
            self.parent().modified = False
            self.update_title_requested.emit()
            self.status_message_requested.emit(f"Saved multilayer to: {path}")
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            QMessageBox.critical(self.parent(), "Save Error", f"Could not save file: {str(e)}")

    def save_master(self):
        if self.master_layer() is None:
            return
        if self.current_file_path != '':
            self.save_master_to_path(self.current_file_path)
            return
        self.save_master_as()

    def save_master_as(self):
        if self.layer_stack() is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self.parent(), "Save Image", "",
            "TIFF Files (*.tif *.tiff);;JPEG Files (*.jpg *.jpeg);;All Files (*)")
        if path:
            self.save_master_to_path(path)

    def save_master_to_path(self, path):
        try:
            self.io_manager.save_master(path)
            self.current_file_path = os.path.abspath(path)
            self.parent().modified = False
            self.update_title_requested.emit()
            self.status_message_requested.emit(f"Saved master layer to: {path}")
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            QMessageBox.critical(self.parent(), "Save Error", f"Could not save file: {str(e)}")

    def select_exif_path(self):
        path, _ = QFileDialog.getOpenFileName(None, "Select file with exif data")
        if path:
            self.io_manager.set_exif_data(path)
            self.status_message_requested.emit(f"EXIF data extracted from {path}.")
        self.exif_dialog = ExifData(self.io_manager.exif_data, self.parent())
        self.exif_dialog.exec()

    def close_file(self):
        if self.parent().check_unsaved_changes():
            self.set_master_layer(None)
            self.blank_layer = None
            self.layer_collection.reset()
            self.current_file_path = ''
            self.parent().modified = False
            self.undo_manager.reset()
            self.image_viewer.clear_image()
            self.display_manager.thumbnail_list.clear()
            self.display_manager.update_thumbnails()
            self.update_title_requested.emit()
            self.status_message_requested.emit("File closed")
