# pylint: disable=C0114, C0115, R0903
from .. config.gui_constants import gui_constants


class Brush:
    def __init__(self):
        self.size = gui_constants.BRUSH_SIZES['default']
        self.hardness = gui_constants.DEFAULT_BRUSH_HARDNESS
        self.opacity = gui_constants.DEFAULT_BRUSH_OPACITY
        self.flow = gui_constants.DEFAULT_BRUSH_FLOW
