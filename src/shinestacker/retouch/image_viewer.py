import math
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QCursor, QShortcut, QKeySequence
from PySide6.QtCore import Qt, QRectF, QTime, QPoint, QPointF, Signal
from .. config.gui_constants import gui_constants
from .brush_preview import BrushPreviewItem
from .brush_gradient import create_brush_gradient


class ImageViewer(QGraphicsView):
    temp_view_requested = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_editor = None
        self.brush = None
        self.cursor_style = gui_constants.DEFAULT_CURSOR_STYLE
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        self.pixmap_item.setPixmap(QPixmap())
        self.scene.setBackgroundBrush(QBrush(QColor(120, 120, 120)))
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
        self.control_pressed = False
        self.setDragMode(QGraphicsView.NoDrag)
        self.scrolling = False
        self.dragging = False
        self.last_update_time = QTime.currentTime()
        self.brush_preview = BrushPreviewItem()
        self.scene.addItem(self.brush_preview)
        self.empty = True

    def set_image(self, qimage):
        pixmap = QPixmap.fromImage(qimage)
        self.pixmap_item.setPixmap(pixmap)
        self.setSceneRect(QRectF(pixmap.rect()))
        img_width = pixmap.width()
        self.min_scale = gui_constants.MIN_ZOOMED_IMG_WIDTH / img_width
        self.max_scale = gui_constants.MAX_ZOOMED_IMG_PX_SIZE
        if self.zoom_factor == 1.0:
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
            self.zoom_factor = self.get_current_scale()
            self.zoom_factor = max(self.min_scale, min(self.max_scale, self.zoom_factor))
            self.resetTransform()
            self.scale(self.zoom_factor, self.zoom_factor)
        self.empty = False
        self.setFocus()
        self.activateWindow()
        self.brush_preview.layer_collection = self.image_editor.layer_collection
        self.brush_preview.brush = self.brush

    def clear_image(self):
        self.scene.clear()
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        self.zoom_factor = 1.0
        self.setup_brush_cursor()
        self.brush_preview = BrushPreviewItem()
        self.scene.addItem(self.brush_preview)
        self.setCursor(Qt.ArrowCursor)
        self.brush_cursor.hide()
        self.empty = True

    def keyPressEvent(self, event):
        if self.empty:
            return
        if event.key() == Qt.Key_Space and not self.scrolling:
            self.space_pressed = True
            self.setCursor(Qt.OpenHandCursor)
            if self.brush_cursor:
                self.brush_cursor.hide()
        elif event.key() == Qt.Key_X:
            self.temp_view_requested.emit(True)
            self.update_brush_cursor()
            return
        if event.key() == Qt.Key_Control and not self.scrolling:
            self.control_pressed = True
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.empty:
            return
        self.update_brush_cursor()
        if event.key() == Qt.Key_Space:
            self.space_pressed = False
            if not self.scrolling:
                self.setCursor(Qt.BlankCursor)
                if self.brush_cursor:
                    self.brush_cursor.show()
        elif event.key() == Qt.Key_X:
            self.temp_view_requested.emit(False)
            return
        if event.key() == Qt.Key_Control:
            self.control_pressed = False
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        if self.empty:
            return
        if event.button() == Qt.LeftButton and self.image_editor.layer_collection.master_layer is not None:
            if self.space_pressed:
                self.scrolling = True
                self.last_mouse_pos = event.position()
                self.setCursor(Qt.ClosedHandCursor)
                if self.brush_cursor:
                    self.brush_cursor.hide()
            else:
                self.last_brush_pos = event.position()
                self.image_editor.begin_copy_brush_area(event.position().toPoint())
                self.dragging = True
                if self.brush_cursor:
                    self.brush_cursor.show()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.empty:
            return
        position = event.position()
        brush_size = self.brush.size
        if not self.space_pressed:
            self.update_brush_cursor()
        if self.dragging and event.buttons() & Qt.LeftButton:
            current_time = QTime.currentTime()
            if self.last_update_time.msecsTo(current_time) >= gui_constants.PAINT_REFRESH_TIMER:
                min_step = brush_size * gui_constants.MIN_MOUSE_STEP_BRUSH_FRACTION * self.zoom_factor
                x, y = position.x(), position.y()
                xp, yp = self.last_brush_pos.x(), self.last_brush_pos.y()
                distance = math.sqrt((x - xp)**2 + (y - yp)**2)
                n_steps = int(float(distance) / min_step)
                if n_steps > 0:
                    delta_x = (position.x() - self.last_brush_pos.x()) / n_steps
                    delta_y = (position.y() - self.last_brush_pos.y()) / n_steps
                    for i in range(0, n_steps + 1):
                        pos = QPoint(self.last_brush_pos.x() + i * delta_x,
                                     self.last_brush_pos.y() + i * delta_y)
                        self.image_editor.continue_copy_brush_area(pos)
                    self.last_brush_pos = position
                self.last_update_time = current_time
        if self.scrolling and event.buttons() & Qt.LeftButton:
            if self.space_pressed:
                self.setCursor(Qt.ClosedHandCursor)
                if self.brush_cursor:
                    self.brush_cursor.hide()
            delta = position - self.last_mouse_pos
            self.last_mouse_pos = position
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.empty:
            return
        if self.space_pressed:
            self.setCursor(Qt.OpenHandCursor)
            if self.brush_cursor:
                self.brush_cursor.hide()
        else:
            self.setCursor(Qt.BlankCursor)
            if self.brush_cursor:
                self.brush_cursor.show()
        if event.button() == Qt.LeftButton:
            if self.scrolling:
                self.scrolling = False
                self.last_mouse_pos = None
            elif hasattr(self, 'dragging') and self.dragging:
                self.dragging = False
                self.image_editor.end_copy_brush_area()
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if self.empty:
            return
        if self.control_pressed:
            if event.angleDelta().y() > 0:
                self.image_editor.decrease_brush_size()
            else:
                self.image_editor.increase_brush_size()
        else:
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
        self.update_brush_cursor()

    def setup_brush_cursor(self):
        self.setCursor(Qt.BlankCursor)
        pen = QPen(QColor(*gui_constants.BRUSH_COLORS['pen']), 1)
        brush = QBrush(QColor(*gui_constants.BRUSH_COLORS['cursor_inner']))
        self.brush_cursor = self.scene.addEllipse(0, 0, self.brush.size, self.brush.size, pen, brush)
        self.brush_cursor.setZValue(1000)
        self.brush_cursor.hide()

    def update_brush_cursor(self):
        if self.empty:
            return
        if not self.brush_cursor or not self.isVisible():
            return
        size = self.brush.size
        mouse_pos = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(mouse_pos):
            self.brush_cursor.hide()
            return
        scene_pos = self.mapToScene(mouse_pos)
        center_x = scene_pos.x()
        center_y = scene_pos.y()
        radius = size / 2
        self.brush_cursor.setRect(center_x - radius, center_y - radius, size, size)
        allow_cursor_preview = self.image_editor.display_manager.allow_cursor_preview()
        if self.cursor_style == 'preview' and allow_cursor_preview:
            self._setup_outline_style()
            self.brush_cursor.hide()
            pos = QCursor.pos()
            if isinstance(pos, QPointF):
                scene_pos = pos
            else:
                cursor_pos = self.image_editor.image_viewer.mapFromGlobal(pos)
                scene_pos = self.image_editor.image_viewer.mapToScene(cursor_pos)
            self.brush_preview.update(scene_pos, int(size))
        else:
            self.brush_preview.hide()
            if self.cursor_style == 'outline' or not allow_cursor_preview:
                self._setup_outline_style()
            else:
                self._setup_simple_brush_style(center_x, center_y, radius)
        if not self.brush_cursor.isVisible():
            self.brush_cursor.show()

    def _setup_outline_style(self):
        self.brush_cursor.setPen(QPen(QColor(*gui_constants.BRUSH_COLORS['pen']),
                                      gui_constants.BRUSH_LINE_WIDTH / self.zoom_factor))
        self.brush_cursor.setBrush(Qt.NoBrush)

    def _setup_simple_brush_style(self, center_x, center_y, radius):
        gradient = create_brush_gradient(
            center_x, center_y, radius,
            self.brush.hardness,
            inner_color=QColor(*gui_constants.BRUSH_COLORS['inner']),
            outer_color=QColor(*gui_constants.BRUSH_COLORS['gradient_end']),
            opacity=self.brush.opacity
        )
        self.brush_cursor.setPen(QPen(QColor(*gui_constants.BRUSH_COLORS['pen']),
                                      gui_constants.BRUSH_LINE_WIDTH / self.zoom_factor))
        self.brush_cursor.setBrush(QBrush(gradient))

    def enterEvent(self, event):
        self.activateWindow()
        self.setFocus()
        if not self.empty:
            self.setCursor(Qt.BlankCursor)
            if self.brush_cursor:
                self.brush_cursor.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.empty:
            self.setCursor(Qt.ArrowCursor)
            if self.brush_cursor:
                self.brush_cursor.hide()
        super().leaveEvent(event)

    def setup_shortcuts(self):
        prev_layer = QShortcut(QKeySequence(Qt.Key_Up), self, context=Qt.ApplicationShortcut)
        prev_layer.activated.connect(self.prev_layer)
        next_layer = QShortcut(QKeySequence(Qt.Key_Down), self, context=Qt.ApplicationShortcut)
        next_layer.activated.connect(self.next_layer)

    def zoom_in(self):
        if self.empty:
            return
        current_scale = self.get_current_scale()
        new_scale = current_scale * gui_constants.ZOOM_IN_FACTOR
        if new_scale <= self.max_scale:
            self.scale(gui_constants.ZOOM_IN_FACTOR, gui_constants.ZOOM_IN_FACTOR)
            self.zoom_factor = new_scale
            self.update_brush_cursor()

    def zoom_out(self):
        if self.empty:
            return
        current_scale = self.get_current_scale()
        new_scale = current_scale * gui_constants.ZOOM_OUT_FACTOR
        if new_scale >= self.min_scale:
            self.scale(gui_constants.ZOOM_OUT_FACTOR, gui_constants.ZOOM_OUT_FACTOR)
            self.zoom_factor = new_scale
            self.update_brush_cursor()

    def reset_zoom(self):
        if self.empty:
            return
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        self.zoom_factor = self.get_current_scale()
        self.zoom_factor = max(self.min_scale, min(self.max_scale, self.zoom_factor))
        self.resetTransform()
        self.scale(self.zoom_factor, self.zoom_factor)
        self.update_brush_cursor()

    def actual_size(self):
        if self.empty:
            return
        self.zoom_factor = max(self.min_scale, min(self.max_scale, 1.0))
        self.resetTransform()
        self.scale(self.zoom_factor, self.zoom_factor)
        self.update_brush_cursor()

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

    def set_cursor_style(self, style):
        self.cursor_style = style
        if self.brush_cursor:
            self.update_brush_cursor()

    def position_on_image(self, pos):
        scene_pos = self.mapToScene(pos)
        item_pos = self.pixmap_item.mapFromScene(scene_pos)
        return item_pos
