import os
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QPushButton, QDialog, QLabel
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from focusstack.core.core_utils import get_app_base_path


class ExifData(QDialog):
    def __init__(self, exif, parent=None):
        super().__init__(parent)
        self.exif = exif
        self.setWindowTitle("EXIF data")
        self.resize(500, self.height())
        self.layout = QFormLayout(self)
        self.layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        self.layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.layout.setLabelAlignment(Qt.AlignLeft)
        self.create_form()
        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.setFocus()
        button_box.addWidget(ok_button)
        self.layout.addRow(button_box)
        ok_button.clicked.connect(self.accept)

    def add_bold_label(self, label):
        label = QLabel(label)
        label.setStyleSheet("font-weight: bold")
        self.layout.addRow(label)

    def create_form(self):
        icon_path = f'{get_app_base_path()}'
        if os.path.exists(f'{icon_path}/ico'):
            icon_path = f'{icon_path}/ico'
        else:
            icon_path = f'{icon_path}/../ico'
        icon_path = f'{icon_path}/focus_stack.png'
        app_icon = QIcon(icon_path)
        icon_pixmap = app_icon.pixmap(128, 128)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignCenter)
        self.layout.addRow(icon_label)
        spacer = QLabel("")
        spacer.setFixedHeight(10)
        self.layout.addRow(spacer)
        shortcuts = {
            "EXIF data": "to be implemented soon...",
        }

        self.add_bold_label("EXIF data")
        for k, v in shortcuts.items():
            self.layout.addRow(f"<b>{k}:</b>", QLabel(v))
