# pylint: disable=C0114, C0116, R0913, R0917, E0611
from PySide6.QtGui import QRadialGradient
from PySide6.QtGui import QColor
from .. config.gui_constants import gui_constants


def create_brush_gradient(center_x, center_y, radius, hardness,
                          inner_color=None, outer_color=None, opacity=100):
    gradient = QRadialGradient(center_x, center_y, float(radius))
    inner = inner_color if inner_color is not None else \
        QColor(*gui_constants.BRUSH_COLORS['inner'])
    outer = outer_color if outer_color is not None else \
        QColor(*gui_constants.BRUSH_COLORS['gradient_end'])
    inner_with_opacity = QColor(inner)
    inner_with_opacity.setAlpha(int(float(inner.alpha()) * float(opacity) / 100.0))
    if hardness < 100:
        hardness_normalized = float(hardness) / 100.0
        gradient.setColorAt(0.0, inner_with_opacity)
        gradient.setColorAt(hardness_normalized, inner_with_opacity)
        gradient.setColorAt(1.0, outer)
    else:
        gradient.setColorAt(0.0, inner_with_opacity)
        gradient.setColorAt(1.0, inner_with_opacity)
    return gradient


def create_default_brush_gradient(center_x, center_y, radius, brush):
    return create_brush_gradient(
        center_x, center_y, radius,
        brush.hardness,
        inner_color=QColor(*gui_constants.BRUSH_COLORS['inner']),
        outer_color=QColor(*gui_constants.BRUSH_COLORS['gradient_end']),
        opacity=brush.opacity
    )
