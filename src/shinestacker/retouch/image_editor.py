import traceback
import numpy as np
from PySide6.QtWidgets import (QMainWindow, QFileDialog, QMessageBox, QAbstractItemView,
                               QVBoxLayout, QLabel, QDialog, QApplication)
from PySide6.QtGui import QPixmap, QPainter, QColor, QImage, QPen, QBrush, QGuiApplication, QCursor
from PySide6.QtCore import Qt, QTimer, QEvent, QPoint
from .. config.constants import constants
from .. config.gui_constants import gui_constants
from .brush import Brush
from .brush_controller import BrushController
from .undo_manager import UndoManager
from .file_loader import FileLoader
from .exif_data import ExifData
from .layer_collection import LayerCollection
from .io_manager import IOManager
from .brush_gradient import create_brush_gradient


class ImageEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.layer_collection = LayerCollection()
        self.io_manager = IOManager(self.layer_collection)
        self._brush_mask_cache = {}
        self.view_mode = 'master'
        self.temp_view_individual = False
        self.modified = False
        self.installEventFilter(self)
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(gui_constants.PAINT_REFRESH_TIMER)
        self.update_timer.timeout.connect(self.process_pending_updates)
        self.needs_update = False
        self.brush = Brush()
        self.brush_controller = BrushController(self.brush)
        self.undo_manager = UndoManager()
        self.undo_action = None
        self.redo_action = None
        self.undo_manager.stack_changed.connect(self.update_undo_redo_actions)
        self.loader_thread = None

    def keyPressEvent(self, event):
        if self.image_viewer.empty:
            return
        elif event.text() == '[':
            self.decrease_brush_size()
            return
        elif event.text() == ']':
            self.increase_brush_size()
            return
        elif event.text() == '{':
            self.decrease_brush_hardness()
            return
        elif event.text() == '}':
            self.increase_brush_hardness()
            return
        super().keyPressEvent(event)

    def process_pending_updates(self):
        if self.needs_update:
            self.display_master_layer()
            self.needs_update = False

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_X:
            self.start_temp_view()
            return True
        elif event.type() == QEvent.KeyRelease and event.key() == Qt.Key_X:
            self.end_temp_view()
            return True
        return super().eventFilter(obj, event)

    def _check_unsaved_changes(self) -> bool:
        if self.modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "The image stack has unsaved changes. Do you want to continue?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self.save_file()
                return True
            elif reply == QMessageBox.Discard:
                return True
            else:
                return False
        else:
            return True

    def sort_layers(self, order):
        if not hasattr(self, 'current_stack') or not hasattr(self, 'current_labels'):
            return
        master_index = -1
        master_label = None
        master_layer = None
        for i, label in enumerate(self.layer_collection.layer_labels):
            if label.lower() == "master":
                master_index = i
                master_label = self.layer_collection.layer_labels.pop(i)
                master_layer = self.layer_collection.layer_stack[i]
                self.layer_collection.layer_stack = np.delete(self.layer_collection.layer_stack, i, axis=0)
                break
        if order == 'asc':
            self.sorted_indices = sorted(range(len(self.layer_collection.layer_labels)),
                                         key=lambda i: self.layer_collection.layer_labels[i].lower())
        elif order == 'desc':
            self.sorted_indices = sorted(range(len(self.layer_collection.layer_labels)),
                                         key=lambda i: self.layer_collection.layer_labels[i].lower(),
                                         reverse=True)
        else:
            raise ValueError(f"Invalid sorting order: {order}")
        self.layer_collection.layer_labels = [self.layer_collection.layer_labels[i] for i in self.sorted_indices]
        self.layer_collection.layer_stack = self.layer_collection.layer_stack[self.sorted_indices]
        if master_index != -1:
            self.layer_collection.layer_labels.insert(0, master_label)
            self.layer_collection.layer_stack = np.insert(self.layer_collection.layer_stack, 0, master_layer, axis=0)
            self.layer_collection.master_layer = master_layer.copy()
            self.layer_collection.master_layer.setflags(write=True)
        self.update_thumbnails()
        if self.layer_collection.current_layer_idx >= self.layer_collection.number_of_layers():
            self.layer_collection.current_layer_idx = self.layer_collection.number_of_layers() - 1
        self.change_layer(self.layer_collection.current_layer)

    def update_title(self):
        title = constants.APP_TITLE
        if self.io_manager.current_file_path:
            title += f" - {self.io_manager.current_file_path.split('/')[-1]}"
            if self.modified:
                title += " *"
        self.window().setWindowTitle(title)

    def open_file(self, file_paths=None):
        if file_paths is None:
            file_paths, _ = QFileDialog.getOpenFileNames(
                self, "Open Image", "", "Images (*.tif *.tiff *.jpg *.jpeg);;All Files (*)")
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
        self.loading_dialog = QDialog(self)
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
        self.update_thumbnails()
        self.image_viewer.setup_brush_cursor()
        self.change_layer(0)
        self.image_viewer.reset_zoom()
        self.statusBar().showMessage(f"Loaded: {self.io_manager.current_file_path}")
        self.thumbnail_list.setFocus()
        self.update_title()

    def on_file_error(self, error_msg):
        QApplication.restoreOverrideCursor()
        self.loading_timer.stop()
        self.loading_dialog.accept()
        self.loading_dialog.deleteLater()
        QMessageBox.critical(self, "Error", error_msg)
        self.statusBar().showMessage(f"Error loading: {self.io_manager.current_file_path}")

    def mark_as_modified(self):
        self.modified = True
        self.update_title()

    def import_frames(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select frames", "",
                                                     "Images Images (*.tif *.tiff *.jpg *.jpeg);;All Files (*)")
        if file_paths:
            self.import_frames_from_files(file_paths)
        self.statusBar().showMessage("Imported selected frames")

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
        self.mark_as_modified()
        self.change_layer(0)
        self.image_viewer.reset_zoom()
        self.thumbnail_list.setFocus()
        self.update_thumbnails()

    def save_file(self):
        if self.save_master_only.isChecked():
            self.save_master()
        else:
            self.save_multilayer()

    def save_file_as(self):
        if self.save_master_only.isChecked():
            self.save_master_as()
        else:
            self.save_multilayer_as()

    def save_multilayer(self):
        if self.layer_collection.layer_stack is None:
            return
        if self.current_file_path != '':
            extension = self.current_file_path.split('.')[-1]
            if extension in ['tif', 'tiff']:
                self.save_multilayer_to_path(self.current_file_path)
                return
        self.save_multilayer_file_as()

    def save_multilayer_as(self):
        if self.layer_collection.layer_stack is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", "",
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
            self.update_title()
            self.statusBar().showMessage(f"Saved multilayer to: {path}")
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            QMessageBox.critical(self, "Save Error", f"Could not save file: {str(e)}")

    def save_master(self):
        if self.layer_collection.master_layer is None:
            return
        if self.current_file_path != '':
            self.save_master_to_path(self.current_file_path)
            return
        self.save_master_as()

    def save_master_as(self):
        if self.layer_collection.layer_stack is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", "",
                                              "TIFF Files (*.tif *.tiff);;JPEG Files (*.jpg *.jpeg);;All Files (*)")
        if path:
            self.save_master_to_path(path)

    def save_master_to_path(self, path):
        try:
            self.io_manager.save_master(path)
            self.io_manager.current_file_path = path
            self.modified = False
            self.update_title()
            self.statusBar().showMessage(f"Saved master layer to: {path}")
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            QMessageBox.critical(self, "Save Error", f"Could not save file: {str(e)}")

    def select_exif_path(self):
        path, _ = QFileDialog.getOpenFileName(None, "Select file with exif data")
        if path:
            self.io_manager.set_exif_data(path)
            self.statusBar().showMessage(f"EXIF data extracted from {path}.")
        self._exif_dialog = ExifData(self.io_manager.exif_data, self)
        self._exif_dialog.exec()

    def close_file(self):
        if self._check_unsaved_changes():
            self.layer_collection.master_layer = None
            self.blank_layer = None
            self.current_stack = None
            self.layer_collection.master_layer = None
            self.layer_collection.current_layer_idx = 0
            self.io_manager.current_file_path = ''
            self.modified = False
            self.undo_manager.reset()
            self.image_viewer.clear_image()
            self.update_thumbnails()
            self.update_title()

    def set_view_master(self):
        self.view_mode = 'master'
        self.temp_view_individual = False
        self.display_master_layer()
        self.statusBar().showMessage("View mode: Master")

    def set_view_individual(self):
        self.view_mode = 'individual'
        self.temp_view_individual = False
        self.display_current_layer()
        self.statusBar().showMessage("View mode: Individual layers")

    def start_temp_view(self):
        if not self.temp_view_individual and self.view_mode == 'master':
            self.temp_view_individual = True
            self.image_viewer.update_brush_cursor()
            self.display_current_layer()
            self.statusBar().showMessage("Temporary view: Individual layer (hold X)")

    def end_temp_view(self):
        if self.temp_view_individual:
            self.temp_view_individual = False
            self.image_viewer.update_brush_cursor()
            self.display_master_layer()
            self.statusBar().showMessage("View mode: Master")

    def display_current_view(self):
        if self.temp_view_individual or self.view_mode == 'individual':
            self.display_current_layer()
        else:
            self.display_master_layer()

    def display_master_layer(self):
        if self.layer_collection.master_layer is None:
            self.image_viewer.clear_image()
        else:
            qimage = self.numpy_to_qimage(self.layer_collection.master_layer)
            self.image_viewer.set_image(qimage)

    def create_thumbnail(self, layer, size):
        if layer.dtype == np.uint16:
            layer = (layer // 256).astype(np.uint8)
        height, width = layer.shape[:2]
        if layer.ndim == 3 and layer.shape[-1] == 3:
            qimg = QImage(layer.data, width, height, 3 * width, QImage.Format_RGB888)
        else:
            qimg = QImage(layer.data, width, height, width, QImage.Format_Grayscale8)
        return QPixmap.fromImage(qimg.scaled(*gui_constants.UI_SIZES['thumbnail'], Qt.KeepAspectRatio))

    def update_master_thumbnail(self):
        if self.layer_collection.master_layer is None:
            self.master_thumbnail_label.clear()
        else:
            thumb_size = gui_constants.UI_SIZES['thumbnail']
            master_thumb = self.create_thumbnail(self.layer_collection.master_layer, thumb_size)
            self.master_thumbnail_label.setPixmap(master_thumb)

    def update_thumbnails(self):
        self.update_master_thumbnail()
        self.thumbnail_list.clear()
        thumb_size = gui_constants.UI_SIZES['thumbnail']
        if self.layer_collection.layer_stack is None:
            return
        for i, (layer, label) in enumerate(zip(self.layer_collection.layer_stack, self.layer_collection.layer_labels)):
            thumbnail = self.create_thumbnail(layer, thumb_size)
            self._add_thumbnail_item(thumbnail, label, i, i == self.layer_collection.current_layer_idx)

    def _add_thumbnail_item(self, thumbnail, label, i, is_current):
        pass

    def change_layer(self, layer_idx):
        if 0 <= layer_idx < self.layer_collection.number_of_layers():
            view_state = self.image_viewer.get_view_state()
            self.layer_collection.current_layer_idx = layer_idx
            self.display_current_view()
            self.image_viewer.set_view_state(view_state)
            self.thumbnail_list.setCurrentRow(layer_idx)
            self.thumbnail_list.setFocus()
            self.image_viewer.update_brush_cursor()
            self.image_viewer.setFocus()

    def display_current_layer(self):
        if self.layer_collection.layer_stack is None:
            return
        layer = self.layer_collection.current_layer()
        qimage = self.numpy_to_qimage(layer)
        self.image_viewer.set_image(qimage)

    def numpy_to_qimage(self, array):
        if array.dtype == np.uint16:
            array = np.right_shift(array, 8).astype(np.uint8)

        if array.ndim == 2:
            height, width = array.shape
            return QImage(memoryview(array), width, height, width, QImage.Format_Grayscale8)
        elif array.ndim == 3:
            height, width, _ = array.shape
            if not array.flags['C_CONTIGUOUS']:
                array = np.ascontiguousarray(array)
            return QImage(memoryview(array), width, height, 3 * width, QImage.Format_RGB888)
        return QImage()

    def prev_layer(self):
        if self.layer_collection.layer_stack is not None:
            new_idx = max(0, self.layer_collection.current_layer_idx - 1)
            if new_idx != self.layer_collection.current_layer_idx:
                self.change_layer(new_idx)
                self.highlight_thumbnail(new_idx)

    def next_layer(self):
        if self.layer_collection.layer_stack is not None:
            new_idx = min(self.layer_collection.number_of_layers() - 1, self.layer_collection.current_layer_idx + 1)
            if new_idx != self.layer_collection.current_layer_idx:
                self.change_layer(new_idx)
                self.highlight_thumbnail(new_idx)

    def highlight_thumbnail(self, index):
        self.thumbnail_list.setCurrentRow(index)
        self.thumbnail_list.scrollToItem(self.thumbnail_list.item(index),
                                         QAbstractItemView.PositionAtCenter)

    def update_brush_size(self, slider_val):

        def slider_to_brush_size(slider_val):
            normalized = slider_val / gui_constants.BRUSH_SIZE_SLIDER_MAX
            size = gui_constants.BRUSH_SIZES['min'] + \
                gui_constants.BRUSH_SIZES['max'] * (normalized ** gui_constants.BRUSH_GAMMA)
            return max(gui_constants.BRUSH_SIZES['min'], min(gui_constants.BRUSH_SIZES['max'], size))

        self.brush.size = slider_to_brush_size(slider_val)
        self.update_brush_thumb()
        self.image_viewer.update_brush_cursor()
        self.clear_brush_cache()

    def increase_brush_size(self, amount=5):
        val = self.brush_size_slider.value()
        self.brush_size_slider.setValue(min(val + amount, self.brush_size_slider.maximum()))
        self.update_brush_size(val)

    def decrease_brush_size(self, amount=5):
        val = self.brush_size_slider.value()
        self.brush_size_slider.setValue(max(val - amount, self.brush_size_slider.minimum()))
        self.update_brush_size(val)

    def increase_brush_hardness(self, amount=2):
        val = self.hardness_slider.value()
        self.hardness_slider.setValue(min(val + amount, self.hardness_slider.maximum()))
        self.update_brush_hardness(val)

    def decrease_brush_hardness(self, amount=2):
        val = self.hardness_slider.value()
        self.hardness_slider.setValue(max(val - amount, self.hardness_slider.minimum()))
        self.update_brush_hardness(val)

    def update_brush_hardness(self, hardness):
        self.brush.hardness = hardness
        self.update_brush_thumb()
        self.image_viewer.update_brush_cursor()
        self.clear_brush_cache()

    def update_brush_opacity(self, opacity):
        self.brush.opacity = opacity
        self.update_brush_thumb()
        self.image_viewer.update_brush_cursor()

    def update_brush_flow(self, flow):
        self.brush.flow = flow
        self.update_brush_thumb()
        self.image_viewer.update_brush_cursor()

    def update_brush_thumb(self):
        width, height = gui_constants.UI_SIZES['brush_preview']
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        preview_size = min(self.brush.size, width + 30, height + 30)
        center_x, center_y = width // 2, height // 2
        radius = preview_size // 2
        if self.image_viewer.cursor_style == 'preview':
            gradient = create_brush_gradient(
                center_x, center_y, radius,
                self.brush.hardness,
                inner_color=QColor(*gui_constants.BRUSH_COLORS['inner']),
                outer_color=QColor(*gui_constants.BRUSH_COLORS['gradient_end']),
                opacity=self.brush.opacity
            )
            painter.setBrush(QBrush(gradient))
            painter.setPen(QPen(QColor(*gui_constants.BRUSH_COLORS['outer']), gui_constants.BRUSH_PREVIEW_LINE_WIDTH))
        elif self.image_viewer.cursor_style == 'outline':
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(*gui_constants.BRUSH_COLORS['outer']), gui_constants.BRUSH_PREVIEW_LINE_WIDTH))
        else:
            painter.setBrush(QBrush(QColor(*gui_constants.BRUSH_COLORS['cursor_inner'])))
            painter.setPen(QPen(QColor(*gui_constants.BRUSH_COLORS['pen']), gui_constants.BRUSH_PREVIEW_LINE_WIDTH))
        painter.drawEllipse(QPoint(center_x, center_y), radius, radius)
        if self.image_viewer.cursor_style == 'preview':
            painter.setPen(QPen(QColor(0, 0, 160)))
            painter.drawText(0, 10, f"Size: {int(self.brush.size)}px")
            painter.drawText(0, 25, f"Hardness: {self.brush.hardness}%")
            painter.drawText(0, 40, f"Opacity: {self.brush.opacity}%")
            painter.drawText(0, 55, f"Flow: {self.brush.flow}%")
        painter.end()
        self.brush_preview.setPixmap(pixmap)

    def clear_brush_cache(self):
        self._brush_mask_cache.clear()

    def allow_cursor_preview(self):
        return self.view_mode == 'master' and not self.temp_view_individual

    def copy_layer_to_master(self):
        if self.layer_collection.layer_stack is None or self.layer_collection.master_layer is None:
            return
        reply = QMessageBox.question(
            self,
            "Confirm Copy",
            "Warning: the current master layer will be erased\n\nDo you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.layer_collection.master_layer = self.layer_collection.current_layer().copy()
            self.layer_collection.master_layer.setflags(write=True)
            self.display_current_view()
            self.update_thumbnails()
            self.mark_as_modified()
            self.statusBar().showMessage(f"Copied layer {self.layer_collection.current_layer_idx + 1} to master")

    def copy_brush_area_to_master(self, view_pos):
        if self.layer_collection.layer_stack is None or self.layer_collection.number_of_layers() == 0 \
           or self.view_mode != 'master' or self.temp_view_individual:
            return
        area = self.brush_controller.apply_brush_operation(self.layer_collection.master_layer_copy,
                                                           self.layer_collection.current_layer(),
                                                           self.layer_collection.master_layer, self.mask_layer,
                                                           view_pos, self.image_viewer)
        self.undo_manager.extend_undo_area(*area)

    def begin_copy_brush_area(self, pos):
        if self.view_mode == 'master' and not self.temp_view_individual:
            self.mask_layer = self.blank_layer.copy()
            self.layer_collection.copy_master_layer()
            self.undo_manager.reset_undo_area()
            self.copy_brush_area_to_master(pos)
            self.needs_update = True
            if not self.update_timer.isActive():
                self.update_timer.start()
            self.mark_as_modified()

    def continue_copy_brush_area(self, pos):
        if self.view_mode == 'master' and not self.temp_view_individual:
            self.copy_brush_area_to_master(pos)
            self.needs_update = True
            if not self.update_timer.isActive():
                self.update_timer.start()
            self.mark_as_modified()

    def end_copy_brush_area(self):
        if self.update_timer.isActive():
            self.display_master_layer()
            self.update_master_thumbnail()
            self.undo_manager.save_undo_state(self.layer_collection.master_layer_copy, 'Brush Stroke')
            self.update_timer.stop()
            self.mark_as_modified()

    def update_undo_redo_actions(self, has_undo, undo_desc, has_redo, redo_desc):
        if self.undo_action:
            if has_undo:
                self.undo_action.setText(f"Undo {undo_desc}")
                self.undo_action.setEnabled(True)
            else:
                self.undo_action.setText("Undo")
                self.undo_action.setEnabled(False)
        if self.redo_action:
            if has_redo:
                self.redo_action.setText(f"Redo {redo_desc}")
                self.redo_action.setEnabled(True)
            else:
                self.redo_action.setText("Redo")
                self.redo_action.setEnabled(False)
