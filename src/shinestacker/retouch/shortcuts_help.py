import os
from PySide6.QtWidgets import (QFormLayout, QHBoxLayout, QPushButton, QDialog,
                               QLabel, QVBoxLayout, QWidget)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt


class ShortcutsHelp(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shortcut Help")
        self.resize(600, self.height())
        self.layout = QVBoxLayout(self)
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        left_column = QWidget()
        left_layout = QFormLayout(left_column)
        left_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        left_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        left_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        left_layout.setLabelAlignment(Qt.AlignLeft)
        right_column = QWidget()
        right_layout = QFormLayout(right_column)
        right_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        right_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        right_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        right_layout.setLabelAlignment(Qt.AlignLeft)
        main_layout.addWidget(left_column)
        main_layout.addWidget(right_column)
        self.layout.addWidget(main_widget)
        self.create_form(left_layout, right_layout)
        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.setFocus()
        button_box.addWidget(ok_button)
        self.layout.addLayout(button_box)
        ok_button.clicked.connect(self.accept)

    def add_bold_label(self, layout, label):
        label = QLabel(label)
        label.setStyleSheet("font-weight: bold")
        layout.addRow(label)

    def create_form(self, left_layout, right_layout):
        icon_path = f"{os.path.dirname(__file__)}/../gui/ico/shinestacker.png"
        app_icon = QIcon(icon_path)
        icon_pixmap = app_icon.pixmap(128, 128)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_container = QWidget()
        icon_container_layout = QHBoxLayout(icon_container)
        icon_container_layout.addWidget(icon_label)
        icon_container_layout.setAlignment(Qt.AlignCenter)
        self.layout.insertWidget(0, icon_container)

        shortcuts = {
            "M": "show master layer",
            "L": "show selected layer",
            "X": "temp. toggle between master and source layer",
            "↑": "select one layer up",
            "↓": "selcet one layer down",
            "Ctrl + O": "open file",
            "Ctrl + S": "save multilayer tiff",
            "Crtl + Z": "undo brush draw",
            "Ctrl + M": "copy selected layer to master",
            "Ctrl + Cmd + F": "full screen mode",
            "Ctrl + +": "zoom in",
            "Ctrl + -": "zoom out",
            "Ctrl + 0": "adapt to screen",
            "Ctrl + =": "actual size",
            "[": "increase brush size",
            "]": "decrease brush size",
            "{": "increase brush hardness",
            "}": "decrease brush hardness"
        }

        self.add_bold_label(left_layout, "Keyboard Shortcuts")
        for k, v in shortcuts.items():
            left_layout.addRow(f"<b>{k}</b>", QLabel(v))

        mouse_controls = {
            "Space + Drag": "pan",
            "Wheel": "zoom in/out",
            "Ctrl + Wheel": "adjust brush size",
            "Left Click": "brush action",
        }

        self.add_bold_label(right_layout, "Mouse Controls")
        for k, v in mouse_controls.items():
            right_layout.addRow(f"<b>{k}</b>", QLabel(v))
