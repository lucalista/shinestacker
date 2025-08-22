# pylint: disable=C0114, C0115, C0116, E0611, R0913, R0917, R0914, W0718
import traceback
import numpy as np
from PySide6.QtWidgets import QGraphicsPixmapItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QImage
from .layer_collection import LayerCollectionHandler


def brush_profile(r, hardness):
    h = 2.0 * hardness - 1.0
    if h >= 1.0:
        result = np.where(r < 1.0, 1.0, 0.0)
    elif h >= 0:
        k = 1.0 / (1.0 - hardness)
        result = 0.5 * (np.cos(np.pi * np.power(np.where(r < 1.0, r, 1.0), k)) + 1.0)
    elif h < 0:
        k = 1.0 / (1.0 + hardness)
        result = np.where(
            r < 1.0,
            0.5 * (1.0 - np.cos(np.pi * np.power(1.0 - np.where(r < 1.0, r, 1.0), k))), 0.0)
    else:
        result = np.zeros_like(r)
    return result


def create_brush_mask(size, hardness_percent, opacity_percent):
    radius = size / 2.0
    center = (size - 1) / 2.0
    h, o = hardness_percent / 100.0, opacity_percent / 100.0
    y, x = np.ogrid[:size, :size]
    r = np.sqrt((x - center)**2 + (y - center)**2) / radius
    mask = np.clip(brush_profile(r, h), 0.0, 1.0) * o
    return mask


class BrushPreviewItem(QGraphicsPixmapItem, LayerCollectionHandler):
    def __init__(self, layer_collection):
        QGraphicsPixmapItem.__init__(self)
        LayerCollectionHandler.__init__(self, layer_collection)
        self.setVisible(False)
        self.setZValue(500)
        self.setTransformationMode(Qt.SmoothTransformation)

    def get_layer_area(self, layer, x, y, w, h):
        if not isinstance(layer, np.ndarray):
            self.hide()
            return None
        height, width = layer.shape[:2]
        x_start, y_start = max(0, x), max(0, y)
        x_end, y_end = min(width, x + w), min(height, y + h)
        if x_end <= x_start or y_end <= y_start:
            self.hide()
            return None
        area = np.ascontiguousarray(layer[y_start:y_end, x_start:x_end])
        if area.ndim == 2:  # grayscale
            area = np.ascontiguousarray(np.stack([area] * 3, axis=-1))
        elif area.shape[2] == 4:  # RGBA
            area = np.ascontiguousarray(area[..., :3])  # RGB
        if area.dtype == np.uint8:
            return area.astype(np.float32) / 256.0
        if area.dtype == np.uint16:
            return area.astype(np.float32) / 65536.0
        raise RuntimeError("Bitmas is neither 8 bit nor 16, but of type " + area.dtype)

    def update(self, scene_pos, size):
        try:
            if self.layer_collection is None or self.number_of_layers() == 0 or size <= 0:
                self.hide()
                return
            radius = size // 2
            x = int(scene_pos.x() - radius + 0.5)
            y = int(scene_pos.y() - radius)
            w = h = size
            if not self.valid_current_layer_idx():
                self.hide()
                return
            layer_area = self.get_layer_area(self.current_layer(), x, y, w, h)
            master_area = self.get_layer_area(self.master_layer(), x, y, w, h)
            if layer_area is None or master_area is None:
                self.hide()
                return
            height, width = self.current_layer().shape[:2]
            full_mask = create_brush_mask(size=size, hardness_percent=self.brush.hardness,
                                          opacity_percent=self.brush.opacity)[:, :, np.newaxis]
            mask_x_start = max(0, -x) if x < 0 else 0
            mask_y_start = max(0, -y) if y < 0 else 0
            mask_x_end = size - (max(0, (x + w) - width)) if (x + w) > width else size
            mask_y_end = size - (max(0, (y + h) - height)) if (y + h) > height else size
            mask_area = full_mask[mask_y_start:mask_y_end, mask_x_start:mask_x_end]
            area = (layer_area * mask_area + master_area * (1 - mask_area)) * 255.0
            area = area.astype(np.uint8)
            qimage = QImage(area.data, area.shape[1], area.shape[0],
                            area.strides[0], QImage.Format_RGB888)
            mask = QPixmap(w, h)
            mask.fill(Qt.transparent)
            painter = QPainter(mask)
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.black)
            painter.drawEllipse(0, 0, w, h)
            painter.end()
            pixmap = QPixmap.fromImage(qimage)
            final_pixmap = QPixmap(w, h)
            final_pixmap.fill(Qt.transparent)
            painter = QPainter(final_pixmap)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            painter.drawPixmap(0, 0, mask)
            painter.end()
            self.setPixmap(final_pixmap)
            x_start, y_start = max(0, x), max(0, y)
            self.setPos(x_start, y_start)
            self.show()
        except Exception:
            traceback.print_exc()
            self.hide()
