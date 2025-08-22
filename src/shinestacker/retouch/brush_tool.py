# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0913, R0917, R0914
import numpy as np
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtCore import Qt, QPoint
from .brush_gradient import create_default_brush_gradient
from .. config.gui_constants import gui_constants
from .. config.constants import constants
from .brush_preview import create_brush_mask


class BrushTool:
    def __init__(self):
        self.brush = None
        self.brush_preview = None
        self.image_viewer = None
        self.size_slider = None
        self.hardness_slider = None
        self.opacity_slider = None
        self.flow_slider = None
        self._brush_mask_cache = {}
        self.brush_text = None

    def setup_ui(self, brush, brush_preview, image_viewer, size_slider, hardness_slider,
                 opacity_slider, flow_slider):
        self.brush = brush
        self.brush_preview = brush_preview
        self.brush_text = QLabel(brush_preview.parent())
        self.brush_text.setStyleSheet("color: navy; background: transparent;")
        self.brush_text.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.brush_text.raise_()
        self.image_viewer = image_viewer
        self.size_slider = size_slider
        self.hardness_slider = hardness_slider
        self.opacity_slider = opacity_slider
        self.flow_slider = flow_slider
        self.size_slider.valueChanged.connect(self.update_brush_size)
        self.hardness_slider.valueChanged.connect(self.update_brush_hardness)
        self.opacity_slider.valueChanged.connect(self.update_brush_opacity)
        self.flow_slider.valueChanged.connect(self.update_brush_flow)
        self.update_brush_size(self.size_slider.value())
        self.update_brush_hardness(self.hardness_slider.value())
        self.update_brush_opacity(self.opacity_slider.value())
        self.update_brush_flow(self.flow_slider.value())

    def update_brush_size(self, slider_val):

        def slider_to_brush_size(slider_val):
            normalized = slider_val / gui_constants.BRUSH_SIZE_SLIDER_MAX
            size = gui_constants.BRUSH_SIZES['min'] + \
                gui_constants.BRUSH_SIZES['max'] * (normalized ** gui_constants.BRUSH_GAMMA)
            return max(gui_constants.BRUSH_SIZES['min'],
                       min(gui_constants.BRUSH_SIZES['max'], size))

        self.brush.size = slider_to_brush_size(slider_val)
        self.update_brush_thumb()

    def increase_brush_size(self, amount=5):
        val = min(self.size_slider.value() + amount, self.size_slider.maximum())
        self.size_slider.setValue(val)
        self.update_brush_size(val)

    def decrease_brush_size(self, amount=5):
        val = max(self.size_slider.value() - amount, self.size_slider.minimum())
        self.size_slider.setValue(val)
        self.update_brush_size(val)

    def increase_brush_hardness(self, amount=2):
        val = min(self.hardness_slider.value() + amount, self.hardness_slider.maximum())
        self.hardness_slider.setValue(val)
        self.update_brush_hardness(val)

    def decrease_brush_hardness(self, amount=2):
        val = max(self.hardness_slider.value() - amount, self.hardness_slider.minimum())
        self.hardness_slider.setValue(val)
        self.update_brush_hardness(val)

    def update_brush_hardness(self, hardness):
        self.brush.hardness = hardness
        self.update_brush_thumb()

    def update_brush_opacity(self, opacity):
        self.brush.opacity = opacity
        self.update_brush_thumb()

    def update_brush_flow(self, flow):
        self.brush.flow = flow
        self.update_brush_thumb()

    def update_brush_thumb(self):
        width, height = gui_constants.UI_SIZES['brush_preview']
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        preview_size = min(self.brush.size, width + 30, height + 30)
        center_x, center_y = width // 2, height // 2
        radius = preview_size // 2
        if self.image_viewer.cursor_style == 'preview':
            gradient = create_default_brush_gradient(center_x, center_y, radius, self.brush)
            painter.setBrush(QBrush(gradient))
            painter.setPen(
                QPen(QColor(*gui_constants.BRUSH_COLORS['outer']),
                     gui_constants.BRUSH_PREVIEW_LINE_WIDTH))
        elif self.image_viewer.cursor_style == 'outline':
            painter.setBrush(Qt.NoBrush)
            painter.setPen(
                QPen(QColor(*gui_constants.BRUSH_COLORS['outer']),
                     gui_constants.BRUSH_PREVIEW_LINE_WIDTH))
        else:
            painter.setBrush(QBrush(QColor(*gui_constants.BRUSH_COLORS['cursor_inner'])))
            painter.setPen(
                QPen(QColor(*gui_constants.BRUSH_COLORS['pen']),
                     gui_constants.BRUSH_PREVIEW_LINE_WIDTH))
        painter.drawEllipse(QPoint(center_x, center_y), radius, radius)
        if self.image_viewer.cursor_style == 'preview':
            painter.setPen(QPen(QColor(0, 0, 160)))
            font = QApplication.font()
            painter.setFont(font)
            font.setHintingPreference(QFont.PreferFullHinting)
            painter.setFont(font)
            self.brush_text.setText(
                f"Size: {int(self.brush.size)}px\n"
                f"Hardness: {self.brush.hardness}%\n"
                f"Opacity: {self.brush.opacity}%\n"
                f"Flow: {self.brush.flow}%"
            )
            self.brush_text.adjustSize()
            self.brush_text.move(10, self.brush_preview.height() // 2 + 125)
            self.brush_text.show()
        else:
            self.brush_text.hide()
        painter.end()
        self.brush_preview.setPixmap(pixmap)
        self.image_viewer.update_brush_cursor()

    def apply_brush_operation(self, master_layer, source_layer, dest_layer, mask_layer,
                              view_pos):
        if master_layer is None or source_layer is None:
            return False
        if dest_layer is None:
            dest_layer = master_layer
        scene_pos = self.image_viewer.mapToScene(view_pos)
        x_center = int(round(scene_pos.x()))
        y_center = int(round(scene_pos.y()))
        radius = int(round(self.brush.size // 2))
        h, w = master_layer.shape[:2]
        x_start, x_end = max(0, x_center - radius), min(w, x_center + radius + 1)
        y_start, y_end = max(0, y_center - radius), min(h, y_center + radius + 1)
        if x_start >= x_end or y_start >= y_end:
            return 0, 0, 0, 0
        mask = self.get_brush_mask(radius)
        if mask is None:
            return 0, 0, 0, 0
        master_area = master_layer[y_start:y_end, x_start:x_end]
        source_area = source_layer[y_start:y_end, x_start:x_end]
        dest_area = dest_layer[y_start:y_end, x_start:x_end]
        mask_layer_area = mask_layer[y_start:y_end, x_start:x_end]
        mask_area = mask[y_start - (y_center - radius):y_end - (y_center - radius),
                         x_start - (x_center - radius):x_end - (x_center - radius)]
        mask_layer_area[:] = np.clip(
            mask_layer_area + mask_area * self.brush.flow / 100.0, 0.0,
            1.0)
        self.apply_mask(master_area, source_area, mask_layer_area, dest_area)
        return x_start, y_start, x_end, y_end

    def get_brush_mask(self, radius):
        mask_key = (radius, self.brush.hardness)
        if mask_key not in self._brush_mask_cache:
            full_mask = create_brush_mask(size=radius * 2 + 1, hardness_percent=self.brush.hardness,
                                          opacity_percent=self.brush.opacity)
            self._brush_mask_cache[mask_key] = full_mask
        return self._brush_mask_cache[mask_key]

    def apply_mask(self, master_area, source_area, mask_area, dest_area):
        opacity_factor = float(self.brush.opacity) / 100.0
        effective_mask = np.clip(mask_area * opacity_factor, 0, 1)
        dtype = master_area.dtype
        max_px_value = constants.MAX_UINT16 if dtype == np.uint16 else constants.MAX_UINT8
        if master_area.ndim == 3:
            dest_area[:] = np.clip(
                master_area * (1 - effective_mask[..., np.newaxis]) +
                source_area * effective_mask[..., np.newaxis], 0, max_px_value).astype(dtype)
        else:
            dest_area[:] = np.clip(
                master_area * (1 - effective_mask) + source_area * effective_mask, 0,
                max_px_value).astype(dtype)
