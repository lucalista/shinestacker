# pylint: disable=C0114, C0115, C0116, E0611
from PIL.TiffImagePlugin import IFDRational
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt
from .. algorithms.exif import exif_dict
from .icon_container import icon_container
from .. gui.base_form_dialog import BaseFormDialog


class ExifData(BaseFormDialog):
    def __init__(self, exif, parent=None):
        super().__init__("EXIF data", parent)
        self.exif = exif
        self.create_form()
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setAlignment(Qt.AlignCenter)
        ok_button = QPushButton("OK")
        ok_button.setFixedWidth(100)
        ok_button.setFocus()
        button_layout.addWidget(ok_button)
        self.add_row_to_layout(button_container)
        ok_button.clicked.connect(self.accept)

    def add_bold_label(self, label):
        label = QLabel(label)
        label.setStyleSheet("font-weight: bold")
        self.layout.addRow(label)

    def create_form(self):
        self.layout.addRow(icon_container())

        spacer = QLabel("")
        spacer.setFixedHeight(10)
        self.layout.addRow(spacer)
        self.add_bold_label("EXIF data")
        shortcuts = {}
        if self.exif is None:
            shortcuts['Warning:'] = 'no EXIF data found'
            data = {}
        else:
            data = exif_dict(self.exif)
        if len(data) > 0:
            for k, (_, d) in data.items():
                if isinstance(d, IFDRational):
                    d = f"{d.numerator}/{d.denominator}"
                else:
                    d = f"{d}"
                if "<<<" not in d and k != 'IPTCNAA':
                    self.layout.addRow(f"<b>{k}:</b>", QLabel(d))
        else:
            self.layout.addRow("-", QLabel("Empty EXIF dictionary"))
