# pylint: disable=C0114, C0115, C0116, E0611, R0904, R0903, R0902, E1101, R0914, R0913, R0917
import math
import time
from abc import abstractmethod
import numpy as np
from PySide6.QtCore import Qt, QPointF, QTime, QPoint, Signal, QRectF
from PySide6.QtGui import QImage, QPainter, QColor, QBrush, QPen, QCursor, QPixmap, QPainterPath
from PySide6.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QApplication,
    QGraphicsItemGroup, QGraphicsPathItem)
from .. config.gui_constants import gui_constants
from .. config.defaults import DEFAULTS
from .. config.app_config import AppConfig
from .layer_collection import LayerCollectionHandler
from .brush_gradient import create_default_brush_gradient
from .brush_preview import BrushPreviewItem


class BrushCursor(QGraphicsItemGroup):
    def __init__(self, x0, y0, size, pen, brush):
        super().__init__()
        self._pen = pen
        self._radius = size / 2
        self._brush = brush
        self._rect = QRectF(x0 - self._radius, y0 - self._radius, size, size)
        self._arc_items = []
        self._create_arcs()

    def _point_on_circle(self, phi_deg):
        phi = phi_deg / 180.0 * math.pi
        x0 = self._rect.x() + self._radius
        y0 = self._rect.y() + self._radius
        return x0 + self._radius * math.cos(phi), y0 - self._radius * math.sin(phi)

    def _create_arcs(self):
        for item in self._arc_items:
            self.removeFromGroup(item)
            if item.scene():
                item.scene().removeItem(item)
        self._arc_items = []
        half_gap = 20
        arcs = [half_gap, 90 + half_gap, 180 + half_gap, 270 + half_gap]
        span_angle = 90 - 2 * half_gap
        for start_angle in arcs:
            path = QPainterPath()
            path.moveTo(*self._point_on_circle(start_angle))
            path.arcTo(self._rect, start_angle, span_angle)
            arc_item = QGraphicsPathItem(path)
            arc_item.setPen(self._pen)
            arc_item.setBrush(Qt.NoBrush)
            self.addToGroup(arc_item)
            self._arc_items.append(arc_item)

    # pylint: disable=C0103
    def setPen(self, pen):
        self._pen = pen
        for item in self._arc_items:
            item.setPen(pen)

    def pen(self):
        return self._pen

    def setBrush(self, brush):
        self._brush = brush
        for item in self._arc_items:
            item.setBrush(Qt.NoBrush)

    def brush(self):
        return self._brush

    def setRect(self, x, y, w, h):
        self._rect = QRectF(x, y, w, h)
        self._radius = min(w, h) / 2
        self._create_arcs()

    def rect(self):
        return self._rect
    # pylint: enable=C0103


class ViewSignals:
    temp_view_requested = Signal(bool)
    end_copy_brush_area_requested = Signal()
    brush_size_change_requested = Signal(int)  # +1 or -1
    brush_hardness_change_requested = Signal(int)
    brush_opacity_change_requested = Signal(int)
    brush_flow_change_requested = Signal(int)
    needs_update_requested = Signal()


class ImageGraphicsViewBase(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setInteractive(False)
        self.grabGesture(Qt.PinchGesture)
        self.grabGesture(Qt.PanGesture)
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setCursor(Qt.BlankCursor)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)


class ViewStrategy(LayerCollectionHandler):
    def __init__(self, layer_collection, status, brush_tool, paint_area_manager):
        LayerCollectionHandler.__init__(self, layer_collection)
        self.status = status
        self.brush_tool = brush_tool
        self.paint_area_manager = paint_area_manager
        self.mask_layer = None
        self.brush = None
        self.brush_cursor = None
        self.brush_preview = BrushPreviewItem(layer_collection)
        self.cursor_style = DEFAULTS['cursor_style']
        self.control_pressed = False
        self.space_pressed = False
        self.gesture_active = False
        self.pinch_center_view = None
        self.pinch_center_scene = None
        self.pinch_start_scale = None
        self.scrolling = False
        self.dragging = False
        self.last_brush_pos = None
        self.last_mouse_pos = None
        self.last_update_time = QTime.currentTime()
        self.last_color_update_time = 0
        self.last_cursor_update_time = 0
        self.enable_paint = True

    @abstractmethod
    def create_pixmaps(self):
        pass

    @abstractmethod
    def set_master_image(self, qimage):
        pass

    @abstractmethod
    def set_current_image(self, qimage):
        pass

    @abstractmethod
    def get_master_view(self):
        pass

    @abstractmethod
    def get_current_view(self):
        pass

    @abstractmethod
    def get_master_scene(self):
        pass

    @abstractmethod
    def get_current_scene(self):
        pass

    @abstractmethod
    def get_views(self):
        pass

    @abstractmethod
    def get_scenes(self):
        pass

    @abstractmethod
    def get_pixmaps(self):
        pass

    @abstractmethod
    def get_master_pixmap(self):
        pass

    @abstractmethod
    def get_current_pixmap(self):
        pass

    @abstractmethod
    def show_master(self):
        pass

    @abstractmethod
    def show_current(self):
        pass

    @abstractmethod
    def arrange_images(self):
        pass

    @abstractmethod
    def get_mouse_callbacks(self):
        pass

    @abstractmethod
    def set_mouse_callbacks(self, callbacks):
        pass

    @abstractmethod
    def get_view_with_mouse(self, event=None):
        pass

    def hide_brush_cursor(self):
        if self.brush_cursor:
            self.brush_cursor.hide()

    def show_brush_cursor(self):
        if self.brush_cursor:
            self.brush_cursor.show()

    def hide_brush_preview(self):
        if self.brush_preview:
            self.brush_preview.hide()

    def show_brush_preview(self):
        if self.brush_preview:
            self.brush_preview.show()

    def current_line_width(self):
        return gui_constants.BRUSH_LINE_WIDTH / self.zoom_factor()

    def zoom_factor(self):
        return self.status.zoom_factor

    def set_zoom_factor(self, zoom_factor):
        self.status.set_zoom_factor(zoom_factor)

    def get_current_scale(self):
        return self.get_master_view().transform().m11()

    def min_scale(self):
        return self.status.min_scale

    def max_scale(self):
        return self.status.max_scale

    def set_min_scale(self, scale):
        self.status.set_min_scale(scale)

    def set_max_scale(self, scale):
        self.status.set_max_scale(scale)

    def empty(self):
        return self.status.empty()

    def set_brush(self, brush):
        self.brush = brush

    def set_preview_brush(self, brush):
        self.brush_preview.brush = brush

    def set_cursor_style(self, style):
        self.cursor_style = style
        if style != 'simple' and self.brush_cursor:
            self.brush_cursor.setBrush(Qt.NoBrush)
        if style == 'preview':
            self.show_brush_preview()
        self.update_brush_cursor()

    def get_cursor_style(self):
        return self.cursor_style

    def handle_key_press_event(self, _event):
        return True

    def handle_key_release_event(self, _event):
        return True

    def update_view_display(self, layer, pixmap_item, scene, view):
        if self.empty():
            return
        qimage = self.numpy_to_qimage(layer)
        if qimage:
            pixmap = QPixmap.fromImage(qimage)
            pixmap_item.setPixmap(pixmap)
            scene.setSceneRect(QRectF(pixmap.rect()))
            view.horizontalScrollBar().setValue(self.status.h_scroll)
            view.verticalScrollBar().setValue(self.status.v_scroll)
            self.arrange_images()

    def update_master_display_area(self):
        if self.empty():
            return
        x_start, y_start, x_end, y_end = self.paint_area_manager.area()
        dirty_region = self.master_layer()[y_start:y_end, x_start:x_end]
        qimage = self.numpy_to_qimage(dirty_region)
        if not qimage:
            return
        pixmap = QPixmap.fromImage(qimage)
        master_pixmap_item = self.get_master_pixmap()
        current_pixmap = master_pixmap_item.pixmap()
        if current_pixmap.isNull():
            self.update_master_display()
            return
        painter = QPainter(current_pixmap)
        painter.drawPixmap(x_start, y_start, pixmap)
        painter.end()
        master_pixmap_item.setPixmap(current_pixmap)

    def update_master_display(self):
        self.update_view_display(
            self.master_layer(),
            self.get_master_pixmap(),
            self.get_master_scene(),
            self.get_master_view())

    def update_current_display(self):
        if self.number_of_layers() <= 0:
            return
        self.update_view_display(
            self.current_layer(),
            self.get_current_pixmap(),
            self.get_current_scene(),
            self.get_current_view())

    def update_cursor_pen_width(self):
        width = self.current_line_width()
        if self.brush_cursor is not None:
            pen = self.brush_cursor.pen()
            pen.setWidthF(width)
            self.brush_cursor.setPen(pen)
        return width

    def clear_image(self):
        for scene in self.get_scenes():
            scene.clear()
        self.create_pixmaps()
        self.status.clear()
        self.setup_brush_cursor()
        self.brush_preview = BrushPreviewItem(self.layer_collection)
        self.get_master_scene().addItem(self.brush_preview)
        self.setCursor(Qt.ArrowCursor)
        self.hide_brush_cursor()

    def set_master_image_np(self, img):
        self.set_master_image(self.numpy_to_qimage(img))
        if self.brush_cursor is None:
            self.setup_brush_cursor()
        self.show_master()

    def numpy_to_qimage(self, array):
        if array is None:
            return None
        if array.dtype == np.uint16:
            array = np.right_shift(array, 8).astype(np.uint8)
        if array.ndim == 2:
            height, width = array.shape
            return QImage(memoryview(array), width, height, width, QImage.Format_Grayscale8)
        if array.ndim == 3:
            height, width, _ = array.shape
            if not array.flags['C_CONTIGUOUS']:
                array = np.ascontiguousarray(array)
            return QImage(memoryview(array), width, height, 3 * width, QImage.Format_RGB888)
        return QImage()

    def setup_view_image(self, view, pixmap):
        img_width, img_height = pixmap.width(), pixmap.height()
        self.set_max_min_scales(img_width, img_height)
        view_rect = view.viewport().rect()
        scale_x = view_rect.width() / img_width
        scale_y = view_rect.height() / img_height
        scale_factor = min(scale_x, scale_y)
        scale_factor = max(self.min_scale(), min(scale_factor, self.max_scale()))
        self.set_zoom_factor(scale_factor)
        return img_width, img_height, scale_factor

    def create_scene(self, view):
        scene = QGraphicsScene()
        view.setScene(scene)
        scene.setBackgroundBrush(QBrush(QColor(120, 120, 120)))
        return scene

    def create_pixmap(self, scene):
        pixmap_item = QGraphicsPixmapItem()
        scene.addItem(pixmap_item)
        return pixmap_item

    def refresh_display(self):
        for scene in self.get_scenes():
            scene.update()
        self.update_brush_cursor()

    def set_max_min_scales(self, img_width, img_height):
        self.set_min_scale(min(gui_constants.MIN_ZOOMED_IMG_WIDTH / img_width,
                               gui_constants.MIN_ZOOMED_IMG_HEIGHT / img_height))
        self.set_max_scale(gui_constants.MAX_ZOOMED_IMG_PX_SIZE)

    def apply_zoom(self):
        if self.empty():
            return
        for view in self.get_views():
            current_scale = view.transform().m11()
            scale_factor = self.zoom_factor() / current_scale
            view.scale(scale_factor, scale_factor)

    def center_image(self, view):
        view.horizontalScrollBar().setValue(self.status.h_scroll)
        view.verticalScrollBar().setValue(self.status.v_scroll)

    def set_scroll_and_center(self, view, delta):
        self.status.set_scroll(
            view.horizontalScrollBar().value() + int(delta.x() * self.zoom_factor()),
            view.verticalScrollBar().value() + int(delta.y() * self.zoom_factor()))
        self.center_image(view)

    def apply_zoom_and_center(self, view, new_scale, ref_pos, old_center):
        self.set_zoom_factor(new_scale)
        self.apply_zoom()
        new_center = view.mapToScene(ref_pos)
        delta = old_center - new_center
        self.set_scroll_and_center(view, delta)

    def handle_pinch_gesture(self, pinch):
        master_view = self.get_master_view()
        if pinch.state() == Qt.GestureStarted:
            self.pinch_start_scale = self.zoom_factor()
            self.pinch_center_view = pinch.centerPoint()
            self.pinch_center_scene = master_view.mapToScene(self.pinch_center_view.toPoint())
            self.gesture_active = True
        elif pinch.state() == Qt.GestureUpdated:
            new_scale = self.pinch_start_scale * pinch.totalScaleFactor()
            new_scale = max(self.min_scale(), min(new_scale, self.max_scale()))
            if abs(new_scale - self.zoom_factor()) > 0.01:
                old_center = self.pinch_center_scene
                ref_pos = self.pinch_center_view.toPoint()
                self.apply_zoom_and_center(master_view, new_scale, ref_pos, old_center)
        elif pinch.state() in (Qt.GestureFinished, Qt.GestureCanceled):
            self.gesture_active = False
        self.update_cursor_pen_width()

    def do_zoom(self, new_scale, view):
        if self.empty():
            return
        if not self.min_scale() <= new_scale <= self.max_scale():
            return
        if view is None:
            view = self.get_master_view()
        global_pos = QCursor.pos()
        ref_pos = view.mapFromGlobal(global_pos)
        old_center = view.mapToScene(ref_pos)
        self.apply_zoom_and_center(view, new_scale, ref_pos, old_center)
        self.update_cursor_pen_width()

    def handle_wheel_event(self, event):
        if self.empty() or self.gesture_active:
            return
        if event.source() == Qt.MouseEventNotSynthesized:  # Physical mouse
            modifiers = QApplication.keyboardModifiers()
            if modifiers & Qt.ControlModifier and modifiers & Qt.ShiftModifier:
                self.brush_flow_change_requested.emit(1 if event.angleDelta().y() > 0 else -1)
            elif modifiers & Qt.ControlModifier:
                self.brush_size_change_requested.emit(1 if event.angleDelta().y() > 0 else -1)
            elif modifiers & Qt.ShiftModifier:
                self.brush_hardness_change_requested.emit(1 if event.angleDelta().y() > 0 else -1)
            elif modifiers & Qt.AltModifier:
                self.brush_opacity_change_requested.emit(1 if event.angleDelta().y() > 0 else -1)
            else:
                self.handle_zoom_wheel(self.get_view_with_mouse(event), event)
            self.update_brush_cursor()
        else:
            self.handle_wheel_touchpad_event(event)

    def handle_wheel_touchpad_event(self, event):
        if not self.control_pressed:
            delta = event.pixelDelta() or event.angleDelta() / 8
            if delta:
                self.scroll_view(self.get_view_with_mouse(event), delta.x(), delta.y())
        else:
            zoom_in = event.angleDelta().y() > 0
            if zoom_in:
                self.zoom_in()
            else:
                self.zoom_out()

    def handle_zoom_wheel(self, view, event):
        if view is None:
            return
        current_scale = self.get_current_scale()
        if event.angleDelta().y() > 0:
            new_scale = current_scale * gui_constants.ZOOM_IN_FACTOR
        else:
            new_scale = current_scale * gui_constants.ZOOM_OUT_FACTOR
        new_scale = max(self.min_scale(), min(new_scale, self.max_scale()))
        self.do_zoom(new_scale, view)

    def zoom_in(self):
        self.do_zoom(
            self.get_current_scale() * gui_constants.ZOOM_IN_FACTOR,
            self.get_view_with_mouse())

    def zoom_out(self):
        self.do_zoom(
            self.get_current_scale() * gui_constants.ZOOM_OUT_FACTOR,
            self.get_view_with_mouse())

    def reset_zoom(self):
        if self.empty():
            return
        self.pinch_start_scale = 1.0
        self.gesture_active = False
        self.pinch_center_view = None
        self.pinch_center_scene = None
        for pixmap, view in self.get_pixmaps().items():
            view.fitInView(pixmap, Qt.KeepAspectRatio)
        self.set_zoom_factor(self.get_current_scale())
        self.set_zoom_factor(max(self.min_scale(), min(self.max_scale(), self.zoom_factor())))
        for view in self.get_views():
            view.resetTransform()
            view.scale(self.zoom_factor(), self.zoom_factor())
        self.update_brush_cursor()
        self.update_cursor_pen_width()

    def actual_size(self):
        if self.empty():
            return
        self.set_zoom_factor(max(self.min_scale(), min(self.max_scale(), 1.0)))
        for view in self.get_views():
            view.resetTransform()
            view.scale(self.zoom_factor(), self.zoom_factor())
        self.update_brush_cursor()
        self.update_cursor_pen_width()

    def setup_simple_brush_style(self, center_x, center_y, radius):
        if self.brush_cursor:
            pen = self.brush_cursor.pen()
        else:
            pen = QPen(QColor(*gui_constants.BRUSH_COLORS['pen']), self.current_line_width())
        gradient = create_default_brush_gradient(center_x, center_y, radius, self.brush)
        self.brush_cursor.setPen(pen)
        self.brush_cursor.setBrush(QBrush(gradient))

    def create_circle(self, scene, line_style=Qt.SolidLine):
        for item in scene.items():
            if isinstance(item, QGraphicsEllipseItem) and item != self.brush_preview:
                scene.removeItem(item)
        pen = QPen(QColor(*gui_constants.BRUSH_COLORS['pen']),
                   self.current_line_width(), line_style)
        brush = Qt.NoBrush
        scene_center = scene.sceneRect().center()
        brush_cursor = scene.addEllipse(
            scene_center.x(), scene_center.y(),
            self.brush.size, self.brush.size, pen, brush)
        brush_cursor.setZValue(1000)
        brush_cursor.hide()
        return brush_cursor

    def create_alt_circle(self, scene, line_style=Qt.SolidLine):
        for item in scene.items():
            if isinstance(item, BrushCursor) and item != self.brush_preview:
                scene.removeItem(item)
        pen = QPen(QColor(*gui_constants.BRUSH_COLORS['pen']),
                   self.current_line_width(), line_style)
        brush = Qt.NoBrush
        scene_center = scene.sceneRect().center()
        brush_cursor = BrushCursor(
            scene_center.x(), scene_center.y(),
            self.brush.size, pen, brush
        )
        brush_cursor.setZValue(1000)
        brush_cursor.hide()
        scene.addItem(brush_cursor)
        return brush_cursor

    def setup_brush_cursor(self):
        if not self.brush:
            return
        self.brush_cursor = self.create_circle(self.get_master_scene())

    def update_brush_cursor(self):
        if self.empty() or self.brush_cursor is None or not self.isVisible():
            return
        self.update_cursor_pen_width()
        master_view = self.get_master_view()
        mouse_pos = master_view.mapFromGlobal(QCursor.pos())
        if not master_view.rect().contains(mouse_pos):
            self.hide_brush_cursor()
            return
        scene_pos = master_view.mapToScene(mouse_pos)
        size = self.brush.size
        radius = size / 2
        self.brush_cursor.setRect(scene_pos.x() - radius, scene_pos.y() - radius, size, size)
        if self.cursor_style == 'preview':
            if self.brush_preview.isVisible():
                self.hide_brush_cursor()
                pos = QCursor.pos()
                if isinstance(pos, QPointF):
                    scene_pos = pos
                else:
                    cursor_pos = master_view.mapFromGlobal(pos)
                    scene_pos = master_view.mapToScene(cursor_pos)
                self.brush_preview.update(scene_pos, int(size))
        else:
            self.hide_brush_preview()
        self.update_master_cursor_color()
        if self.cursor_style == 'brush':
            self.setup_simple_brush_style(scene_pos.x(), scene_pos.y(), radius)
        if not self.scrolling:
            self.show_brush_cursor()

    def update_color_time(self):
        current_time = time.time()
        if current_time - self.last_color_update_time < 0.2:
            return False
        self.last_color_update_time = current_time
        return True

    def update_master_cursor_color(self):
        self.update_cursor_color_based_on_background(
            self.brush_cursor, self.master_layer(),
            self.get_visible_image_region, self.get_master_pixmap,
            self.update_color_time)

    def update_cursor_color_based_on_background(
            self, cursor, layer,
            visible_region, get_pixmap, update_timer):
        if not update_timer():
            return
        cursor_rect = cursor.rect()
        image_region = visible_region()
        if image_region and cursor_rect.intersects(image_region):
            intersect_rect = cursor_rect.intersected(image_region)
            top_left = get_pixmap().mapFromScene(intersect_rect.topLeft())
            bottom_right = get_pixmap().mapFromScene(intersect_rect.bottomRight())
            x1, y1 = max(0, int(top_left.x())), max(0, int(top_left.y()))
            x2, y2 = min(layer.shape[1], int(bottom_right.x())), \
                min(layer.shape[0], int(bottom_right.y()))
            if x2 > x1 and y2 > y1:
                region = layer[y1:y2, x1:x2]
                if region.size > 10000:
                    step = int(math.sqrt(region.size / 100))
                    region = region[::step, ::step]
                if region.ndim == 3:
                    luminosity = np.dot(region[..., :3], [0.299, 0.587, 0.114])
                    avg_luminosity = np.mean(luminosity)
                else:
                    avg_luminosity = np.mean(region)
                if region.dtype == np.uint16:
                    avg_luminosity /= 256.0
                if avg_luminosity < 128:
                    new_color = QColor(255, 255, 255)
                else:
                    new_color = QColor(0, 0, 0)
                current_pen = cursor.pen()
                current_pen.setColor(new_color)
                cursor.setPen(current_pen)

    def position_on_image(self, pos):
        master_view = self.get_master_view()
        pixmap = self.get_master_pixmap()
        scene_pos = master_view.mapToScene(pos)
        item_pos = pixmap.mapFromScene(scene_pos)
        return item_pos

    def get_visible_image_region(self):
        if self.empty():
            return None
        master_view = self.get_master_view()
        master_pixmap = self.get_master_pixmap()
        view_rect = master_view.viewport().rect()
        scene_rect = master_view.mapToScene(view_rect).boundingRect()
        image_rect = master_pixmap.mapFromScene(scene_rect).boundingRect().toRect()
        return image_rect.intersected(master_pixmap.boundingRect().toRect())

    def get_visible_current_image_region(self):
        if self.empty():
            return None
        current_view = self.get_current_view()
        current_pixmap = self.get_current_pixmap()
        view_rect = current_view.viewport().rect()
        scene_rect = current_view.mapToScene(view_rect).boundingRect()
        image_rect = current_pixmap.mapFromScene(scene_rect).boundingRect().toRect()
        return image_rect.intersected(current_pixmap.boundingRect().toRect())

    def get_visible_image_portion(self):
        if self.has_no_master_layer():
            return None
        visible_rect = self.get_visible_image_region()
        if not visible_rect:
            return self.master_layer()
        x, y = int(visible_rect.x()), int(visible_rect.y())
        w, h = int(visible_rect.width()), int(visible_rect.height())
        master_img = self.master_layer()
        return master_img[y:y + h, x:x + w], (x, y, w, h)

    def map_to_scene(self, pos):
        return self.get_master_view().mapToScene(pos)

    # pylint: disable=C0103
    def keyPressEvent(self, event):
        if self.empty():
            return
        if event.key() in (Qt.Key_Space, Qt.Key_P) and not self.scrolling:
            self.space_pressed = True
            self.get_master_view().setCursor(Qt.OpenHandCursor)
            self.hide_brush_cursor()
        if self.handle_key_press_event(event):
            if event.key() == Qt.Key_Control and not self.scrolling:
                self.control_pressed = True
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.empty():
            return
        if event.key() in (Qt.Key_Space, Qt.Key_P):
            self.space_pressed = False
            if not self.scrolling:
                self.get_master_view().setCursor(Qt.BlankCursor)
                self.show_brush_cursor()
        if self.handle_key_release_event(event):
            if event.key() == Qt.Key_Control:
                self.control_pressed = False
            super().keyReleaseEvent(event)

    def leaveEvent(self, event):
        if self.empty():
            self.setCursor(Qt.ArrowCursor)
        else:
            self.get_master_view().setCursor(Qt.ArrowCursor)
            self.hide_brush_cursor()
        super().leaveEvent(event)
    # pylint: enable=C0103

    def scroll_view(self, view, delta_x, delta_y):
        view.horizontalScrollBar().setValue(
            view.horizontalScrollBar().value() - delta_x)
        view.verticalScrollBar().setValue(
            view.verticalScrollBar().value() - delta_y)
        self.status.set_scroll(view.horizontalScrollBar().value(),
                               view.verticalScrollBar().value())

    def copy_brush_area_to_master(self, view_pos):
        if self.layer_stack() is None or self.number_of_layers() == 0:
            return
        area = self.brush_tool.apply_brush_operation(
            self.master_layer_copy(),
            self.current_layer(),
            self.master_layer(), self.mask_layer,
            view_pos)
        self.paint_area_manager.extend(*area)

    def begin_copy_brush_area(self, pos):
        self.mask_layer = self.blank_layer().copy()
        self.copy_master_layer()
        self.paint_area_manager.reset()
        self.copy_brush_area_to_master(pos)
        self.needs_update_requested.emit()

    def continue_copy_brush_area(self, pos):
        self.copy_brush_area_to_master(pos)
        self.needs_update_requested.emit()

    def mouse_press_event(self, event):
        if self.empty():
            return
        if event.button() & Qt.LeftButton and self.has_master_layer():
            if self.space_pressed:
                self.scrolling = True
                self.last_mouse_pos = event.position()
                self.setCursor(Qt.ClosedHandCursor)
            elif self.enable_paint:
                self.last_brush_pos = event.position()
                self.begin_copy_brush_area(event.position().toPoint())
                self.dragging = True
            if not self.scrolling:
                self.show_brush_cursor()

    def mouse_move_event(self, event):
        if self.empty():
            return
        current_time = time.time() * 1000  # ms
        cursor_update_interval = AppConfig.get('cursor_update_time')
        if current_time - self.last_cursor_update_time < cursor_update_interval:
            return
        self.last_cursor_update_time = current_time
        position = event.position()
        brush_size = self.brush.size
        if not self.space_pressed:
            self.update_brush_cursor()
        if self.enable_paint and self.dragging and event.buttons() & Qt.LeftButton:
            current_time = QTime.currentTime()
            paint_refresh_time = AppConfig.get('paint_refresh_time')
            if self.last_update_time.msecsTo(current_time) >= paint_refresh_time:
                min_step = AppConfig.get('min_mouse_step_brush_fraction')
                min_step = brush_size * min_step * self.zoom_factor()
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
                        self.continue_copy_brush_area(pos)
                    self.last_brush_pos = position
                self.last_update_time = current_time
        if self.scrolling and event.buttons() & Qt.LeftButton:
            master_view = self.get_master_view()
            if self.space_pressed:
                master_view.setCursor(Qt.ClosedHandCursor)
                self.hide_brush_cursor()
            delta = position - self.last_mouse_pos
            self.last_mouse_pos = position
            self.scroll_view(master_view, delta.x(), delta.y())

    def mouse_release_event(self, event):
        if self.empty():
            return
        master_view = self.get_master_view()
        if self.space_pressed:
            master_view.setCursor(Qt.OpenHandCursor)
            self.hide_brush_cursor()
        else:
            master_view.setCursor(Qt.BlankCursor)
            self.show_brush_cursor()
        if event.button() == Qt.LeftButton:
            if self.scrolling:
                self.scrolling = False
                self.last_mouse_pos = None
            elif self.dragging:
                self.dragging = False
                self.end_copy_brush_area_requested.emit()
