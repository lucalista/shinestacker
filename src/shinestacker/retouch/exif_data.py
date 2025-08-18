# pylint: disable=C0114, C0115, C0116, E0611
from PIL.TiffImagePlugin import IFDRational
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QPushButton, QDialog, QLabel
from PySide6.QtCore import Qt
from .. algorithms.exif import exif_dict
from .icon_container import icon_container


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
