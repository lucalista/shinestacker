# pylint: disable=C0114, C0115, C0116, C0103, R0903
import math


class _GuiConstants:
    GUI_IMG_WIDTH = 250  # px
    DISABLED_TAG = ""  # " <disabled>"

    MIN_ZOOMED_IMG_WIDTH = 600
    MIN_ZOOMED_IMG_HEIGHT = 600
    MAX_ZOOMED_IMG_PX_SIZE = 40
    MAX_UNDO_SIZE = 65535

    NEW_PROJECT_NOISE_DETECTION = False
    NEW_PROJECT_VIGNETTING_CORRECTION = False
    NEW_PROJECT_ALIGN_FRAMES = True
    NEW_PROJECT_BALANCE_FRAMES = True
    NEW_PROJECT_BUNCH_STACK = False
    NEW_PROJECT_BUNCH_FRAMES = {'min': 2, 'max': 20}
    NEW_PROJECT_BUNCH_OVERLAP = {'min': 0, 'max': 10}
    NEW_PROJECT_FOCUS_STACK_PYRAMID = True
    NEW_PROJECT_FOCUS_STACK_DEPTH_MAP = False
    NEW_PROJECT_MULTI_LAYER = False

    BRUSH_COLORS = {
        'outer': (255, 0, 0, 200),
        'inner': (255, 0, 0, 150),
        'gradient_end': (255, 0, 0, 0),
        'pen': (255, 0, 0, 150),
        'preview': (255, 180, 180),
        'cursor_inner': (255, 0, 0, 120),
        'preview_inner': (255, 255, 255, 150)
    }

    MIN_MOUSE_STEP_BRUSH_FRACTION = 0.25
    PAINT_REFRESH_TIMER = 50  # milliseconds

    THUMB_WIDTH = 120  # px
    THUMB_HEIGHT = 80  # px
    THUMB_HI_COLOR = '#0000FF'
    THUMB_LO_COLOR = '#0000FF'
    THUMB_MASTER_HI_COLOR = '#0000FF'
    THUMB_MASTER_LO_COLOR = 'transparent'

    BRUSH_SIZE_SLIDER_MAX = 1000

    UI_SIZES = {
        'brush_preview': (100, 80),
        'thumbnail_width': 100,
        'master_thumb': (THUMB_WIDTH, THUMB_HEIGHT),
        'label_height': 20
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
