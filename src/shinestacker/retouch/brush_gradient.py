# pylint: disable=R0913, R0917, R0914
from PySide6.QtGui import QRadialGradient
from PySide6.QtGui import QColor
from .. config.gui_constants import gui_constants


def create_brush_gradient(center_x, center_y, radius, hardness, opacity=100, luminosity=0):
    gradient = QRadialGradient(center_x, center_y, float(radius))
    if luminosity == 0:
        inner = gui_constants.BRUSH_COLORS['inner']
        outer = gui_constants.BRUSH_COLORS['gradient_end']
    else:
        inner, outer = [], []
        if luminosity < 0:
            lumi_scale = 1.0 + float(luminosity) / 100.0
            for i, (ci, co) in enumerate(zip(gui_constants.BRUSH_COLORS['inner'],
                                             gui_constants.BRUSH_COLORS['gradient_end'])):
                if i < 3:
                    inner.append(ci * lumi_scale)
                    outer.append(co * lumi_scale)
                else:
                    inner.append(ci)
                    outer.append(co)
        else:
            lumi_offset = 255.0 * float(luminosity) / 100.0
            for i, (ci, co) in enumerate(zip(gui_constants.BRUSH_COLORS['inner'],
                                             gui_constants.BRUSH_COLORS['gradient_end'])):
                if i < 3:
                    inner.append(min(255, lumi_offset + ci))
                    outer.append(min(255, lumi_offset + co))
                else:
                    inner.append(ci)
                    outer.append(co)
    outer = QColor(*outer)
    inner_corrected = QColor(*inner)
    inner_corrected.setAlpha(int(float(inner_corrected.alpha()) * float(opacity) / 100.0))
    if hardness < 100:
        hardness_normalized = float(hardness) / 100.0
        gradient.setColorAt(0.0, inner_corrected)
        gradient.setColorAt(hardness_normalized, inner_corrected)
        gradient.setColorAt(1.0, outer)
    else:
        gradient.setColorAt(0.0, inner_corrected)
        gradient.setColorAt(1.0, inner_corrected)
    return gradient


def create_default_brush_gradient(center_x, center_y, radius, brush):
    return create_brush_gradient(
        center_x, center_y, radius, hardness=brush.hardness,
        opacity=brush.opacity, luminosity=brush.luminosity
    )
