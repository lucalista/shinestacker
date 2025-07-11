import traceback
import numpy as np
from PySide6.QtWidgets import (QMainWindow, QFileDialog, QMessageBox, QAbstractItemView,
                               QVBoxLayout, QLabel, QDialog, QApplication)
from PySide6.QtGui import QPixmap, QPainter, QColor, QImage, QPen, QBrush, QRadialGradient, QGuiApplication, QCursor
from PySide6.QtCore import Qt, QTimer, QEvent, QPoint
from focusstack.algorithms.multilayer import write_multilayer_tiff_from_images
from focusstack.config.constants import constants
from focusstack.retouch.gui_constants import gui_constants
from focusstack.retouch.brush import Brush
from focusstack.retouch.brush_controller import BrushController
from focusstack.retouch.undo_manager import UndoManager
from focusstack.retouch.file_loader import FileLoader


def slider_to_brush_size(slider_val):
    normalized = slider_val / gui_constants.BRUSH_SIZE_SLIDER_MAX
    size = gui_constants.BRUSH_SIZES['min'] + gui_constants.BRUSH_SIZES['max'] * (normalized ** gui_constants.BRUSH_GAMMA)
    return max(gui_constants.BRUSH_SIZES['min'], min(gui_constants.BRUSH_SIZES['max'], size))


def create_brush_gradient(center_x, center_y, radius, hardness, inner_color=None, outer_color=None, opacity=100):
    gradient = QRadialGradient(center_x, center_y, float(radius))
    inner = inner_color if inner_color is not None else gui_constants.BRUSH_COLORS['inner']
    outer = outer_color if outer_color is not None else gui_constants.BRUSH_COLORS['gradient_end']
    inner_with_opacity = QColor(inner)
    inner_with_opacity.setAlpha(int(float(inner.alpha()) * float(opacity) / 100.0))
    if hardness < 100:
        hardness_normalized = float(hardness) / 100.0
        gradient.setColorAt(0.0, inner_with_opacity)
        gradient.setColorAt(hardness_normalized, inner_with_opacity)
        gradient.setColorAt(1.0, outer)
    else:
        gradient.setColorAt(0.0, inner_with_opacity)
        gradient.setColorAt(1.0, inner_with_opacity)
    return gradient


class ImageEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_stack = None
        self.master_layer = None
        self.current_layer = 0
        self._brush_mask_cache = {}
        self.view_mode = 'master'
        self.temp_view_individual = False
        self.current_file_path = ''
        self.exif_path = ''
        self.modified = False
        self.sort_order = 'original'
        self.installEventFilter(self)
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(gui_constants.PAINT_REFRESH_TIMER)
        self.update_timer.timeout.connect(self.process_pending_updates)
        self.needs_update = False
        self.brush = Brush()
        self.brush_controller = BrushController(self.brush)
        self.undo_manager = UndoManager()

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
                self._save_file()
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
        self.sort_order = order
        if order == 'original':
            if self.current_file_path:
                self.current_stack, self.current_labels = self.load_tiff_stack(self.current_file_path)
                self.update_thumbnails()
                if self.current_layer >= len(self.current_stack):
                    self.current_layer = len(self.current_stacke) - 1
                self.change_layer(self.current_layer)
            return
        master_index = -1
        master_label = None
        master_layer = None
        for i, label in enumerate(self.current_labels):
            if label.lower() == "master":
                master_index = i
                master_label = self.current_labels.pop(i)
                master_layer = self.current_stack[i]
                self.current_stack = np.delete(self.current_stack, i, axis=0)
                break
        if order == 'asc':
            sorted_indices = sorted(range(len(self.current_labels)),
                                    key=lambda i: self.current_labels[i].lower())
        else:
            sorted_indices = sorted(range(len(self.current_labels)),
                                    key=lambda i: self.current_labels[i].lower(),
                                    reverse=True)
        self.current_labels = [self.current_labels[i] for i in sorted_indices]
        self.current_stack = self.current_stack[sorted_indices]
        if master_index != -1:
            self.current_labels.insert(0, master_label)
            self.current_stack = np.insert(self.current_stack, 0, master_layer, axis=0)
            self.master_layer = master_layer.copy()
            self.master_layer.setflags(write=True)
        self.update_thumbnails()
        if self.current_layer >= len(self.current_stack):
            self.current_layer = len(self.current_stack) - 1
        self.change_layer(self.current_layer)

    def update_title(self):
        title = constants.APP_TITLE
        if self.current_file_path:
            title += f" - {self.current_file_path.split('/')[-1]}"
            if self.modified:
                title += " *"
        self.setWindowTitle(title)

    def open_file(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open Image", "", "Images (*.tif *.tiff *.png *.jpg)")
        if not path:
            return
        self.current_file_path = path
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
        self.current_stack = stack
        self.current_labels = labels
        self.master_layer = master_layer
        self.blank_layer = np.zeros(master_layer.shape[:2])
        self.update_thumbnails()
        self.change_layer(0)
        self.image_viewer.reset_zoom()
        self.statusBar().showMessage(f"Loaded: {self.current_file_path}")
        self.thumbnail_list.setFocus()
        self.update_title()

    def on_file_error(self, error_msg):
        QApplication.restoreOverrideCursor()
        self.loading_timer.stop()
        self.loading_dialog.accept()
        self.loading_dialog.deleteLater()
        QMessageBox.critical(self, "Error", error_msg)
        self.statusBar().showMessage(f"Error loading: {self.current_file_path}")

    def mark_as_modified(self):
        self.modified = True
        self.update_title()

    def save_file(self):
        if self.current_stack is None:
            return
        if self.current_file_path != '':
            self._save_to_path(self.current_file_path)
            self.modified = False
            self.update_title()
        else:
            self.save_file_as()

    def select_exif_path(self):
        if self.current_stack is None:
            return
        dialog = QFileDialog()
        path = dialog.getExistingDirectory(None, "Select EXIF path")
        if path:
            self.exif_path = path
            self.statusBar().showMessage(f"EXIF path set to {path}.")

    def save_file_as(self):
        if self.current_stack is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", "",
                                              "TIFF Files (*.tif *.tiff);;All Files (*)")
        if path:
            if not path.lower().endswith(('.tif', '.tiff')):
                path += '.tiff'
            self._save_to_path(path)
            self.statusBar().showMessage(f"Saved: {path}")

    def _save_to_path(self, path):
        try:
            master_layer = {'Master': self.master_layer}
            individual_layers = {label: image for label, image in zip(self.current_labels, self.current_stack)}
            write_multilayer_tiff_from_images({**master_layer, **individual_layers}, path, exif_path=self.exif_path)
            self.statusBar().showMessage(f"Saved: {path}")
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            QMessageBox.critical(self, "Save Error", f"Could not save file: {str(e)}")

    def new_file(self):
        if self._check_unsaved_changes():
            self.master_layer = None
            self.blank_layer = None
            self.current_stack = None
            self.master_layer = None
            self.current_layer = 0
            self.current_file_path = ''
            self.display_master_layer()
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
        if self.master_layer is None:
            self.image_viewer.clear_image()
        else:
            qimage = self.numpy_to_qimage(self.master_layer)
            self.image_viewer.set_image(qimage)

    def create_thumbnail(self, layer, size):
        if layer.ndim == 3 and layer.shape[-1] == 3:
            return self.create_rgb_thumbnail(layer)
        else:
            return self.create_grayscale_thumbnail(layer)

    def update_master_thumbnail(self):
        if self.master_layer is None:
            self.master_thumbnail_label.clear()
        else:
            thumb_size = gui_constants.UI_SIZES['thumbnail']
            master_thumb = self.create_thumbnail(self.master_layer, thumb_size)
            self.master_thumbnail_label.setPixmap(master_thumb)

    def update_thumbnails(self):
        self.update_master_thumbnail()
        self.thumbnail_list.clear()
        thumb_size = gui_constants.UI_SIZES['thumbnail']
        if self.current_stack is None:
            return
        for i, (layer, label) in enumerate(zip(self.current_stack, self.current_labels)):
            thumbnail = self.create_thumbnail(layer, thumb_size)
            self._add_thumbnail_item(thumbnail, label, i == self.current_layer)

    def _add_thumbnail_item(self, thumbnail, label, is_current):
        pass

    def create_rgb_thumbnail(self, layer):
        if layer.dtype == np.uint16:
            layer = (layer // 256).astype(np.uint8)
        height, width, _ = layer.shape
        qimg = QImage(layer.data, width, height, 3 * width, QImage.Format_RGB888)
        return QPixmap.fromImage(qimg.scaled(*gui_constants.UI_SIZES['thumbnail'], Qt.KeepAspectRatio))

    def create_grayscale_thumbnail(self, layer):
        if layer.dtype == np.uint16:
            p2, p98 = np.percentile(layer, (2, 98))
            layer = np.clip(np.multiply(np.subtract(layer, p2), 255.0 / (p98 - p2)), 0, 255).astype(np.uint8)
        height, width = layer.shape
        qimg = QImage(layer.data, width, height, width, QImage.Format_Grayscale8)
        return QPixmap.fromImage(qimg.scaled(*gui_constants.UI_SIZES['thumbnail'], Qt.KeepAspectRatio))

    def change_layer(self, layer_idx):
        if 0 <= layer_idx < len(self.current_stack):
            view_state = self.image_viewer.get_view_state()
            self.current_layer = layer_idx
            self.display_current_view()
            self.image_viewer.set_view_state(view_state)
            self.thumbnail_list.setCurrentRow(layer_idx)
            self.thumbnail_list.setFocus()
            self.image_viewer.update_brush_cursor()
            self.image_viewer.setFocus()

    def change_layer_item(self, item):
        layer_idx = self.thumbnail_list.row(item)
        self.change_layer(layer_idx)

    def display_current_layer(self):
        if self.current_stack is None:
            return
        layer = self.current_stack[self.current_layer]
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
        if self.current_stack is not None:
            new_idx = max(0, self.current_layer - 1)
            if new_idx != self.current_layer:
                self.change_layer(new_idx)
                self.highlight_thumbnail(new_idx)

    def next_layer(self):
        if self.current_stack is not None:
            new_idx = min(len(self.current_stack) - 1, self.current_layer + 1)
            if new_idx != self.current_layer:
                self.change_layer(new_idx)
                self.highlight_thumbnail(new_idx)

    def highlight_thumbnail(self, index):
        self.thumbnail_list.setCurrentRow(index)
        self.thumbnail_list.scrollToItem(self.thumbnail_list.item(index),
                                         QAbstractItemView.PositionAtCenter)

    def update_brush_size(self, slider_val):
        self.brush.size = slider_to_brush_size(slider_val)
        self.update_brush_thumb()
        self.image_viewer.update_brush_cursor()
        self.clear_brush_cache()

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
                inner_color=gui_constants.BRUSH_COLORS['inner'],
                outer_color=gui_constants.BRUSH_COLORS['gradient_end'],
                opacity=self.brush.opacity
            )
            painter.setBrush(QBrush(gradient))
            painter.setPen(QPen(gui_constants.BRUSH_COLORS['outer'], gui_constants.BRUSH_PREVIEW_LINE_WIDTH))
        elif self.image_viewer.cursor_style == 'outline':
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(gui_constants.BRUSH_COLORS['outer'], gui_constants.BRUSH_PREVIEW_LINE_WIDTH))
        else:
            painter.setBrush(QBrush(gui_constants.BRUSH_COLORS['cursor_inner']))
            painter.setPen(QPen(gui_constants.BRUSH_COLORS['pen'], gui_constants.BRUSH_PREVIEW_LINE_WIDTH))
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
        if self.current_stack is None or self.master_layer is None:
            return
        reply = QMessageBox.question(
            self,
            "Confirm Copy",
            "Warning: the current master layer will be erased\n\nDo you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.master_layer = self.current_stack[self.current_layer].copy()
            self.master_layer.setflags(write=True)
            self.display_current_view()
            self.update_thumbnails()
            self.mark_as_modified()
            self.statusBar().showMessage(f"Copied layer {self.current_layer + 1} to master")

    def copy_brush_area_to_master(self, view_pos):
        if self.current_layer is None or self.current_stack is None or len(self.current_stack) == 0 \
           or self.view_mode != 'master' or self.temp_view_individual:
            return
        area = self.brush_controller.apply_brush_operation(self.master_layer_copy,
                                                           self.current_stack[self.current_layer],
                                                           self.master_layer, self.mask_layer,
                                                           view_pos, self.image_viewer)
        self.undo_manager.extend_undo_area(*area)

    def begin_copy_brush_area(self, pos):
        if self.view_mode == 'master' and not self.temp_view_individual:
            self.mask_layer = self.blank_layer.copy()
            self.master_layer_copy = self.master_layer.copy()
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
            self.undo_manager.save_undo_state(self.master_layer_copy)
            self.update_timer.stop()
            self.mark_as_modified()
