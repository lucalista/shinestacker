import os
from PySide6.QtGui import QIcon


class IconManager:
    def __init__(self, dark_theme=False):
        self.script_dir = os.path.dirname(__file__)
        self.dark_theme = dark_theme

    def get_icon(self, icon_name):
        theme_dir = 'dark' if self.dark_theme else 'light'
        path = os.path.join(self.script_dir, "img", theme_dir, f"{icon_name}.png")
        return QIcon(path)

    def set_dark_theme(self, dark_theme):
        if self.dark_theme != dark_theme:
            self.dark_theme = dark_theme
            self._update_icons()

    def _update_icons(self):
        pass
