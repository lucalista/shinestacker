from PySide6.QtGui import QColor


class ColorEntry:
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def tuple(self):
        return self.r, self.g, self.b

    def hex(self):
        return f"{self.r:02x}{self.g:02x}{self.b:02x}"

    def q_color(self):
        return QColor(self.r, self.g, self.b)


class ColorPalette:
    BLACK = ColorEntry(0, 0, 0)
    WHITE = ColorEntry(255, 255, 255)
    LIGHT_BLUE = ColorEntry(210, 210, 240)
    LIGHT_RED = ColorEntry(240, 210, 210)
    DARK_BLUE = ColorEntry(0, 0, 160)
    DARK_RED = ColorEntry(160, 0, 0)
    MEDIUM_BLUE = ColorEntry(160, 160, 200)
    MEDIUM_GREEN = ColorEntry(160, 200, 160)
    MEDIUM_RED = ColorEntry(200, 160, 160)


RED_BUTTON_STYLE = f"""
    QPushButton {{
        color: #{ColorPalette.DARK_RED.hex()};
    }}
    QPushButton:disabled {{
        color: #{ColorPalette.MEDIUM_RED.hex()};
    }}
"""

BLUE_BUTTON_STYLE = f"""
    QPushButton {{
        color: #{ColorPalette.DARK_BLUE.hex()};
    }}
    QPushButton:disabled {{
        color: #{ColorPalette.MEDIUM_BLUE.hex()};
    }}
"""

BLUE_COMBO_STYLE = f"""
    QComboBox {{
        color: #{ColorPalette.DARK_BLUE.hex()};
    }}
    QComboBox:disabled {{
        color: #{ColorPalette.MEDIUM_BLUE.hex()};
    }}
"""
