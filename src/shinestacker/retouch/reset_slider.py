# pylint: disable=E0611, R0903
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSlider


class ResetSlider(QSlider):
    def __init__(self, default_value, orientation=Qt.Horizontal):
        super().__init__(orientation)
        self.default_value = default_value
        self.setToolTip("Double-click to reset")

    # pylint: disable=C0103
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setValue(self.default_value)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)
    # pylint: enable=C0103
