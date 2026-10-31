# pylint: disable=E0611
from PySide6.QtCore import QObject, Signal
from .. config.gui_constants import gui_constants


class UndoManager(QObject):
    stack_changed = Signal(bool, str, bool, str)

    def __init__(self, transformation_manager, paint_area_manager):
        super().__init__()
        self.transformation_manager = transformation_manager
        self.paint_area_manager = paint_area_manager
        self.undo_stack = None
        self.redo_stack = None
        self.reset()

    def reset(self):
        self.undo_stack = []
        self.redo_stack = []
        self.reset_undo_area()
        self.stack_changed.emit(False, "", False, "")

    def reset_undo_area(self):
        self.paint_area_manager.reset()

    def paint_area(self):
        return self.paint_area_manager.area()

    def set_paint_area(self, x_start, y_start, x_end, y_end):
        self.paint_area_manager.set_area(x_start, y_start, x_end, y_end)

    def save_undo_state(self, layer, description):
        if layer is None:
            return
        self.redo_stack = []
        x_start, y_start, x_end, y_end = self.paint_area()
        undo_state = {
            'master': layer[y_start:y_end, x_start:x_end].copy(),
            'area': (x_start, y_start, x_end, y_end),
            'description': description
        }
        if len(self.undo_stack) >= gui_constants.MAX_UNDO_SIZE:
            self.undo_stack.pop(0)
        self.undo_stack.append(undo_state)
        undo_desc = description
        redo_desc = self.redo_stack[-1]['description'] if self.redo_stack else ""
        self.stack_changed.emit(bool(self.undo_stack), undo_desc, bool(self.redo_stack), redo_desc)

    def undo(self, layer):
        if layer is None or not self.undo_stack:
            return False
        undo_state = self.undo_stack.pop()
        x_start, y_start, x_end, y_end = undo_state['area']
        self.set_paint_area(x_start, y_start, x_end, y_end)
        redo_state = {
            'master': layer[y_start:y_end, x_start:x_end].copy(),
            'area': (x_start, y_start, x_end, y_end),
            'description': undo_state['description']
        }
        self.redo_stack.append(redo_state)
        descr = undo_state['description']
        if descr.startswith(gui_constants.ROTATE_LABEL):
            if descr == gui_constants.ROTATE_90_CW_LABEL:
                self.transformation_manager.rotate_90_ccw(False)
            elif descr == gui_constants.ROTATE_90_CCW_LABEL:
                self.transformation_manager.rotate_90_cw(False)
            elif descr == gui_constants.ROTATE_180_LABEL:
                self.transformation_manager.rotate_180(False)
        else:
            layer[y_start:y_end, x_start:x_end] = undo_state['master']
        undo_desc = self.undo_stack[-1]['description'] if self.undo_stack else ""
        redo_desc = redo_state['description']
        self.stack_changed.emit(bool(self.undo_stack), undo_desc, bool(self.redo_stack), redo_desc)
        return True

    def redo(self, layer):
        if layer is None or not self.redo_stack:
            return False
        redo_state = self.redo_stack.pop()
        x_start, y_start, x_end, y_end = redo_state['area']
        self.set_paint_area(x_start, y_start, x_end, y_end)
        undo_state = {
            'master': layer[y_start:y_end, x_start:x_end].copy(),
            'area': (x_start, y_start, x_end, y_end),
            'description': redo_state['description']
        }
        self.undo_stack.append(undo_state)
        descr = undo_state['description']
        if descr.startswith(gui_constants.ROTATE_LABEL):
            if descr == gui_constants.ROTATE_90_CW_LABEL:
                self.transformation_manager.rotate_90_cw(False)
            elif descr == gui_constants.ROTATE_90_CCW_LABEL:
                self.transformation_manager.rotate_90_ccw(False)
            elif descr == gui_constants.ROTATE_180_LABEL:
                self.transformation_manager.rotate_180(False)
        else:
            layer[y_start:y_end, x_start:x_end] = redo_state['master']
        undo_desc = undo_state['description']
        redo_desc = self.redo_stack[-1]['description'] if self.redo_stack else ""
        self.stack_changed.emit(bool(self.undo_stack), undo_desc, bool(self.redo_stack), redo_desc)
        return True
