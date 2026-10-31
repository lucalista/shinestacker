# pylint: disable=R0903, E0611
class ColorEntry:
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def tuple(self):
        return self.r, self.g, self.b

    def hex(self):
        return f"{self.r:02x}{self.g:02x}{self.b:02x}"


class ColorPalette:
    LIGHT_BLUE = ColorEntry(210, 210, 240)
    LIGHT_GREEN = ColorEntry(210, 240, 210)
    LIGHT_RED = ColorEntry(240, 210, 210)
    DARK_BLUE = ColorEntry(0, 0, 80)
    DARK_RED = ColorEntry(80, 0, 0)
    DARK_GREEN = ColorEntry(0, 80, 0)
    MEDIUM_BLUE = ColorEntry(160, 160, 200)
    MEDIUM_GREEN = ColorEntry(160, 200, 160)
    MEDIUM_RED = ColorEntry(200, 160, 160)
    DARK_BLUE_0 = DARK_BLUE
    DARK_BLUE_1 = ColorEntry(26, 26, 93)   # ~10% lighter
    DARK_BLUE_2 = ColorEntry(51, 51, 106)  # ~20% lighter
    LIGHT_BLUE_0 = LIGHT_BLUE
    LIGHT_BLUE_1 = ColorEntry(189, 189, 216)  # ~10% darker
    LIGHT_BLUE_2 = ColorEntry(168, 168, 192)  # ~20% darker
    DARK_RED_0 = DARK_RED
    DARK_RED_1 = ColorEntry(93, 26, 26)   # ~10% lighter
    DARK_RED_2 = ColorEntry(106, 51, 51)  # ~20% lighter
    LIGHT_RED_0 = LIGHT_RED
    LIGHT_RED_1 = ColorEntry(216, 189, 189)  # ~10% darker
    LIGHT_RED_2 = ColorEntry(192, 168, 168)  # ~20% darker


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

ACTION_RUNNING_COLOR = ColorPalette.MEDIUM_BLUE
ACTION_COMPLETED_COLOR = ColorPalette.MEDIUM_GREEN
ACTION_STOPPED_COLOR = ColorPalette.MEDIUM_RED
ACTION_FAILED_COLOR = ColorPalette.MEDIUM_RED
ACTION_RUNNING_BKG_COLOR = ColorPalette.LIGHT_BLUE
ACTION_COMPLETED_BKG_COLOR = ColorPalette.LIGHT_GREEN
ACTION_STOPPED_BKG_COLOR = ColorPalette.LIGHT_RED
ACTION_FAILED_BKG_COLOR = ColorPalette.LIGHT_RED
ACTION_RUNNING_TXT_COLOR = ColorPalette.DARK_BLUE
ACTION_COMPLETED_TXT_COLOR = ColorPalette.DARK_GREEN
ACTION_STOPPED_TXT_COLOR = ColorPalette.DARK_RED
ACTION_FAILED_TXT_COLOR = ColorPalette.DARK_RED
