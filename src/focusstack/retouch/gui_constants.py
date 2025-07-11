import math
from PySide6.QtGui import QColor


class _GuiConstants:
    APP_TITLE = "Focus Stack"
    MIN_ZOOMED_IMG_WIDTH = 400
    MAX_ZOOMED_IMG_PX_SIZE = 50
    MAX_UNDO_SIZE = 65535

    BRUSH_COLORS = {
        'outer': QColor(255, 0, 0, 200),
        'inner': QColor(255, 0, 0, 150),
        'gradient_end': QColor(255, 0, 0, 0),
        'pen': QColor(255, 0, 0, 150),
        'preview': QColor(255, 180, 180),
        'cursor_inner': QColor(255, 0, 0, 120),
        'preview_inner': QColor(255, 255, 255, 150)
    }

    MIN_MOUSE_STEP_BRUSH_FRACTION = 0.25
    PAINT_REFRESH_TIMER = 50  # milliseconds

    THUMB_WIDTH = 120
    THUMB_HEIGHT = 80
    IMG_WIDTH = 100
    IMG_HEIGHT = 80
    LABEL_HEIGHT = 20

    MAX_UNDO_STEPS = 50

    BRUSH_SIZE_SLIDER_MAX = 1000

    UI_SIZES = {
        'brush_preview': (100, 80),
        'thumbnail': (IMG_WIDTH, IMG_HEIGHT),
        'master_thumb': (THUMB_WIDTH, THUMB_HEIGHT)
    }

    DEFAULT_BRUSH_HARDNESS = 50
    DEFAULT_BRUSH_OPACITY = 100
    DEFAULT_BRUSH_FLOW = 100
    BRUSH_SIZES = {
        'default': 50,
        'min': 5,
        'mid': 50,
        'max': 1000
    }
    DEFAULT_CURSOR_STYLE = 'preview'
    BRUSH_LINE_WIDTH = 2
    BRUSH_PREVIEW_LINE_WIDTH = 1.5
    ZOOM_IN_FACTOR = 1.25
    ZOOM_OUT_FACTOR = 0.80

    def calculate_gamma(self):
        if self.BRUSH_SIZES['mid'] <= self.BRUSH_SIZES['min'] or self.BRUSH_SIZES['max'] <= 0:
            return 1.0
        ratio = (self.BRUSH_SIZES['mid'] - self.BRUSH_SIZES['min']) / self.BRUSH_SIZES['max']
        half_point = self.BRUSH_SIZE_SLIDER_MAX / 2
        if ratio <= 0:
            return 1.0
        gamma = math.log(ratio) / math.log(half_point / self.BRUSH_SIZE_SLIDER_MAX)
        return gamma

    def __setattr__aux(self, name, value):
        raise AttributeError(f"Can't reassign constant '{name}'")

    def __init__(self):
        self.BRUSH_GAMMA = self.calculate_gamma()
        _GuiConstants.__setattr__ = _GuiConstants.__setattr__aux


gui_constants = _GuiConstants()
