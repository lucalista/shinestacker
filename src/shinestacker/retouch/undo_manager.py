from PySide6.QtCore import QObject, Signal
from .. config.gui_constants import gui_constants


class UndoManager(QObject):
    stack_changed = Signal(bool, str)

    def __init__(self):
        super().__init__()
        self.undo_stack = []
        self.max_undo_steps = gui_constants.MAX_UNDO_STEPS
        self.reset_undo_area()
        self.stack_changed.emit(False, "")

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
        undo_state = {
            'master': layer[self.y_start:self.y_end, self.x_start:self.x_end],
            'area': (self.x_start, self.y_start, self.x_end, self.y_end),
            'description': description
        }
        if len(self.undo_stack) >= self.max_undo_steps:
            self.undo_stack.pop(0)
        self.undo_stack.append(undo_state)
        self.stack_changed.emit(True, description)

    def undo(self, layer):
        if layer is None or not self.undo_stack or len(self.undo_stack) == 0:
            return False
        else:
            undo_state = self.undo_stack.pop()
            x_start, y_start, x_end, y_end = undo_state['area']
            layer[y_start:y_end, x_start:x_end] = undo_state['master']
            has_undo = bool(self.undo_stack)
            last_description = self.undo_stack[-1]['description'] if has_undo else ""
            self.stack_changed.emit(has_undo, last_description)
            return True
