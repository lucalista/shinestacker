# pylint: disable=R0913, R0917, R0914, W0718, R0915
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
        self.brush = None

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
        if self.brush is None:
            return
        try:
            if self.layer_collection is None or self.number_of_layers() == 0 or size <= 0:
                self.hide()
                return
            radius = size // 2
            x_center = int(scene_pos.x() + 0.5)
            y_center = int(scene_pos.y() + 0.5)
            x = x_center - radius
            y = y_center - radius
            w = h = size
            if not self.valid_current_layer_idx():
                self.hide()
                return
            height, width = self.current_layer().shape[:2]
            visible_x = max(0, x)
            visible_y = max(0, y)
            visible_w = min(width, x + w) - visible_x
            visible_h = min(height, y + h) - visible_y
            if visible_w <= 0 or visible_h <= 0:
                self.hide()
                return
            layer_area = self.get_layer_area(
                self.current_layer(), visible_x, visible_y, visible_w, visible_h)
            master_area = self.get_layer_area(
                self.master_layer(), visible_x, visible_y, visible_w, visible_h)
            if layer_area is None or master_area is None:
                self.hide()
                return
            full_mask = create_brush_mask(size=size, hardness_percent=self.brush.hardness,
                                          opacity_percent=self.brush.opacity)[:, :, np.newaxis]
            mask_x_start = max(0, -x)
            mask_y_start = max(0, -y)
            mask_x_end = mask_x_start + visible_w
            mask_y_end = mask_y_start + visible_h
            mask_area = full_mask[mask_y_start:mask_y_end, mask_x_start:mask_x_end]
            if self.brush.luminosity != 0:
                lumi_scale = 1.0 + float(self.brush.luminosity) / 100.0
                area = np.clip((layer_area * mask_area * lumi_scale +
                                master_area * (1 - mask_area)) * 255.0,
                               0, 255)
            else:
                area = np.clip((layer_area * mask_area +
                                master_area * (1 - mask_area)) * 255.0,
                               0, 255)
            area = area.astype(np.uint8)
            qimage = QImage(area.data, area.shape[1], area.shape[0],
                            area.strides[0], QImage.Format_RGB888)
            mask = QPixmap(visible_w, visible_h)
            mask.fill(Qt.transparent)
            painter = QPainter(mask)
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.black)
            center_x_in_visible = x_center - visible_x
            center_y_in_visible = y_center - visible_y
            painter.drawEllipse(
                center_x_in_visible - radius, center_y_in_visible - radius, size, size)
            painter.end()
            pixmap = QPixmap.fromImage(qimage)
            final_pixmap = QPixmap(visible_w, visible_h)
            final_pixmap.fill(Qt.transparent)
            painter = QPainter(final_pixmap)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            painter.drawPixmap(0, 0, mask)
            painter.end()
            self.setPixmap(final_pixmap)
            self.setPos(visible_x, visible_y)
            self.show()
        except Exception:
            traceback.print_exc()
            self.hide()
