from .. config.gui_constants import gui_constants


class UndoManager:
    def __init__(self):
        self.undo_stack = []
        self.max_undo_steps = gui_constants.MAX_UNDO_STEPS
        self.reset_undo_area()

    def reset_undo_area(self):
        self.x_end = self.y_end = 0
        self.x_start = self.y_start = gui_constants.MAX_UNDO_SIZE

    def extend_undo_area(self, x_start, y_start, x_end, y_end):
        self.x_start = min(self.x_start, x_start)
        self.y_start = min(self.y_start, y_start)
        self.x_end = max(self.x_end, x_end)
        self.y_end = max(self.y_end, y_end)

    def save_undo_state(self, layer):
        if layer is None:
            return
        undo_state = {
            'master': layer[self.y_start:self.y_end, self.x_start:self.x_end],
            'area': (self.x_start, self.y_start, self.x_end, self.y_end)
        }
        if len(self.undo_stack) >= self.max_undo_steps:
            self.undo_stack.pop(0)
        self.undo_stack.append(undo_state)

    def undo(self, layer):
        if layer is None or not self.undo_stack or len(self.undo_stack) == 0:
            return False
        else:
            undo_state = self.undo_stack.pop()
            x_start, y_start, x_end, y_end = undo_state['area']
            layer[y_start:y_end, x_start:x_end] = undo_state['master']
            return True
