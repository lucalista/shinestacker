# pylint: disable=E0611, R0902
from PySide6.QtCore import QObject, QRectF, Signal
from PySide6.QtGui import QPixmap


class ImageViewStatus(QObject):
    set_zoom_factor_requested = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap_master = QPixmap()
        self.pixmap_current = QPixmap()
        self.zoom_factor = 1.0
        self.min_scale = 0.0
        self.max_scale = 0.0
        self.h_scroll = 0
        self.v_scroll = 0
        self.scene_rect = QRectF()

    def empty(self):
        return self.pixmap_master.isNull()

    def set_master_image(self, qimage):
        pixmap = QPixmap.fromImage(qimage)
        self.pixmap_master = pixmap
        if not self.empty():
            self.scene_rect = QRectF(pixmap.rect())

    def set_current_image(self, qimage):
        pixmap = QPixmap.fromImage(qimage)
        self.pixmap_current = pixmap

    def clear(self):
        self.pixmap_master = QPixmap()
        self.pixmap_current = QPixmap()
        self.zoom_factor = 1.0
        self.min_scale = 0.0
        self.max_scale = 0.0
        self.h_scroll = 0
        self.v_scroll = 0
        self.scene_rect = QRectF()

    def get_state(self):
        return {
            'zoom': self.zoom_factor,
            'h_scroll': self.h_scroll,
            'v_scroll': self.v_scroll
        }

    def set_zoom_factor(self, zoom_factor):
        self.zoom_factor = zoom_factor
        self.set_zoom_factor_requested.emit(zoom_factor)

    def set_min_scale(self, min_scale):
        self.min_scale = min_scale

    def set_max_scale(self, min_scale):
        self.max_scale = min_scale

    def set_scroll(self, h_scroll, v_scroll):
        self.h_scroll = h_scroll
        self.v_scroll = v_scroll
