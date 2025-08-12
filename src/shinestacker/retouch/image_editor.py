from PySide6.QtWidgets import QMainWindow, QMessageBox, QAbstractItemView
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QEvent, QPoint
from .. config.constants import constants
from .. config.gui_constants import gui_constants
from .undo_manager import UndoManager
from .layer_collection import LayerCollection
from .io_manager import IOManager
from .io_gui_handler import IOGuiHandler
from .brush_gradient import create_brush_gradient
from .display_manager import DisplayManager
from .brush_tool import BrushTool


class ImageEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.layer_collection = LayerCollection()
        self.undo_manager = UndoManager()
        self.undo_action = None
        self.redo_action = None
        self.undo_manager.stack_changed.connect(self.update_undo_redo_actions)
        self.io_manager = IOManager(self.layer_collection)
        self.io_gui_handler = None
        self.display_manager = None
        self.brush_tool = BrushTool()
        self.modified = False
        self.installEventFilter(self)

    def setup_ui(self):
        self.display_manager = DisplayManager(self.layer_collection, self.image_viewer,
                                              self.master_thumbnail_label, self.thumbnail_list, parent=self)
        self.io_gui_handler = IOGuiHandler(self.io_manager, self.layer_collection,
                                           self.undo_manager, parent=self)
        self.display_manager.status_message_requested.connect(self.show_status_message)
        self.io_gui_handler.status_message_requested.connect(self.show_status_message)
        self.brush_tool.setup_ui(self.brush, self.brush_preview, self.image_viewer,
                                 self.brush_size_slider, self.hardness_slider, self.opacity_slider,
                                 self.flow_slider)
        self.image_viewer.brush = self.brush_tool.brush
        self.brush_tool.update_brush_thumb()
        self.io_gui_handler.setup_ui(self.display_manager, self.image_viewer)

    def show_status_message(self, message):
        self.statusBar().showMessage(message)

    def keyPressEvent(self, event):
        if self.image_viewer.empty:
            return
        if event.text() == '[':
            self.brush_tool.decrease_brush_size()
            return
        if event.text() == ']':
            self.brush_tool.increase_brush_size()
            return
        if event.text() == '{':
            self.brush_tool.decrease_brush_hardness()
            return
        if event.text() == '}':
            self.brush_tool.increase_brush_hardness()
            return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_X:
            self.display_manager.start_temp_view()
            return True
        if event.type() == QEvent.KeyRelease and event.key() == Qt.Key_X:
            self.display_manager.end_temp_view()
            return True
        return super().eventFilter(obj, event)

    def _check_unsaved_changes(self) -> bool:
        if self.modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "The image stack has unsaved changes. Do you want to continue?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self.save_file()
                return True
            if reply == QMessageBox.Discard:
                return True
            return False
        return True

    def sort_layers(self, order):
        self.layer_collection.sort_layers(order)
        self.display_manager.update_thumbnails()
        self.change_layer(self.layer_collection.current_layer)

    def update_title(self):
        title = constants.APP_TITLE
        if self.io_manager.current_file_path:
            title += f" - {self.io_manager.current_file_path.split('/')[-1]}"
            if self.modified:
                title += " *"
        self.window().setWindowTitle(title)

    def mark_as_modified(self):
        self.modified = True
        self.update_title()

    def change_layer(self, layer_idx):
        if 0 <= layer_idx < self.layer_collection.number_of_layers():
            view_state = self.image_viewer.get_view_state()
            self.layer_collection.current_layer_idx = layer_idx
            self.display_manager.display_current_view()
            self.image_viewer.set_view_state(view_state)
            self.thumbnail_list.setCurrentRow(layer_idx)
            self.thumbnail_list.setFocus()
            self.image_viewer.update_brush_cursor()
            self.image_viewer.setFocus()

    def prev_layer(self):
        if self.layer_collection.layer_stack is not None:
            new_idx = max(0, self.layer_collection.current_layer_idx - 1)
            if new_idx != self.layer_collection.current_layer_idx:
                self.change_layer(new_idx)
                self.highlight_thumbnail(new_idx)

    def next_layer(self):
        if self.layer_collection.layer_stack is not None:
            new_idx = min(self.layer_collection.number_of_layers() - 1, self.layer_collection.current_layer_idx + 1)
            if new_idx != self.layer_collection.current_layer_idx:
                self.change_layer(new_idx)
                self.highlight_thumbnail(new_idx)

    def highlight_thumbnail(self, index):
        self.thumbnail_list.setCurrentRow(index)
        self.thumbnail_list.scrollToItem(self.thumbnail_list.item(index), QAbstractItemView.PositionAtCenter)

    def copy_layer_to_master(self):
        if self.layer_collection.layer_stack is None or self.layer_collection.master_layer is None:
            return
        reply = QMessageBox.question(
            self,
            "Confirm Copy",
            "Warning: the current master layer will be erased\n\nDo you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.layer_collection.master_layer = self.layer_collection.current_layer().copy()
            self.layer_collection.master_layer.setflags(write=True)
            self.display_manager.display_current_view()
            self.display_manager.update_thumbnails()
            self.mark_as_modified()
            self.statusBar().showMessage(f"Copied layer {self.layer_collection.current_layer_idx + 1} to master")

    def copy_brush_area_to_master(self, view_pos):
        if self.layer_collection.layer_stack is None or self.layer_collection.number_of_layers() == 0 \
           or not self.display_manager.allow_cursor_preview():
            return
        area = self.brush_tool.apply_brush_operation(
            self.layer_collection.master_layer_copy,
            self.layer_collection.current_layer(),
            self.layer_collection.master_layer, self.mask_layer,
            view_pos, self.image_viewer)
        self.undo_manager.extend_undo_area(*area)

    def update_brush_thumb(self):
        width, height = gui_constants.UI_SIZES['brush_preview']
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        preview_size = min(self.brush.size, width + 30, height + 30)
        center_x, center_y = width // 2, height // 2
        radius = preview_size // 2
        if self.image_viewer.cursor_style == 'preview':
            gradient = create_brush_gradient(
                center_x, center_y, radius,
                self.brush.hardness,
                inner_color=QColor(*gui_constants.BRUSH_COLORS['inner']),
                outer_color=QColor(*gui_constants.BRUSH_COLORS['gradient_end']),
                opacity=self.brush.opacity
            )
            painter.setBrush(QBrush(gradient))
            painter.setPen(QPen(QColor(*gui_constants.BRUSH_COLORS['outer']), gui_constants.BRUSH_PREVIEW_LINE_WIDTH))
        elif self.image_viewer.cursor_style == 'outline':
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(*gui_constants.BRUSH_COLORS['outer']), gui_constants.BRUSH_PREVIEW_LINE_WIDTH))
        else:
            painter.setBrush(QBrush(QColor(*gui_constants.BRUSH_COLORS['cursor_inner'])))
            painter.setPen(QPen(QColor(*gui_constants.BRUSH_COLORS['pen']), gui_constants.BRUSH_PREVIEW_LINE_WIDTH))
        painter.drawEllipse(QPoint(center_x, center_y), radius, radius)
        if self.image_viewer.cursor_style == 'preview':
            painter.setPen(QPen(QColor(0, 0, 160)))
            painter.drawText(0, 10, f"Size: {int(self.brush.size)}px")
            painter.drawText(0, 25, f"Hardness: {self.brush.hardness}%")
            painter.drawText(0, 40, f"Opacity: {self.brush.opacity}%")
            painter.drawText(0, 55, f"Flow: {self.brush.flow}%")
        painter.end()
        self.brush_preview.setPixmap(pixmap)
        self.image_viewer.update_brush_cursor()

    def begin_copy_brush_area(self, pos):
        if self.display_manager.allow_cursor_preview():
            self.mask_layer = self.io_gui_handler.blank_layer.copy()
            self.layer_collection.copy_master_layer()
            self.undo_manager.reset_undo_area()
            self.copy_brush_area_to_master(pos)
            self.display_manager.needs_update = True
            if not self.display_manager.update_timer.isActive():
                self.display_manager.update_timer.start()
            self.mark_as_modified()

    def continue_copy_brush_area(self, pos):
        if self.display_manager.allow_cursor_preview():
            self.copy_brush_area_to_master(pos)
            self.display_manager.needs_update = True
            if not self.display_manager.update_timer.isActive():
                self.display_manager.update_timer.start()
            self.mark_as_modified()

    def end_copy_brush_area(self):
        if self.display_manager.update_timer.isActive():
            self.display_manager.display_master_layer()
            self.display_manager.update_master_thumbnail()
            self.undo_manager.save_undo_state(self.layer_collection.master_layer_copy, 'Brush Stroke')
            self.display_manager.update_timer.stop()
            self.mark_as_modified()

    def update_undo_redo_actions(self, has_undo, undo_desc, has_redo, redo_desc):
        if self.undo_action:
            if has_undo:
                self.undo_action.setText(f"Undo {undo_desc}")
                self.undo_action.setEnabled(True)
            else:
                self.undo_action.setText("Undo")
                self.undo_action.setEnabled(False)
        if self.redo_action:
            if has_redo:
                self.redo_action.setText(f"Redo {redo_desc}")
                self.redo_action.setEnabled(True)
            else:
                self.redo_action.setText("Redo")
                self.redo_action.setEnabled(False)
