from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QCursor, QShortcut, QKeySequence, QRadialGradient
from PySide6.QtCore import Qt, QRectF, QTime
from gui.brush_preview import BrushPreviewItem

MIN_ZOOMED_IMG_WIDTH = 400
MAX_ZOOMED_IMG_PX_SIZE = 50

BRUSH_COLORS = {
    'outer': QColor(255, 0, 0, 200),
    'inner': QColor(255, 0, 0, 150),
    'gradient_end': QColor(255, 0, 0, 0),
    'pen': QColor(255, 0, 0, 150),
    'preview': QColor(255, 180, 180),
    'cursor_inner': QColor(255, 0, 0, 120),
    'preview_inner': QColor(255, 255, 255, 150)
}

MIN_MOUSE_STEP_BRUSH_FRACTION = 0.3
PAINT_REFRESH_TIMER = 20  # milliseconds


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


class ImageViewer(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_editor = None
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        self.zoom_factor = 1.0
        self.min_scale = 0.0
        self.max_scale = 0.0
        self.last_mouse_pos = None
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.brush_cursor = None
        self.setMouseTracking(True)
        self.space_pressed = False
        self.setDragMode(QGraphicsView.NoDrag)
        self.setCursor(Qt.BlankCursor)
        self.scrolling = False
        self.dragging = False
        self.last_update_time = QTime.currentTime()
        self.pending_update = False
        self.brush_preview = BrushPreviewItem()
        self.scene.addItem(self.brush_preview)

    def set_image(self, qimage):
        pixmap = QPixmap.fromImage(qimage)
        self.pixmap_item.setPixmap(pixmap)
        self.setSceneRect(QRectF(pixmap.rect()))
        img_width = pixmap.width()
        self.min_scale = MIN_ZOOMED_IMG_WIDTH / img_width
        self.max_scale = MAX_ZOOMED_IMG_PX_SIZE
        if self.zoom_factor == 1.0:
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
            self.zoom_factor = self.get_current_scale()
            self.zoom_factor = max(self.min_scale, min(self.max_scale, self.zoom_factor))
            self.resetTransform()
            self.scale(self.zoom_factor, self.zoom_factor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not self.scrolling:
            self.space_pressed = True
            self.setCursor(Qt.OpenHandCursor)
            if self.brush_cursor:
                self.brush_cursor.hide()
        elif event.key() == Qt.Key_X:
            self.image_editor.start_temp_view()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.space_pressed = False
            if not self.scrolling:
                self.setCursor(Qt.BlankCursor)
                if self.brush_cursor:
                    self.brush_cursor.show()
        elif event.key() == Qt.Key_X:
            self.image_editor.end_temp_view()
            return
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.space_pressed:
                self.scrolling = True
                self.last_mouse_pos = event.position()
                self.setCursor(Qt.ClosedHandCursor)
                if self.brush_cursor:
                    self.brush_cursor.hide()
            else:
                if self.image_editor.view_mode == 'master' and not self.image_editor.temp_view_individual:
                    self.image_editor.copy_brush_area_to_master(event.position().toPoint(), continuous=False)
                    self.dragging = True
                if self.brush_cursor:
                    self.brush_cursor.show()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not hasattr(self, 'last_brush_pos'):
            self.last_brush_pos = event.pos()
        brush_size = self.image_editor.brush_controller.brush_size
        self.update_brush_cursor(brush_size)
        if self.dragging and self.image_editor.view_mode == 'master' and not self.image_editor.temp_view_individual and event.buttons() & Qt.LeftButton:
            current_time = QTime.currentTime()
            min_step = brush_size * MIN_MOUSE_STEP_BRUSH_FRACTION
            distance = (event.pos() - self.last_brush_pos).manhattanLength()
            if (self.last_update_time.msecsTo(current_time) >= PAINT_REFRESH_TIMER and  # noqa
                distance >= min_step) or not self.pending_update:  # noqa
                self.image_editor.copy_brush_area_to_master(event.position().toPoint(), continuous=True)
                self.last_update_time = current_time
                self.pending_update = False
            else:
                self.pending_update = True
        if self.scrolling and event.buttons() & Qt.LeftButton:
            delta = event.position() - self.last_mouse_pos
            self.last_mouse_pos = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.scrolling:
                self.scrolling = False
                if self.space_pressed:
                    self.setCursor(Qt.OpenHandCursor)
                else:
                    self.setCursor(Qt.BlankCursor)
                    if self.brush_cursor:
                        self.brush_cursor.show()
                self.last_mouse_pos = None
            elif hasattr(self, 'dragging') and self.dragging:
                self.dragging = False
                if self.image_editor.update_timer.isActive():
                    self.image_editor.update_timer.stop()
                    self.image_editor.display_current_view()
                    self.image_editor.mark_as_modified()
                    self.image_editor.save_undo_state()
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        zoom_in_factor = 1.10
        zoom_out_factor = 1 / zoom_in_factor
        current_scale = self.get_current_scale()
        if event.angleDelta().y() > 0:  # Zoom in
            new_scale = current_scale * zoom_in_factor
            if new_scale <= self.max_scale:
                self.scale(zoom_in_factor, zoom_in_factor)
                self.zoom_factor = new_scale
        else:  # Zoom out
            new_scale = current_scale * zoom_out_factor
            if new_scale >= self.min_scale:
                self.scale(zoom_out_factor, zoom_out_factor)
                self.zoom_factor = new_scale

        self.update_brush_cursor(self.image_editor.brush_controller.brush_size)

    def setup_brush_cursor(self):
        pen = QPen(BRUSH_COLORS['pen'], 1)
        brush = QBrush(BRUSH_COLORS['cursor_inner'])
        self.brush_cursor = self.scene.addEllipse(0, 0,
                                                  self.image_editor.brush_controller.brush_size,
                                                  self.image_editor.brush_controller.brush_size,
                                                  pen, brush)
        self.brush_cursor.setZValue(1000)
        self.brush_cursor.hide()

    def update_brush_cursor(self, size):
        if not self.brush_cursor or not self.isVisible():
            return
        mouse_pos = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(mouse_pos):
            self.brush_cursor.hide()
            return
        scene_pos = self.mapToScene(mouse_pos)
        center_x = scene_pos.x()
        center_y = scene_pos.y()
        radius = size / 2
        self.brush_cursor.setRect(center_x - radius, center_y - radius, size, size)
        if self.image_editor.cursor_style == 'preview':
            self._setup_outline_style()
            self.brush_cursor.hide()
            self.brush_preview.update_preview(self.image_editor, QCursor.pos(), int(size))
        else:
            self.brush_preview.setVisible(False)
            if self.image_editor.cursor_style == 'outline':
                self._setup_outline_style()
            else:
                self._setup_simple_brush_style(center_x, center_y, radius)
        if not self.brush_cursor.isVisible():
            self.brush_cursor.show()

    def _setup_outline_style(self):
        self.brush_cursor.setPen(QPen(BRUSH_COLORS['pen'], 1))
        self.brush_cursor.setBrush(Qt.NoBrush)

    def _setup_simple_brush_style(self, center_x, center_y, radius):
        gradient = create_brush_gradient(
            center_x, center_y, radius,
            self.image_editor.brush_controller.brush_hardness,
            inner_color=BRUSH_COLORS['inner'],
            outer_color=BRUSH_COLORS['gradient_end'],
            opacity=self.image_editor.brush_controller.brush_opacity
        )
        self.brush_cursor.setPen(QPen(BRUSH_COLORS['pen'], 1))
        self.brush_cursor.setBrush(QBrush(gradient))

    def enterEvent(self, event):
        self.setCursor(Qt.BlankCursor)
        if self.brush_cursor:
            self.brush_cursor.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.brush_cursor:
            self.brush_cursor.hide()
        super().leaveEvent(event)

    def setup_shortcuts(self):
        prev_layer = QShortcut(QKeySequence(Qt.Key_Up), self, context=Qt.ApplicationShortcut)
        prev_layer.activated.connect(self.prev_layer)
        next_layer = QShortcut(QKeySequence(Qt.Key_Down), self, context=Qt.ApplicationShortcut)
        next_layer.activated.connect(self.next_layer)

    def zoom_in(self):
        current_scale = self.get_current_scale()
        new_scale = current_scale * 1.25
        if new_scale <= self.max_scale:
            self.scale(1.25, 1.25)
            self.zoom_factor = new_scale

    def zoom_out(self):
        current_scale = self.get_current_scale()
        new_scale = current_scale * 0.8
        if new_scale >= self.min_scale:
            self.scale(0.8, 0.8)
            self.zoom_factor = new_scale

    def reset_zoom(self):
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        self.zoom_factor = self.get_current_scale()
        self.zoom_factor = max(self.min_scale, min(self.max_scale, self.zoom_factor))
        self.resetTransform()
        self.scale(self.zoom_factor, self.zoom_factor)

    def actual_size(self):
        self.zoom_factor = max(self.min_scale, min(self.max_scale, 1.0))
        self.resetTransform()
        self.scale(self.zoom_factor, self.zoom_factor)

    def get_current_scale(self):
        return self.transform().m11()

    def get_view_state(self):
        return {
            'zoom': self.zoom_factor,
            'h_scroll': self.horizontalScrollBar().value(),
            'v_scroll': self.verticalScrollBar().value()
        }

    def set_view_state(self, state):
        if state:
            self.resetTransform()
            self.scale(state['zoom'], state['zoom'])
            self.horizontalScrollBar().setValue(state['h_scroll'])
            self.verticalScrollBar().setValue(state['v_scroll'])
            self.zoom_factor = state['zoom']
