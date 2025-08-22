# pylint: disable=C0114, C0115, C0116, R0903, E0611
from PySide6.QtWidgets import QFormLayout, QDialog
from PySide6.QtCore import Qt


class BaseFormDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(500, self.height())
        self.layout = QFormLayout(self)
        self.layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        self.layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.layout.setLabelAlignment(Qt.AlignLeft)

    def add_row_to_layout(self, item):
        self.layout.addRow(item)
