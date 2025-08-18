# pylint: disable=C0114, C0115, C0116, E0611
import os
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt


def icon_container():
    icon_path = f"{os.path.dirname(__file__)}/../gui/ico/shinestacker.png"
    app_icon = QIcon(icon_path)
    pixmap = app_icon.pixmap(128, 128)
    label = QLabel()
    label.setPixmap(pixmap)
    label.setAlignment(Qt.AlignCenter)
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.addWidget(label)
    layout.setAlignment(Qt.AlignCenter)
    return container
