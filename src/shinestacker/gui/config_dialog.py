from abc import abstractmethod
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QScrollArea, QFormLayout, QDialog
from .base_form_dialog import create_form_layout


class ConfigDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.form_layout = create_form_layout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container_widget = QWidget()
        self.container_layout = QFormLayout(container_widget)
        self.container_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.container_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        self.container_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.container_layout.setLabelAlignment(Qt.AlignLeft)
        scroll_area.setWidget(container_widget)
        self.button_box = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.setFocus()
        self.cancel_button = QPushButton("Cancel")
        self.reset_button = QPushButton("Reset")
        self.button_box.addWidget(self.ok_button)
        self.button_box.addWidget(self.cancel_button)
        self.button_box.addWidget(self.reset_button)
        self.reset_button.clicked.connect(self.reset_to_defaults)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.form_layout.addRow(scroll_area)
        self.form_layout.addRow(self.button_box)
        QTimer.singleShot(0, self.adjust_dialog_size)
        self.create_form_content()

    @abstractmethod
    def create_form_content(self):
        pass

    def adjust_dialog_size(self):
        screen_geometry = self.screen().availableGeometry()
        screen_height = screen_geometry.height()
        screen_width = screen_geometry.width()
        scroll_area = self.findChild(QScrollArea)
        container_widget = scroll_area.widget()
        container_size = container_widget.sizeHint()
        container_height = container_size.height()
        container_width = container_size.width()
        button_row_height = 50  # Approx height of button row
        margins_height = 40  # Approx. height of margins
        total_height_needed = container_height + button_row_height + margins_height
        if total_height_needed < screen_height * 0.8:
            width = max(container_width + 40, 600)
            height = total_height_needed
            self.resize(width, height)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            max_height = int(screen_height * 0.9)
            width = max(container_width + 40, 600)
            width = min(width, int(screen_width * 0.9))
            self.resize(width, max_height)
            self.setMaximumHeight(max_height)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.setMinimumHeight(min(max_height, 500))
            self.setMinimumWidth(width)
        self.center_on_screen()

    def center_on_screen(self):
        screen_geometry = self.screen().availableGeometry()
        center_point = screen_geometry.center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def reset_to_defaults(self):
        pass
