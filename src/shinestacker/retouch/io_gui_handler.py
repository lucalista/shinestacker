import traceback
import numpy as np
from PySide6.QtWidgets import QFileDialog, QMessageBox, QVBoxLayout, QLabel, QDialog, QApplication
from PySide6.QtGui import QGuiApplication, QCursor
from PySide6.QtCore import Qt, QObject, QTimer, Signal
from .file_loader import FileLoader
from .exif_data import ExifData


class IOGuiHandler(QObject):
    status_message_requested = Signal(str)

    def __init__(self, io_manager, layer_collection, undo_manager, parent):
        super().__init__(parent)
        self.io_manager = io_manager
        self.undo_manager = undo_manager
        self.layer_collection = layer_collection
        self.loader_thread = None

    def setup_ui(self, display_manager, image_viewer):
        self.display_manager = display_manager
        self.image_viewer = image_viewer

    def on_file_loaded(self, stack, labels, master_layer):
        QApplication.restoreOverrideCursor()
        self.loading_timer.stop()
        self.loading_dialog.hide()
        self.layer_collection.layer_stack = stack
        if labels is None:
            self.layer_collection.layer_labels = [f'Layer {i:03d}' for i in range(len(stack))]
        else:
            self.layer_collection.layer_labels = labels
        self.layer_collection.master_layer = master_layer
        self.modified = False
        self.undo_manager.reset()
        self.blank_layer = np.zeros(master_layer.shape[:2])
        self.display_manager.update_thumbnails()
        self.image_viewer.setup_brush_cursor()
        self.parent().change_layer(0)
        self.image_viewer.reset_zoom()
        self.status_message_requested.emit(f"Loaded: {self.io_manager.current_file_path}")
        self.parent().thumbnail_list.setFocus()
        self.parent().update_title()

    def on_file_error(self, error_msg):
        QApplication.restoreOverrideCursor()
        self.loading_timer.stop()
        self.loading_dialog.accept()
        self.loading_dialog.deleteLater()
        QMessageBox.critical(self, "Error", error_msg)
        elf.status_message_requested.emit(f"Error loading: {self.io_manager.current_file_path}")

    def open_file(self, file_paths=None):
        if file_paths is None:
            file_paths, _ = QFileDialog.getOpenFileNames(
                self.parent(), "Open Image", "", "Images (*.tif *.tiff *.jpg *.jpeg);;All Files (*)")
        if not file_paths:
            return
        if self.loader_thread and self.loader_thread.isRunning():
            if not self.loader_thread.wait(10000):
                raise RuntimeError("Loading timeout error.")
        if isinstance(file_paths, list) and len(file_paths) > 1:
            self.import_frames_from_files(file_paths)
            return
        path = file_paths[0] if isinstance(file_paths, list) else file_paths
        self.io_manager.current_file_path = path
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
        file_paths, _ = QFileDialog.getOpenFileNames(self.parent(), "Select frames", "",
                                                     "Images Images (*.tif *.tiff *.jpg *.jpeg);;All Files (*)")
        if file_paths:
            self.import_frames_from_files(file_paths)
        elf.status_message_requested.emit("Imported selected frames")

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
        if self.layer_collection.layer_stack is None and len(stack) > 0:
            self.layer_collection.layer_stack = np.array(stack)
            self.layer_collection.layer_labels = labels
            self.layer_collection.master_layer = master
            self.blank_layer = np.zeros(master.shape[:2])
        else:
            for img, label in zip(stack, labels):
                self.layer_collection.layer_labels.append(label)
                self.layer_collection.layer_stack = np.append(
                    self.layer_collection.layer_stack, [img], axis=0)
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
        if self.layer_collection.layer_stack is None:
            return
        if self.io_manager.current_file_path != '':
            extension = self.io_manager.current_file_path.split('.')[-1]
            if extension in ['tif', 'tiff']:
                self.save_multilayer_to_path(self.io_manager.current_file_path)
                return

    def save_multilayer_as(self):
        if self.layer_collection.layer_stack is None:
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
            self.io_manager.current_file_path = path
            self.modified = False
            self.parent().update_title()
            elf.status_message_requested.emit(f"Saved multilayer to: {path}")
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            QMessageBox.critical(self.parent(), "Save Error", f"Could not save file: {str(e)}")

    def save_master(self):
        if self.layer_collection.master_layer is None:
            return
        if self.io_manager.current_file_path != '':
            self.save_master_to_path(self.io_manager.current_file_path)
            return
        self.save_master_as()

    def save_master_as(self):
        if self.layer_collection.layer_stack is None:
            return
        path, _ = QFileDialog.getSaveFileName(self.parent(), "Save Image", "",
                                              "TIFF Files (*.tif *.tiff);;JPEG Files (*.jpg *.jpeg);;All Files (*)")
        if path:
            self.save_master_to_path(path)

    def save_master_to_path(self, path):
        try:
            self.io_manager.save_master(path)
            self.io_manager.current_file_path = path
            self.modified = False
            self.parent.update_title()
            elf.status_message_requested.emit(f"Saved master layer to: {path}")
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            QMessageBox.critical(self.parent(), "Save Error", f"Could not save file: {str(e)}")

    def select_exif_path(self):
        path, _ = QFileDialog.getOpenFileName(None, "Select file with exif data")
        if path:
            self.io_manager.set_exif_data(path)
            elf.status_message_requested.emit(f"EXIF data extracted from {path}.")
        self._exif_dialog = ExifData(self.io_manager.exif_data, self.parent())
        self._exif_dialog.exec()

    def close_file(self):
        if self.parent()._check_unsaved_changes():
            self.layer_collection.master_layer = None
            self.blank_layer = None
            self.current_stack = None
            self.layer_collection.reset()
            self.io_manager.current_file_path = ''
            self.modified = False
            self.undo_manager.reset()
            self.image_viewer.clear_image()
            self.display_manager.thumbnail_list.clear()
            self.display_manager.update_thumbnails()
            self.parent().update_title()
            self.status_message_requested.emit("File closed")

