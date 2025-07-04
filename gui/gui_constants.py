from PySide6.QtGui import QColor


class _GuiConstants:
    MIN_ZOOMED_IMG_WIDTH = 400
    MAX_ZOOMED_IMG_PX_SIZE = 50

    BRUSH_COLORS = {
        'outer': QColor(255, 0, 0, 200),
        'inner': QColor(255, 0, 0, 150),
        'gradient_end': QColor(255, 0, 0, 0),
        'pen': QColor(255, 0, 0, 150),
        'preview': QColor(255, 180, 180),
        'cursor_inner': QColor(255, 0, 0, 120),
        'preview_inner': QColor(255, 255, 255, 150)
    }

    MIN_MOUSE_STEP_BRUSH_FRACTION = 0.2
    PAINT_REFRESH_TIMER = 50  # milliseconds

    def __setattr__(self, name, value):
        raise AttributeError(f"Can't reassign constant '{name}'")


gui_constants = _GuiConstants()
