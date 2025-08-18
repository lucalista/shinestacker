# pylint: disable=C0114, C0115, C0116, E0611, R0902
from PySide6.QtWidgets import QMainWindow, QMessageBox, QAbstractItemView
from .. config.constants import constants
from .undo_manager import UndoManager
from .layer_collection import LayerCollection
from .io_gui_handler import IOGuiHandler
from .display_manager import DisplayManager
from .brush_tool import BrushTool
from .layer_collection import LayerCollectionHandler


class ImageEditor(QMainWindow, LayerCollectionHandler):
    def __init__(self):
        QMainWindow.__init__(self)
        LayerCollectionHandler.__init__(self, LayerCollection())
        self.undo_manager = UndoManager()
        self.undo_action = None
        self.redo_action = None
        self.undo_manager.stack_changed.connect(self.update_undo_redo_actions)
        self.io_gui_handler = None
        self.display_manager = None
        self.brush_tool = BrushTool()
        self.modified = False
        self.installEventFilter(self)
        self.mask_layer = None

    def setup_ui(self):
        self.display_manager = DisplayManager(
            self.layer_collection, self.image_viewer,
            self.master_thumbnail_label, self.thumbnail_list, parent=self)
        self.io_gui_handler = IOGuiHandler(self.layer_collection, self.undo_manager, parent=self)
        self.display_manager.status_message_requested.connect(self.show_status_message)
        self.display_manager.cursor_preview_state_changed.connect(
            lambda state: setattr(self.image_viewer, 'allow_cursor_preview', state))
        self.io_gui_handler.status_message_requested.connect(self.show_status_message)
        self.io_gui_handler.update_title_requested.connect(self.update_title)
        self.brush_tool.setup_ui(self.brush, self.brush_preview, self.image_viewer,
                                 self.brush_size_slider, self.hardness_slider, self.opacity_slider,
                                 self.flow_slider)
        self.image_viewer.brush = self.brush_tool.brush
        self.brush_tool.update_brush_thumb()
        self.io_gui_handler.setup_ui(self.display_manager, self.image_viewer)
        self.image_viewer.display_manager = self.display_manager

    def show_status_message(self, message):
        self.statusBar().showMessage(message)

    # pylint: disable=C0103
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
    # pylint: enable=C0103

    def check_unsaved_changes(self) -> bool:
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
        self.sort_layers(order)
        self.display_manager.update_thumbnails()
        self.change_layer(self.current_layer())

    def update_title(self):
        title = constants.APP_TITLE
        if self.io_gui_handler is not None:
            path = self.io_gui_handler.current_file_path
            if path != '':
                title += f" - {path.split('/')[-1]}"
                if self.modified:
                    title += " *"
        self.window().setWindowTitle(title)

    def mark_as_modified(self):
        self.modified = True
        self.update_title()

    def change_layer(self, layer_idx):
        if 0 <= layer_idx < self.number_of_layers():
            view_state = self.image_viewer.get_view_state()
            self.set_current_layer_idx(layer_idx)
            self.display_manager.display_current_view()
            self.image_viewer.set_view_state(view_state)
            self.thumbnail_list.setCurrentRow(layer_idx)
            self.thumbnail_list.setFocus()
            self.image_viewer.update_brush_cursor()
            self.image_viewer.setFocus()

    def prev_layer(self):
        if self.layer_stack() is not None:
            new_idx = max(0, self.current_layer_idx() - 1)
            if new_idx != self.current_layer_idx():
                self.change_layer(new_idx)
                self.highlight_thumbnail(new_idx)

    def next_layer(self):
        if self.layer_stack() is not None:
            new_idx = min(self.number_of_layers() - 1, self.current_layer_idx() + 1)
            if new_idx != self.current_layer_idx():
                self.change_layer(new_idx)
                self.highlight_thumbnail(new_idx)

    def highlight_thumbnail(self, index):
        self.thumbnail_list.setCurrentRow(index)
        self.thumbnail_list.scrollToItem(
            self.thumbnail_list.item(index), QAbstractItemView.PositionAtCenter)

    def copy_layer_to_master(self):
        if self.layer_stack() is None or self.master_layer() is None:
            return
        reply = QMessageBox.question(
            self,
            "Confirm Copy",
            "Warning: the current master layer will be erased\n\nDo you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.set_master_layer(self.current_layer().copy())
            self.master_layer().setflags(write=True)
            self.display_manager.display_current_view()
            self.display_manager.update_thumbnails()
            self.mark_as_modified()
            self.statusBar().showMessage(f"Copied layer {self.current_layer_idx() + 1} to master")

    def copy_brush_area_to_master(self, view_pos):
        if self.layer_stack() is None or self.number_of_layers() == 0 \
           or not self.display_manager.allow_cursor_preview():
            return
        area = self.brush_tool.apply_brush_operation(
            self.master_layer_copy(),
            self.current_layer(),
            self.master_layer(), self.mask_layer,
            view_pos, self.image_viewer)
        self.undo_manager.extend_undo_area(*area)

    def begin_copy_brush_area(self, pos):
        if self.display_manager.allow_cursor_preview():
            self.mask_layer = self.io_gui_handler.blank_layer.copy()
            self.copy_master_layer()
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
            self.undo_manager.save_undo_state(self.master_layer_copy(), 'Brush Stroke')
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
