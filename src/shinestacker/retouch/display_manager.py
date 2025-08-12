import numpy as np
from PySide6.QtWidgets import QWidget, QListWidgetItem, QVBoxLayout, QLabel
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QTimer, QSize, Signal
from .. config.gui_constants import gui_constants


class ClickableLabel(QLabel):
    doubleClicked = Signal()

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMouseTracking(True)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class DisplayManager:
    def __init__(self, layer_collection, image_viewer, master_thumbnail_label, thumbnail_list):
        self.layer_collection = layer_collection
        self.image_viewer = image_viewer
        self.master_thumbnail_label = master_thumbnail_label
        self.thumbnail_list = thumbnail_list
        self.view_mode = 'master'
        self.temp_view_individual = False
        self.needs_update = False
        self.update_timer = QTimer()
        self.update_timer.setInterval(gui_constants.PAINT_REFRESH_TIMER)
        self.update_timer.timeout.connect(self.process_pending_updates)

    def process_pending_updates(self):
        if self.needs_update:
            self.display_master_layer()
            self.needs_update = False

    def display_master_layer(self):
        if self.layer_collection.master_layer is None:
            self.image_viewer.clear_image()
        else:
            qimage = self.numpy_to_qimage(self.layer_collection.master_layer)
            self.image_viewer.set_image(qimage)

    def display_current_layer(self):
        if self.layer_collection.layer_stack is None:
            return
        layer = self.layer_collection.current_layer()
        qimage = self.numpy_to_qimage(layer)
        self.image_viewer.set_image(qimage)

    def display_current_view(self):
        if self.temp_view_individual or self.view_mode == 'individual':
            self.display_current_layer()
        else:
            self.display_master_layer()

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

    def set_view_master(self):
        if self.layer_collection.master_layer is None:
            return
        self.view_mode = 'master'
        self.temp_view_individual = False
        self.display_master_layer()
        self.statusBar().showMessage("View mode: Master")

    def set_view_individual(self):
        if self.layer_collection.master_layer is None:
            return
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

    def allow_cursor_preview(self):
        return self.view_mode == 'master' and not self.temp_view_individual

    def _add_thumbnail_item(self, thumbnail, label, i, is_current):
        item_widget = QWidget()
        layout = QVBoxLayout(item_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        thumbnail_label = QLabel()
        thumbnail_label.setPixmap(thumbnail)
        thumbnail_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(thumbnail_label)

        label_widget = ClickableLabel(label)
        label_widget.setAlignment(Qt.AlignCenter)
        label_widget.doubleClicked.connect(lambda: self._rename_label(label_widget, label, i))
        layout.addWidget(label_widget)

        item = QListWidgetItem()
        item.setSizeHint(QSize(gui_constants.IMG_WIDTH, gui_constants.IMG_HEIGHT))
        self.thumbnail_list.addItem(item)
        self.thumbnail_list.setItemWidget(item, item_widget)

        if is_current:
            self.thumbnail_list.setCurrentItem(item)
