# pylint: disable=C0114, C0115, C0116, E0611, E1101, R0904, R0912, R0914, R0902, E0202, R0913, R0917
from PySide6.QtCore import Qt, QPointF, QEvent, QRectF
from .view_strategy import ViewStrategy, ImageGraphicsViewBase, ViewSignals


class OverlaidView(ViewStrategy, ImageGraphicsViewBase, ViewSignals):
    def __init__(self, layer_collection, status, brush_tool, paint_area_manager, parent):
        ViewStrategy.__init__(self, layer_collection, status, brush_tool, paint_area_manager)
        ImageGraphicsViewBase.__init__(self, parent)
        self.scene = self.create_scene(self)
        self.create_pixmaps()
        self.scene.addItem(self.brush_preview)
        self.brush_cursor = None
        self.pinch_start_scale = 1.0
        self.last_scroll_pos = QPointF()

    def create_pixmaps(self):
        self.pixmap_item_master = self.create_pixmap(self.scene)
        self.pixmap_item_current = self.create_pixmap(self.scene)

    def get_master_view(self):
        return self

    def get_current_view(self):
        return self

    def get_master_scene(self):
        return self.scene

    def get_current_scene(self):
        return self.scene

    def get_master_pixmap(self):
        return self.pixmap_item_master

    def get_current_pixmap(self):
        return self.pixmap_item_current

    def get_views(self):
        return [self]

    def get_scenes(self):
        return [self.scene]

    def get_pixmaps(self):
        return {
            self.pixmap_item_master: self,
            self.pixmap_item_current: self
        }

# pylint: disable=C0103
    def mousePressEvent(self, event):
        self.mouse_press_event(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.mouse_move_event(event)

    def mouseReleaseEvent(self, event):
        self.mouse_release_event(event)
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        self.handle_wheel_event(event)
        event.accept()

    def enterEvent(self, event):
        self.activateWindow()
        self.setFocus()
        if self.empty():
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.BlankCursor)
            if self.brush_cursor:
                self.brush_cursor.show()
        super().enterEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.auto_fit_to_window:
            self.handle_resize(self)

    def get_mouse_callbacks(self):
        return self.mousePressEvent

    def set_mouse_callbacks(self, callbacks):
        self.mousePressEvent = callbacks
# pylint: enable=C0103

    def get_view_with_mouse(self, event=None):
        return self

    def show(self):
        self.show_master()
        super().show()

    def event(self, event):
        if event.type() == QEvent.Gesture:
            return self.handle_gesture_event(event)
        return super().event(event)

    def setup_scene_image(self, pixmap, pixmap_item):
        self.setSceneRect(QRectF(pixmap.rect()))
        _img_width, _img_height, scale_factor = self.setup_view_image(self, pixmap)
        self.resetTransform()
        self.scale(scale_factor, scale_factor)
        self.centerOn(pixmap_item)
        self.center_image(self)
        self.update_cursor_pen_width()

    def set_master_image(self, qimage):
        self.status.set_master_image(qimage)
        self.setup_scene_image(self.status.pixmap_master, self.pixmap_item_master)
        self.update_master_display()

    def set_current_image(self, qimage):
        self.status.set_current_image(qimage)
        if self.empty():
            self.setup_scene_image(self.status.pixmap_current, self.pixmap_item_current)

    def setup_brush_cursor(self):
        super().setup_brush_cursor()
        self.update_cursor_pen_width()

    def show_master(self):
        self.pixmap_item_master.setVisible(True)
        self.pixmap_item_current.setVisible(False)
        self.show_brush_preview()
        self.enable_paint = True
        if self.brush_cursor:
            self.scene.removeItem(self.brush_cursor)
            self.brush_cursor = self.create_circle(self.scene)
            self.update_brush_cursor()

    def show_current(self):
        self.pixmap_item_master.setVisible(False)
        self.pixmap_item_current.setVisible(True)
        self.hide_brush_preview()
        self.enable_paint = False
        if self.brush_cursor:
            self.scene.removeItem(self.brush_cursor)
            self.brush_cursor = self.create_alt_circle(self.scene)
            self.update_brush_cursor()

    def master_is_visible(self):
        return self.pixmap_item_master.isVisible()

    def current_is_visible(self):
        return self.pixmap_item_current.isVisible()

    def arrange_images(self):
        if self.empty():
            return
        if self.master_is_visible():
            pixmap = self.pixmap_item_master.pixmap()
            if not pixmap.isNull():
                self.setSceneRect(QRectF(pixmap.rect()))
                self.centerOn(self.pixmap_item_master)
                self.center_image(self)
        elif self.current_is_visible():
            pixmap = self.pixmap_item_current.pixmap()
            if not pixmap.isNull():
                self.setSceneRect(QRectF(pixmap.rect()))
                self.centerOn(self.pixmap_item_current)
                self.center_image(self)
        current_scale = self.get_current_scale()
        scale_factor = self.zoom_factor() / current_scale
        self.scale(scale_factor, scale_factor)

    def handle_key_press_event(self, event):
        if event.key() in [Qt.Key_Up, Qt.Key_Down]:
            return False
        if event.key() == Qt.Key_X:
            self.temp_view_requested.emit(True)
            return False
        return True

    def handle_key_release_event(self, event):
        if event.key() in [Qt.Key_Up, Qt.Key_Down]:
            return False
        if event.key() == Qt.Key_X:
            self.temp_view_requested.emit(False)
            return False
        return True

    def handle_gesture_event(self, event):
        if self.empty():
            return False
        handled = False
        pan_gesture = event.gesture(Qt.PanGesture)
        if pan_gesture:
            self.handle_pan_gesture(pan_gesture)
            handled = True
        pinch_gesture = event.gesture(Qt.PinchGesture)
        if pinch_gesture:
            self.handle_pinch_gesture(pinch_gesture)
            handled = True
        if handled:
            event.accept()
        return handled

    def handle_pan_gesture(self, pan_gesture):
        if pan_gesture.state() == Qt.GestureStarted:
            self.last_scroll_pos = pan_gesture.delta()
            self.gesture_active = True
        elif pan_gesture.state() == Qt.GestureUpdated:
            delta = pan_gesture.delta() - self.last_scroll_pos
            self.last_scroll_pos = pan_gesture.delta()
            scaled_delta = delta / self.get_current_scale()
            self.scroll_view(self, int(scaled_delta.x()), int(scaled_delta.y()))
        elif pan_gesture.state() == Qt.GestureFinished:
            self.gesture_active = False
