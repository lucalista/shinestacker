# pylint: disable=C0114, C0115, C0116, E0611
from PySide6.QtWidgets import (QFormLayout, QHBoxLayout, QPushButton, QDialog,
                               QLabel, QVBoxLayout, QWidget)
from PySide6.QtCore import Qt
from .icon_container import icon_container


class ShortcutsHelp(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shortcut Help")
        self.resize(600, self.height())
        self.main_layout = QVBoxLayout(self)
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
        self.main_layout.addWidget(main_widget)
        self.create_form(left_layout, right_layout)
        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.setFixedWidth(100)
        ok_button.setFocus()
        button_box.addWidget(ok_button)
        self.main_layout.addLayout(button_box)
        ok_button.clicked.connect(self.accept)

    def add_bold_label(self, layout, label):
        label = QLabel(f"{label}:")
        label.setStyleSheet("font-weight: bold")
        layout.addRow(label)

    def create_form(self, left_layout, right_layout):
        self.main_layout.insertWidget(0, icon_container())

        shortcuts = {
            "M": "Show master layer",
            "L": "Show selected layer",
            "T": "Toggle master/selected layer",
            "X": "Temporarily toggle between master and source layer",
            "↑": "Select one layer up",
            "↓": "Select one layer down",
            "Ctrl + O": "Open file",
            "Ctrl + S": "Save multilayer tiff",
            "Ctrl + Z": "Undo brush draw",
            "Ctrl + M": "Copy selected layer to master",
            "Ctrl + Cmd + F or F11": "Full screen mode",
            "Ctrl + +": "Zoom in",
            "Ctrl + -": "Zoom out",
            "Ctrl + 0": "Fit to screen",
            "Ctrl + R": "Actual size",
            "Ctrl + 1": "View: overlaid",
            "Ctrl + 2": "View: side by side",
            "Ctrl + 3": "View: top-bottom",
        }

        self.add_bold_label(left_layout, "Keyboard Shortcuts")
        for k, v in shortcuts.items():
            left_layout.addRow(f"<b>{k}</b>", QLabel(v))

        shortcuts = {
            "[": "Decrease brush size",
            "]": "Increase brush size",
            "{": "Decrease brush hardness",
            "}": "Increase brush hardness",
            ",": "Decrease brush opacity",
            ".": "Increase brush opacity",
            ";": "Decrease brush flow",
            ":": "Increase brush flow",
            "&gt;": "Increase brush luminosity",
            "&lt;": "Decrease brush luminosity",
        }

        self.add_bold_label(right_layout, "Keyboard Shortcuts")
        for k, v in shortcuts.items():
            right_layout.addRow(f"<b>{k}</b>", QLabel(v))

        mouse_controls = {
            "Space + Drag": "Move",
            "Wheel": "Zoom in/out",
            "Ctrl + Wheel": "Adjust brush size",
            "Shift + Wheel": "Adjust brush hardness",
            "Alt + Wheel": "Adjust brush opacity",
            "Ctrl + Shift + Wheel": "Adjust brush flow",
            "Left Click": "Use brush to copy from selected layer to master",
        }

        spacer = QLabel("")
        spacer.setFixedHeight(10)
        right_layout.addWidget(spacer)
        self.add_bold_label(right_layout, "Mouse Controls")
        for k, v in mouse_controls.items():
            right_layout.addRow(f"<b>{k}</b>", QLabel(v))

        touchpad_controls = {
            "Two-finger drag": "Move",
            "Pinch two fingers": "Zoom in/out"
        }
        spacer = QLabel("")
        spacer.setFixedHeight(10)
        right_layout.addWidget(spacer)
        self.add_bold_label(right_layout, "Touchpad Controls")
        for k, v in touchpad_controls.items():
            right_layout.addRow(f"<b>{k}</b>", QLabel(v))
