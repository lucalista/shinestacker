from .. config.gui_constants import gui_constants


class PaintAreaManager:
    def __init__(self):
        self.x_start = None
        self.y_start = None
        self.x_end = None
        self.y_end = None
        self.reset()

    def reset(self):
        self.x_end = self.y_end = 0
        self.x_start = self.y_start = gui_constants.MAX_UNDO_SIZE

    def extend(self, x_start, y_start, x_end, y_end):
        self.x_start = min(self.x_start, x_start)
        self.y_start = min(self.y_start, y_start)
        self.x_end = max(self.x_end, x_end)
        self.y_end = max(self.y_end, y_end)

    def area(self):
        return self.x_start, self.y_start, self.x_end, self.y_end

    def set_area(self, x_start, y_start, x_end, y_end):
        self.x_start = x_start
        self.y_start = y_start
        self.x_end = x_end
        self.y_end = y_end
