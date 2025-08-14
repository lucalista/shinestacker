# pylint: disable=C0114, C0115, C0116, E0611
from PySide6.QtCore import QObject, Signal
from .. config.gui_constants import gui_constants


class UndoManager(QObject):
    stack_changed = Signal(bool, str, bool, str)

    def __init__(self):
        super().__init__()
        self.x_start = None
        self.y_start = None
        self.x_end = None
        self.y_end = None
        self.undo_stack = None
        self.redo_stack = None
        self.reset()

    def reset(self):
        self.undo_stack = []
        self.redo_stack = []
        self.reset_undo_area()
        self.stack_changed.emit(False, "", False, "")

    def reset_undo_area(self):
        self.x_end = self.y_end = 0
        self.x_start = self.y_start = gui_constants.MAX_UNDO_SIZE

    def extend_undo_area(self, x_start, y_start, x_end, y_end):
        self.x_start = min(self.x_start, x_start)
        self.y_start = min(self.y_start, y_start)
        self.x_end = max(self.x_end, x_end)
        self.y_end = max(self.y_end, y_end)

    def save_undo_state(self, layer, description):
        if layer is None:
            return
        self.redo_stack = []
        undo_state = {
            'master': layer[self.y_start:self.y_end, self.x_start:self.x_end],
            'area': (self.x_start, self.y_start, self.x_end, self.y_end),
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
        redo_state = {
            'master': layer[y_start:y_end, x_start:x_end].copy(),
            'area': (x_start, y_start, x_end, y_end),
            'description': undo_state['description']
        }
        self.redo_stack.append(redo_state)
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
        undo_state = {
            'master': layer[y_start:y_end, x_start:x_end].copy(),
            'area': (x_start, y_start, x_end, y_end),
            'description': redo_state['description']
        }
        self.undo_stack.append(undo_state)
        layer[y_start:y_end, x_start:x_end] = redo_state['master']
        undo_desc = undo_state['description']
        redo_desc = self.redo_stack[-1]['description'] if self.redo_stack else ""
        self.stack_changed.emit(bool(self.undo_stack), undo_desc, bool(self.redo_stack), redo_desc)
        return True
