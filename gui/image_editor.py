import webbrowser
import numpy as np
import tifffile
from psdtags import PsdChannelId
from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QAbstractItemView
from PySide6.QtGui import QPixmap, QPainter, QColor, QImage, QPen, QBrush, QRadialGradient
from PySide6.QtCore import Qt, QTimer, QEvent, QPoint, QDateTime
from algorithms.multilayer import read_multilayer_tiff, write_multilayer_tiff_from_images
from gui.image_viewer import BRUSH_COLORS, PAINT_REFRESH_TIMER
from gui.brush_controller import BrushController, BRUSH_SIZES

THUMB_WIDTH = 120
THUMB_HEIGHT = 80
IMG_WIDTH = 100
IMG_HEIGHT = 80

BRUSH_SIZE_SLIDER_MAX = 1000

UI_SIZES = {
    'brush_preview': (100, 80),
    'thumbnail': (IMG_WIDTH, IMG_HEIGHT),
    'master_thumb': (THUMB_WIDTH, THUMB_HEIGHT)
}


def calculate_gamma():
    if BRUSH_SIZES['mid'] <= BRUSH_SIZES['min'] or BRUSH_SIZES['max'] <= 0:
        return 1.0
    ratio = (BRUSH_SIZES['mid'] - BRUSH_SIZES['min']) / BRUSH_SIZES['max']
    half_point = BRUSH_SIZE_SLIDER_MAX / 2
    if ratio <= 0:
        return 1.0
    gamma = np.log(ratio) / np.log(half_point / BRUSH_SIZE_SLIDER_MAX)
    return gamma


BRUSH_GAMMA = calculate_gamma()


def slider_to_brush_size(slider_val):
    normalized = slider_val / BRUSH_SIZE_SLIDER_MAX
    size = BRUSH_SIZES['min'] + BRUSH_SIZES['max'] * (normalized ** BRUSH_GAMMA)
    return max(BRUSH_SIZES['min'], min(BRUSH_SIZES['max'], size))


def create_brush_gradient(center_x, center_y, radius, hardness, inner_color=None, outer_color=None, opacity=100):
    gradient = QRadialGradient(center_x, center_y, float(radius))
    inner = inner_color if inner_color is not None else BRUSH_COLORS['inner']
    outer = outer_color if outer_color is not None else BRUSH_COLORS['gradient_end']
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
        self.cursor_style = 'preview'
        self.view_mode = 'master'
        self.temp_view_individual = False
        self.current_file_path = None
        self.modified = False
        self.undo_stack = []
        self.max_undo_steps = 10
        self.sort_order = 'original'
        self.installEventFilter(self)
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(PAINT_REFRESH_TIMER)
        self.update_timer.timeout.connect(self.process_pending_updates)
        self.needs_update = False
        self.brush_controller = BrushController()

    def process_pending_updates(self):
        if self.needs_update:
            self.display_current_view()
            self.mark_as_modified()
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

    def website(self):
        webbrowser.open("https://github.com/lucalista/focusstack/blob/main/docs/main.md")

    def sort_layers(self, order):
        if not hasattr(self, 'current_stack') or not hasattr(self, 'current_labels'):
            return
        self.sort_order = order
        if order == 'original':
            if self.current_file_path:
                self.current_stack, self.current_labels = self.load_tiff_stack(self.current_file_path)
                self.update_thumbnails()
                if self.current_layer >= len(self.current_stack):
                    self.current_layer = len(self.current_stack) - 1
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

    def load_tiff_stack(self, path):
        try:
            psd_data = read_multilayer_tiff(path)
            layers = []
            labels = []
            for layer in reversed(psd_data.layers.layers):
                channels = {}
                for channel in layer.channels:
                    channels[channel.channelid] = channel.data
                if PsdChannelId.CHANNEL0 in channels:
                    img = np.stack([
                        channels[PsdChannelId.CHANNEL0],
                        channels[PsdChannelId.CHANNEL1],
                        channels[PsdChannelId.CHANNEL2]
                    ], axis=-1)
                    layers.append(img)
                    labels.append(layer.name)
            if layers:
                stack = np.array(layers)
                if labels:
                    master_indices = [i for i, label in enumerate(labels) if label.lower() == "master"]
                    if master_indices:
                        master_index = master_indices[0]
                        master_label = labels.pop(master_index)
                        master_layer = stack[master_index]
                        stack = np.delete(stack, master_index, axis=0)
                        labels.insert(0, master_label)
                        stack = np.insert(stack, 0, master_layer, axis=0)
                    return stack, labels
                return stack, labels
        except Exception:
            try:
                stack = tifffile.imread(path)
                if stack.ndim == 3:
                    return stack, None
                return None, None
            except Exception:
                return None, None

    def open_file(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open Image", "", "Images (*.tif *.tiff *.png *.jpg)")
        if path:
            self.current_file_path = path
            self.current_stack, self.current_labels = self.load_tiff_stack(path)
            if self.current_stack is not None and len(self.current_stack) > 0:
                master_indices = [i for i, label in enumerate(self.current_labels) if label.lower() == "master"]
                master_index = -1 if len(master_indices) == 0 else master_indices[0]
                if master_index == -1:
                    self.master_layer = self.current_stack[0].copy()
                else:
                    self.current_labels.pop(master_index)
                    self.master_layer = self.current_stack[master_index].copy()
                    indices = list(range(len(self.current_stack)))
                    indices.remove(master_index)
                    self.current_stack = self.current_stack[indices]
                self.master_layer.setflags(write=True)
                if self.current_labels is None:
                    self.current_labels = [f"Layer {i + 1}" for i in range(len(self.current_stack))]
                self.blank_layer = np.zeros(self.master_layer.shape[:2])
            self.update_thumbnails()
            self.change_layer(0)
            self.image_viewer.reset_zoom()
            self.statusBar().showMessage(f"Loaded: {path}")
            self.thumbnail_list.setFocus()

    def mark_as_modified(self):
        self.modified = True
        title = "Focus Stack Editor"
        if self.current_file_path:
            title += f" - {self.current_file_path}"
        self.setWindowTitle(title + "*")

    def save_file(self):
        if self.current_stack is None:
            return
        if self.current_file_path:
            self._save_to_path(self.current_file_path)
            self.modified = False
            self.setWindowTitle("Focus Stack Editor")
        else:
            self.save_file_as()

    def save_file_as(self):
        if self.current_stack is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", "",
                                              "TIFF Files (*.tif *.tiff);;All Files (*)")
        if path:
            if not path.lower().endswith(('.tif', '.tiff')):
                path += '.tiff'
            self._save_to_path(path)
            self.current_file_path = path
            self.statusBar().showMessage(f"Saved: {path}")

    def _save_to_path(self, path):
        try:
            master_layer = {'Master': self.master_layer}
            individual_layers = {label: image for label, image in zip(self.current_labels, self.current_stack)}
            write_multilayer_tiff_from_images({**individual_layers, **master_layer}, path)
            self.statusBar().showMessage(f"Saved: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save file: {str(e)}")

    def set_view_master(self):
        self.view_mode = 'master'
        self.temp_view_individual = False
        self.display_current_view()
        self.statusBar().showMessage("View mode: Master")

    def set_view_individual(self):
        self.view_mode = 'individual'
        self.temp_view_individual = False
        self.display_current_view()
        self.statusBar().showMessage("View mode: Individual layers")

    def start_temp_view(self):
        if not self.temp_view_individual and self.view_mode == 'master':
            self.temp_view_individual = True
            self.display_current_view()
            self.statusBar().showMessage("Temporary view: Individual layer (hold X)")

    def end_temp_view(self):
        if self.temp_view_individual:
            self.temp_view_individual = False
            self.display_current_view()
            self.statusBar().showMessage("View mode: Master")

    def display_current_view(self):
        if self.temp_view_individual or self.view_mode == 'individual':
            self.display_current_layer()
        else:
            self.display_master_layer()

    def display_master_layer(self):
        if self.master_layer is not None:
            qimage = self.numpy_to_qimage(self.master_layer)
            self.image_viewer.set_image(qimage)
            self.update_thumbnails()

    def create_thumbnail(self, layer, size):
        if layer.ndim == 3 and layer.shape[-1] == 3:
            return self.create_rgb_thumbnail(layer)
        else:
            return self.create_grayscale_thumbnail(layer)

    def update_thumbnails(self):
        if not hasattr(self, 'master_layer') or self.master_layer is None:
            return
        thumb_size = UI_SIZES['thumbnail']
        master_thumb = self.create_thumbnail(self.master_layer, thumb_size)
        self.master_thumbnail_label.setPixmap(master_thumb)
        self.thumbnail_list.clear()
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
        return QPixmap.fromImage(qimg.scaled(*UI_SIZES['thumbnail'], Qt.KeepAspectRatio))

    def create_grayscale_thumbnail(self, layer):
        if layer.dtype == np.uint16:
            p2, p98 = np.percentile(layer, (2, 98))
            layer = np.clip(np.multiply(np.subtract(layer, p2), 255.0 / (p98 - p2)), 0, 255).astype(np.uint8)
        height, width = layer.shape
        qimg = QImage(layer.data, width, height, width, QImage.Format_Grayscale8)
        return QPixmap.fromImage(qimg.scaled(*UI_SIZES['thumbnail'], Qt.KeepAspectRatio))

    def change_layer(self, layer_idx):
        if 0 <= layer_idx < len(self.current_stack):
            view_state = self.image_viewer.get_view_state()
            self.current_layer = layer_idx
            self.display_current_view()
            self.image_viewer.set_view_state(view_state)
            self.thumbnail_list.setCurrentRow(layer_idx)
            self.thumbnail_list.setFocus()
            self.image_viewer.update_brush_cursor(self.brush_controller.brush_size)
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
        self.brush_controller.brush_size = slider_to_brush_size(slider_val)
        self.update_brush_preview()
        self.image_viewer.update_brush_cursor(self.brush_controller.brush_size)
        self.clear_brush_cache()

    def update_brush_hardness(self, hardness):
        self.brush_controller.brush_hardness = max(1, min(100, hardness))
        self.update_brush_preview()
        self.image_viewer.update_brush_cursor(self.brush_controller.brush_size)
        self.clear_brush_cache()

    def update_brush_opacity(self, opacity):
        self.brush_controller.brush_opacity = opacity
        self.update_brush_preview()
        self.image_viewer.update_brush_cursor(self.brush_controller.brush_size)

    def update_brush_preview(self):
        width, height = UI_SIZES['brush_preview']
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        preview_size = min(self.brush_controller.brush_size, width + 30, height + 30)
        center_x, center_y = width // 2, height // 2
        radius = preview_size // 2
        if self.cursor_style == 'preview':
            gradient = create_brush_gradient(
                center_x, center_y, radius,
                self.brush_controller.brush_hardness,
                inner_color=BRUSH_COLORS['inner'],
                outer_color=BRUSH_COLORS['gradient_end'],
                opacity=self.brush_controller.brush_opacity
            )
            painter.setBrush(QBrush(gradient))
            painter.setPen(QPen(BRUSH_COLORS['outer'], 1))
        elif self.cursor_style == 'outline':
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(BRUSH_COLORS['outer'], 1))
        else:
            painter.setBrush(QBrush(BRUSH_COLORS['cursor_inner']))
            painter.setPen(QPen(BRUSH_COLORS['pen'], 1))

        painter.drawEllipse(QPoint(center_x, center_y), radius, radius)

        if self.cursor_style == 'preview':
            painter.setPen(QPen(QColor(0, 0, 160)))
            painter.drawText(0, 10, f"Size: {int(self.brush_controller.brush_size)}px")
            painter.drawText(0, 25, f"Hardness: {self.brush_controller.brush_hardness}%")
            painter.drawText(0, 40, f"Opacity: {self.brush_controller.brush_opacity}%")

        painter.end()
        self.brush_preview.setPixmap(pixmap)

    def clear_brush_cache(self):
        self._brush_mask_cache.clear()

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
        source_layer = self.current_stack[self.current_layer]
        master_layer = self.master_layer
        destination_layer = self.master_layer
        self.mask_layer = self.blank_layer.copy()
        success = self.brush_controller.apply_brush_operation(master_layer, source_layer, destination_layer, self.mask_layer,
                                                              view_pos=view_pos, image_viewer=self.image_viewer)

    def begin_copy_brush_area(self, pos):
        if self.view_mode == 'master' and not self.temp_view_individual:
            self.save_undo_state()
            self.copy_brush_area_to_master(pos)
            self.display_current_view()
            self.mark_as_modified()

    def continue_copy_brush_area(self, pos):
        if self.view_mode == 'master' and not self.temp_view_individual:
            self.copy_brush_area_to_master(pos)
            self.needs_update = True
            if not self.update_timer.isActive():
                self.update_timer.start()             
        
    def save_undo_state(self):
        if self.master_layer is None:
            return
        undo_state = {
            'master': self.master_layer.copy()
        }
        if len(self.undo_stack) >= self.max_undo_steps:
            self.undo_stack.pop(0)
        self.undo_stack.append(undo_state)

    def undo_last_brush(self):
        print("try undo state")
        if self.master_layer is None or not self.undo_stack or len(self.undo_stack) == 0:
            return
        undo_state = self.undo_stack.pop()
        self.master_layer = undo_state['master']
        self.master_layer
        self.display_current_view()
        self.mark_as_modified()
        self.statusBar().showMessage("Undo applied", 2000)
        print("undo applied")
        
    def set_cursor_style(self, style):
        self.cursor_style = style
        if self.image_viewer.brush_cursor:
            self.image_viewer.update_brush_cursor(self.brush_controller.brush_size)
