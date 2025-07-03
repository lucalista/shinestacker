import numpy as np
from PySide6.QtWidgets import QGraphicsPixmapItem
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPixmap, QPainter, QImage


def brush_profile(r, hardness):
    if hardness >= 1.0:
        result = np.where(r < 1.0, 1.0, 0.0)
    else:
        k = 1.0 / (1.0 - hardness)
        result = np.where(r < 1.0, 0.5 * (np.cos(np.pi * np.power(r, k)) + 1.0), 0.0)
    return result


def create_brush_mask(size, hardness_percent, opacity_percent):
    radius = size / 2.0
    center = (size - 1) / 2.0
    h, o = hardness_percent / 100.0, opacity_percent / 100.0
    y, x = np.ogrid[:size, :size]
    r = np.sqrt((x - center)**2 + (y - center)**2) / radius
    mask = np.clip(brush_profile(r, h), 0.0, 1.0) * o
    return mask


class BrushPreviewItem(QGraphicsPixmapItem):
    def __init__(self):
        super().__init__()
        self.setVisible(False)
        self.setZValue(500)
        self.setTransformationMode(Qt.SmoothTransformation)

    def get_layer_area(self, layer, x, y, w, h):
        if not isinstance(layer, np.ndarray):
            self.setVisible(False)
            return None
        height, width = layer.shape[:2]
        x_start, y_start = max(0, x), max(0, y)
        x_end, y_end = min(width, x + w), min(height, y + h)
        if x_end <= x_start or y_end <= y_start:
            self.setVisible(False)
            return None
        area = np.ascontiguousarray(layer[y_start:y_end, x_start:x_end])
        if area.ndim == 2:  # grayscale
            area = np.ascontiguousarray(np.stack([area] * 3, axis=-1))
        elif area.shape[2] == 4:  # RGBA
            area = np.ascontiguousarray(area[..., :3])  # RGB
        if area.dtype == np.uint8:
            return area.astype(np.float32) / 256.0
        elif area.dtype == np.uint16:
            return area.astype(np.float32) / 65536.0
        else:
            raise Exception("Bitmas is neither 8 bit nor 16, but of type " + area.dtype)

    def update_preview(self, editor, pos, size):
        try:
            if editor.current_stack is None or not hasattr(editor, 'image_viewer') or size <= 0:
                self.setVisible(False)
                return
            radius = size // 2
            if isinstance(pos, QPointF):
                scene_pos = pos
            else:
                cursor_pos = editor.image_viewer.mapFromGlobal(pos)
                scene_pos = editor.image_viewer.mapToScene(cursor_pos)
            x = int(scene_pos.x() - radius + 0.5)
            y = int(scene_pos.y() - radius)
            w = h = size
            if editor.current_layer < 0 or editor.current_layer >= len(editor.current_stack):
                self.setVisible(False)
                return
            layer_area = self.get_layer_area(editor.current_stack[editor.current_layer], x, y, w, h)
            master_area = self.get_layer_area(editor.master_layer, x, y, w, h)
            if layer_area is None or master_area is None:
                self.setVisible(False)
                return
            height, width = editor.current_stack[editor.current_layer].shape[:2]
            full_mask = create_brush_mask(size=size, hardness_percent=editor.brush_controller.brush_hardness,
                                          opacity_percent=editor.brush_controller.brush_opacity)[:, :, np.newaxis]
            mask_x_start = max(0, -x) if x < 0 else 0
            mask_y_start = max(0, -y) if y < 0 else 0
            mask_x_end = size - (max(0, (x + w) - width)) if (x + w) > width else size
            mask_y_end = size - (max(0, (y + h) - height)) if (y + h) > height else size
            mask_area = full_mask[mask_y_start:mask_y_end, mask_x_start:mask_x_end]
            area = (layer_area * mask_area + master_area * (1 - mask_area)) * 255.0
            area = area.astype(np.uint8)
            qimage = QImage(area.data, area.shape[1], area.shape[0], area.strides[0], QImage.Format_RGB888)
            mask = QPixmap(w, h)
            mask.fill(Qt.transparent)
            painter = QPainter(mask)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.black)
            painter.drawEllipse(0, 0, w, h)
            painter.end()

            pixmap = QPixmap.fromImage(qimage)
            final_pixmap = QPixmap(w, h)
            final_pixmap.fill(Qt.transparent)
            painter = QPainter(final_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            painter.drawPixmap(0, 0, mask)
            painter.end()

            self.setPixmap(final_pixmap)
            x_start, y_start = max(0, x), max(0, y)
            self.setPos(x_start, y_start)
            self.setVisible(True)
        except Exception as e:
            print(f"Preview error: {str(e)}")
            import traceback
            traceback.print_exc()
            self.setVisible(False)
