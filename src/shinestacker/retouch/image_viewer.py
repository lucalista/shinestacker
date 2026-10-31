# pylint: disable=E0611, R0904, R0902, R0914, R0912, R0913, R0917
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from .image_view_status import ImageViewStatus
from .overlaid_view import OverlaidView
from .sidebyside_view import SideBySideView, TopBottomView


class ImageViewer(QWidget):
    def __init__(self, layer_collection, brush_tool, paint_area_manager, parent=None):
        super().__init__(parent)
        self.status = ImageViewStatus()
        self._strategies = {
            'overlaid':
                OverlaidView(layer_collection, self.status, brush_tool, paint_area_manager, self),
            'sidebyside':
                SideBySideView(layer_collection, self.status, brush_tool, paint_area_manager, self),
            'topbottom':
                TopBottomView(layer_collection, self.status, brush_tool, paint_area_manager, self)
        }
        for strategy in self._strategies.values():
            strategy.hide()
        self.strategy = self._strategies['overlaid']
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.strategy)
        self.strategy.show()

    def set_strategy(self, label):
        new_strategy = self._strategies.get(label, None)
        if new_strategy is None:
            raise RuntimeError(f"View strategy {label} is invalid.")
        self.layout.removeWidget(self.strategy)
        self.strategy.hide()
        self.strategy = new_strategy
        self.layout.addWidget(self.strategy)
        self.strategy.show()
        self.strategy.resize(self.size())
        if not self.strategy.empty():
            self.strategy.update_master_display()
            self.strategy.update_current_display()
            self.strategy.setup_brush_cursor()
            self.strategy.update_brush_cursor()
            self.strategy.show_master()
            self.strategy.setFocus()
            self.strategy.activateWindow()

    def empty(self):
        return self.strategy.empty()

    def set_master_image_np(self, img):
        self.strategy.set_master_image_np(img)

    def arrange_images(self):
        self.strategy.arrange_images()

    def show_master(self):
        self.strategy.show_master()

    def show_current(self):
        self.strategy.show_current()

    def update_master_display_area(self):
        self.strategy.update_master_display_area()

    def update_master_display(self):
        self.strategy.update_master_display()

    def update_current_display(self):
        self.strategy.update_current_display()

    def update_brush_cursor(self):
        self.strategy.update_brush_cursor()

    def refresh_display(self):
        self.strategy.refresh_display()

    def zoom_in(self):
        self.strategy.zoom_in()

    def zoom_out(self):
        self.strategy.zoom_out()

    def reset_zoom(self):
        self.strategy.reset_zoom()

    def actual_size(self):
        self.strategy.actual_size()

    def get_brush(self):
        return self.strategy.brush

    def get_current_scale(self):
        return self.strategy.get_current_scale()

    def get_cursor_style(self):
        return self.strategy.get_cursor_style()

    def position_on_image(self, pos):
        return self.strategy.position_on_image(pos)

    def get_visible_image_portion(self):
        return self.strategy.get_visible_image_portion()

    def hide_brush_cursor(self):
        self.strategy.hide_brush_cursor()

    def show_brush_cursor(self):
        self.strategy.show_brush_cursor()

    def hide_brush_preview(self):
        self.strategy.hide_brush_preview()

    def show_brush_preview(self):
        self.strategy.show_brush_preview()

    def clear_image(self):
        for st in self._strategies.values():
            st.clear_image()

    def set_brush(self, brush):
        for st in self._strategies.values():
            st.set_brush(brush)

    def set_preview_brush(self, brush):
        for st in self._strategies.values():
            st.set_preview_brush(brush)

    def set_cursor_style(self, style):
        for st in self._strategies.values():
            st.set_cursor_style(style)

    def connect_signals(
            self, handle_temp_view, end_copy_brush_area,
            handle_brush_size_change, handle_brush_hardness_change,
            handle_brush_opacity_change, handle_brush_flow_change,
            handle_needs_update):
        for st in self._strategies.values():
            st.temp_view_requested.connect(handle_temp_view)
            st.end_copy_brush_area_requested.connect(end_copy_brush_area)
            st.brush_size_change_requested.connect(handle_brush_size_change)
            st.brush_hardness_change_requested.connect(handle_brush_hardness_change)
            st.brush_opacity_change_requested.connect(handle_brush_opacity_change)
            st.brush_flow_change_requested.connect(handle_brush_flow_change)
            st.needs_update_requested.connect(handle_needs_update)
            st.setFocusPolicy(Qt.StrongFocus)
