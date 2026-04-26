# pylint: disable=C0114, C0115, C0116, E0611, R0902, W0718, R0904, E1101, R0914, R0915
import os
import traceback
import numpy as np
import cv2
from PySide6.QtWidgets import (
    QMessageBox, QVBoxLayout, QLabel, QDialog, QRadioButton, QApplication, QProgressBar,
    QPushButton, QButtonGroup, QHBoxLayout)
from PySide6.QtGui import QGuiApplication, QCursor
from PySide6.QtCore import Qt, QObject, QTimer, Signal
from .. config.app_config import AppConfig
from .. algorithms.utils import EXTENSIONS_GUI_STR_IN, extension_tif, write_img
from .. algorithms.exif import get_exif, write_image_with_exif_data
from ..gui.folder_file_selection import SessionFileDialog
from .file_loader import FileLoader
from .io_threads import FileMultilayerSaver, FrameImporter
from .layer_collection import LayerCollectionHandler


class IOGuiHandler(QObject, LayerCollectionHandler):
    status_message_requested = Signal(str)
    update_title_requested = Signal()
    mark_as_modified_requested = Signal(bool)
    change_layer_requested = Signal(int)
    add_recent_file_requested = Signal(str)
    set_enabled_file_open_close_actions_requested = Signal(bool)

    def __init__(self, layer_collection, undo_manager, parent):
        QObject.__init__(self, parent)
        LayerCollectionHandler.__init__(self)
        self.undo_manager = undo_manager
        self.set_layer_collection(layer_collection)
        self.loader_thread = None
        self.display_manager = None
        self.image_viewer = None
        self.loading_dialog = None
        self.loading_timer = None
        self.saver_thread = None
        self.saving_dialog = None
        self.saving_timer = None
        self.current_file_path_master = ''
        self.current_file_path_multi = ''
        self.frame_importer_thread = None
        self.frame_loading_dialog = None
        self.frame_loading_timer = None
        self.progress_label = None
        self.progress_bar = None
        self.exif_data = None
        self.exif_path = ''
        self.exif_err_msg = ''
        self.save_master_only = None
        self.selected_format = None
        self.selected_bit_depth = None
        self.file_dialog = SessionFileDialog(AppConfig.get('input_folder_path'), self.parent())

    def reset_save_config(self):
        self.save_master_only = None
        self.selected_format = None
        self.selected_bit_depth = None

    def set_exif_data(self, data, path):
        self.exif_data = data
        self.exif_path = path

    def current_file_path(self):
        return self.current_file_path_master if self.save_master_only \
            else self.current_file_path_multi

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
        self.image_viewer.set_master_image_np(master_layer)
        self.set_blank_layer()
        self.undo_manager.reset()
        self.finish_loading_setup(f"Loaded file: {os.path.basename(self.current_file_path())}.")
        self.image_viewer.reset_zoom()
        if self.exif_err_msg != '':
            QMessageBox.warning(self.parent(), "Save Error", self.exif_err_msg)
            self.exif_err_msg = ''

    def on_file_error(self, error_msg):
        QApplication.restoreOverrideCursor()
        self.loading_timer.stop()
        self.loading_dialog.accept()
        self.loading_dialog.deleteLater()
        QMessageBox.critical(self.parent(), "Error", error_msg)
        self.current_file_path_master = ''
        self.current_file_path_multi = ''
        self.status_message_requested.emit(
            f"Error loading: {os.path.basename(self.current_file_path())}.")

    def on_frames_imported(self, stack, labels, master):
        QApplication.restoreOverrideCursor()
        self.frame_loading_timer.stop()
        self.frame_loading_dialog.hide()
        self.frame_loading_dialog.deleteLater()
        empty_viewer = self.image_viewer.empty()
        if self.number_of_layers() == 0:
            self.image_viewer.set_master_image_np(master)
            self.set_layer_stack(np.array(stack))
            if labels is None:
                labels = [f'Layer {i:03d}' for i in range(len(stack))]
            self.set_layer_labels(labels)
            self.set_master_layer(master)
            self.set_blank_layer()
        else:
            if labels is None:
                current_count = self.number_of_layers()
                labels = [f'Layer {current_count + i:03d}' for i in range(len(stack))]
            for img, label in zip(stack, labels):
                self.add_layer_label(label)
                self.add_layer(img)
        self.finish_loading_setup("Selected frames imported.")
        if empty_viewer:
            self.image_viewer.update_master_display()

    def on_frames_import_error(self, error_msg):
        QApplication.restoreOverrideCursor()
        self.frame_loading_timer.stop()
        self.frame_loading_dialog.hide()
        self.frame_loading_dialog.deleteLater()
        QMessageBox.critical(self.parent(), "Import Error", error_msg)
        self.status_message_requested.emit("Error importing frames.")

    def on_multilayer_saved(self):
        QApplication.restoreOverrideCursor()
        self.saving_timer.stop()
        self.saving_dialog.hide()
        self.saving_dialog.deleteLater()
        self.mark_as_modified_requested.emit(False)
        self.update_title_requested.emit()
        self.add_recent_file_requested.emit(self.current_file_path_multi)
        self.status_message_requested.emit(
            f"Saved multilayer to: {os.path.basename(self.current_file_path_multi)}.")

    def on_multilayer_save_error(self, error_msg):
        QApplication.restoreOverrideCursor()
        self.saving_timer.stop()
        self.saving_dialog.hide()
        self.saving_dialog.deleteLater()
        QMessageBox.critical(self.parent(), "Save Error", f"Could not save file: {error_msg}.")

    def open_file(self, file_paths=None):
        self.cleanup_old_threads()
        if file_paths is None:
            file_paths, _ = self.file_dialog.open_files(
                "Open Project", f"Images ({EXTENSIONS_GUI_STR_IN});;All Files (*)")
        if not file_paths:
            return
        if self.loader_thread and self.loader_thread.isRunning():
            if not self.loader_thread.wait(10000):
                raise RuntimeError("Loading timeout error.")
        if isinstance(file_paths, list) and len(file_paths) > 1:
            self.import_frames_from_files(file_paths)
            return
        path = file_paths[0] if isinstance(file_paths, list) else file_paths
        self.current_file_path_master = os.path.abspath(path)
        self.current_file_path_multi = os.path.abspath(path)
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
        self.exif_path = self.current_file_path_master
        try:
            self.exif_data = get_exif(self.exif_path)
            self.exif_err_msg = ''
        except Exception as e:
            traceback.print_stack()
            traceback.print_exc()
            self.exif_err_msg = "Can't read EXIF data from selected file " \
                "due to the following error:\n\n" \
                f"{str(e)}.\n\nEXIF data not loaded."
            self.exif_data = None

    def import_frames(self):
        file_paths, _ = self.file_dialog.open_files(
            "Select frames",
            f"Images Images ({EXTENSIONS_GUI_STR_IN});;All Files (*)")
        if file_paths:
            self.import_frames_from_files(file_paths)

    def import_frames_from_files(self, file_paths):
        if len(file_paths) > 20:
            result = QMessageBox.warning(
                None, "Warning",
                f"<b>Warning:</b> You selected {len(file_paths)} frames. "
                "This operation requires significant system memory "
                "and could freeze youd computer.<br><br>"
                "Are you sure you want to proceed?",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            if result != QMessageBox.StandardButton.Ok:
                return
        self.cleanup_old_threads()
        QGuiApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
        self.frame_loading_dialog = QDialog(self.parent())
        self.frame_loading_dialog.setWindowTitle("Loading Frames")
        self.frame_loading_dialog.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.frame_loading_dialog.setModal(True)
        layout = QVBoxLayout()
        self.progress_label = QLabel("Frames loading...")
        layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        self.frame_loading_dialog.setLayout(layout)
        self.frame_loading_timer = QTimer()
        self.frame_loading_timer.setSingleShot(True)
        self.frame_loading_timer.timeout.connect(self.frame_loading_dialog.show)
        self.frame_loading_timer.start(100)
        self.frame_importer_thread = FrameImporter(file_paths, self.master_layer())
        self.frame_importer_thread.finished.connect(self.on_frames_imported)
        self.frame_importer_thread.error.connect(self.on_frames_import_error)
        self.frame_importer_thread.progress.connect(self.update_import_progress)
        self.frame_importer_thread.start()
        if self.exif_data is None:
            self.exif_path = file_paths[0]
            self.exif_data = get_exif(self.exif_path)

    def update_import_progress(self, percent, filename):
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(percent)
        if hasattr(self, 'progress_label'):
            self.progress_label.setText(f"Loading: {filename} ({percent}%)")

    def finish_loading_setup(self, message):
        self.display_manager.update_thumbnails()
        self.mark_as_modified_requested.emit(True)
        self.change_layer_requested.emit(0)
        self.status_message_requested.emit(message)
        self.update_title_requested.emit()
        self.set_enabled_file_open_close_actions_requested.emit(True)
        self.add_recent_file_requested.emit(self.current_file_path_master)

    def save_file_as(self):
        dialog = QDialog(self.parent())
        dialog.setWindowTitle("Save As - Options")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Choose what to save:"))
        master_only_radio = QRadioButton("Master layer only")
        multilayer_radio = QRadioButton("Multilayer TIFF (more space required)")
        save_type_group = QButtonGroup(dialog)
        save_type_group.addButton(master_only_radio)
        save_type_group.addButton(multilayer_radio)
        master_only_radio.setChecked(
            self.save_master_only if self.save_master_only is not None else True)
        multilayer_radio.setChecked(
            not self.save_master_only if self.save_master_only is not None else False)
        layout.addWidget(master_only_radio)
        layout.addWidget(multilayer_radio)
        format_group = QVBoxLayout()
        format_group.addWidget(QLabel("Format options:"))
        tiff_radio = QRadioButton("TIFF")
        jpeg_radio = QRadioButton("JPEG")
        png_radio = QRadioButton("PNG")
        tiff_radio.setChecked(True)
        format_button_group = QButtonGroup(dialog)
        format_button_group.addButton(tiff_radio)
        format_button_group.addButton(jpeg_radio)
        format_button_group.addButton(png_radio)
        tiff_radio.setChecked(self.selected_format == "tiff")
        jpeg_radio.setChecked(self.selected_format == "jpeg")
        png_radio.setChecked(self.selected_format == "png")
        format_group.addWidget(tiff_radio)
        format_group.addWidget(jpeg_radio)
        format_group.addWidget(png_radio)
        layout.addLayout(format_group)
        bit_depth_group = QVBoxLayout()
        bit_depth_group.addWidget(QLabel("Bit depth:"))
        bit16_radio = QRadioButton("16-bit")
        bit8_radio = QRadioButton("8-bit")
        bit_depth_button_group = QButtonGroup(dialog)
        bit_depth_button_group.addButton(bit16_radio)
        bit_depth_button_group.addButton(bit8_radio)
        bit16_radio.setChecked(self.selected_bit_depth != 8)
        bit8_radio.setChecked(self.selected_bit_depth == 8)
        bit_depth_group.addWidget(bit16_radio)
        bit_depth_group.addWidget(bit8_radio)
        layout.addLayout(bit_depth_group)
        warning_label = QLabel("")
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: orange;")
        layout.addWidget(warning_label)
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)

        def update_ui_state():
            multilayer_selected = multilayer_radio.isChecked()
            jpeg_selected = jpeg_radio.isChecked()
            png_selected = png_radio.isChecked()
            bit16_selected = bit16_radio.isChecked()
            tiff_radio.setEnabled(not multilayer_selected)
            jpeg_radio.setEnabled(not multilayer_selected)
            png_radio.setEnabled(not multilayer_selected)
            bit8_radio.setEnabled(not (multilayer_selected or jpeg_selected))
            bit16_radio.setEnabled(not (multilayer_selected or jpeg_selected))
            if multilayer_selected:
                tiff_radio.setChecked(True)
                bit16_radio.setChecked(True)
                warning_label.setText("")
            elif jpeg_selected:
                bit8_radio.setChecked(True)
                warning_label.setText("")
            elif png_selected and bit16_selected:
                warning_label.setText(
                    "Note: Saving 16-bit PNG will result in loss of EXIF metadata.")
            else:
                warning_label.setText("")

        master_only_radio.toggled.connect(update_ui_state)
        multilayer_radio.toggled.connect(update_ui_state)
        tiff_radio.toggled.connect(update_ui_state)
        jpeg_radio.toggled.connect(update_ui_state)
        png_radio.toggled.connect(update_ui_state)
        bit8_radio.toggled.connect(update_ui_state)
        bit16_radio.toggled.connect(update_ui_state)
        update_ui_state()

        def on_save():
            self.save_master_only = master_only_radio.isChecked()
            self.selected_format = "tiff" \
                if tiff_radio.isChecked() else "jpeg" if jpeg_radio.isChecked() else "png"
            self.selected_bit_depth = 8 if bit8_radio.isChecked() else 16
            dialog.accept()
            if self.save_master_only:
                self.save_master()
            else:
                self.save_multilayer_as()

        def on_cancel():
            dialog.reject()

        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(on_cancel)
        dialog.exec_()

    def save_master(self):
        if self.layer_stack() is None:
            return
        filters = {
            "png": "PNG Files (*.png *.PNG);;All Files (*)",
            "tiff": "TIFF Files (*.tif *.tiff *.TIF *.TIFF);;All Files (*)",
            "jpeg": "JPEG Files (*.jpg *.jpeg *.JPG *.JPEG);;All Files (*)"
        }
        extensions = {
            "png": [".png"],
            "tiff": [".tif", ".tiff"],
            "jpeg": [".jpg", ".jpeg"]
        }
        root, ext = os.path.splitext(self.current_file_path_master)
        if ext.lower() in extensions[self.selected_format]:
            current_file_path = self.current_file_path_master
        else:
            current_file_path = root + "." + self.selected_format
        path, _selected_filter = self.file_dialog.save_file(
            "Save Master Image", filters[self.selected_format],
            current_file_path)
        if not path:
            return
        self.save_master_to_path(path)

    def save_master_to_path(self, path):
        try:
            img = cv2.cvtColor(self.master_layer(), cv2.COLOR_RGB2BGR)
            if self.selected_bit_depth == 8 and img.dtype == np.uint16:
                img = (img // 256).astype(np.uint8)
            if self.selected_format == "png" and img.dtype == np.uint16:
                write_img(path, img)
            else:
                write_image_with_exif_data(self.exif_data, img, path)
            self.current_file_path_master = os.path.abspath(path)
            self.update_title_requested.emit()
            self.add_recent_file_requested.emit(self.current_file_path_master)
            self.status_message_requested.emit(
                f"Saved master layer to files: {os.path.basename(path)}.")
        except Exception as e:
            traceback.print_exc()
            msg = f"Could not save file: {str(e)}."
            self.status_message_requested.emit(msg)
            QMessageBox.critical(self.parent(), "Save Error", msg)

    def save_file(self):
        if self.save_master_only is None:
            self.save_file_as()
        elif self.save_master_only:
            if self.current_file_path_master:
                self.save_master_to_path(self.current_file_path_master)
            else:
                self.save_master()
        else:
            self.save_multilayer()

    def save_multilayer(self):
        if self.layer_stack() is None:
            return
        if self.current_file_path_multi != '':
            if extension_tif(self.current_file_path_multi):
                self.save_multilayer_to_path(self.current_file_path_multi)
                return
        else:
            self.save_multilayer_as()

    def save_multilayer_as(self):
        if self.layer_stack() is None:
            return
        root, ext = os.path.splitext(self.current_file_path_multi)
        if ext.lower() in ['.tif', '.tiff']:
            current_file_path = self.current_file_path_multi
        else:
            current_file_path = root + ".tif"
        path, _ = self.file_dialog.save_file(
            "Save Image", "TIFF Files (*.tif *.tiff *.TIF *.TIFF);;All Files (*)",
            current_file_path)
        if path:
            if not extension_tif(path):
                path += '.tif'
            self.save_multilayer_to_path(path)

    def save_multilayer_to_path(self, path):
        self.cleanup_old_threads()
        try:
            master_layer = {'Master': self.master_layer().copy()}
            individual_layers = dict(zip(
                self.layer_labels(),
                [layer.copy() for layer in self.layer_stack()]
            ))
            images_dict = {**master_layer, **individual_layers}
            self.saver_thread = FileMultilayerSaver(
                images_dict, path, exif_path=self.exif_path)
            self.saver_thread.finished.connect(self.on_multilayer_saved)
            self.saver_thread.error.connect(self.on_multilayer_save_error)
            QGuiApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
            self.saving_dialog = QDialog(self.parent())
            self.saving_dialog.setWindowTitle("Saving")
            self.saving_dialog.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
            self.saving_dialog.setModal(True)
            layout = QVBoxLayout()
            layout.addWidget(QLabel("Saving file..."))
            self.saving_dialog.setLayout(layout)
            self.saving_timer = QTimer()
            self.saving_timer.setSingleShot(True)
            self.saving_timer.timeout.connect(self.saving_dialog.show)
            self.saving_timer.start(100)
            self.saver_thread.start()
        except Exception as e:
            traceback.print_exc()
            msg = f"Could not save file: {str(e)}."
            self.status_message_requested.emit(msg)
            QMessageBox.critical(self.parent(), "Save Error", msg)

    def close_file(self):
        self.mark_as_modified_requested.emit(False)
        self.layer_collection.reset()
        self.current_file_path_master = ''
        self.current_file_path_multi = ''
        self.undo_manager.reset()
        self.image_viewer.clear_image()
        self.display_manager.thumbnail_list.clear()
        self.display_manager.update_thumbnails()
        self.update_title_requested.emit()
        self.set_enabled_file_open_close_actions_requested.emit(False)
        self.status_message_requested.emit("File closed.")
        self.reset_save_config()

    def cleanup_old_threads(self):
        if self.loader_thread and self.loader_thread.isFinished():
            self.loader_thread = None
        if self.frame_importer_thread and self.frame_importer_thread.isFinished():
            self.frame_importer_thread = None
        if self.saver_thread and self.saver_thread.isFinished():
            self.saver_thread = None
