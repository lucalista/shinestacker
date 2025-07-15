import os
from PySide6.QtWidgets import (QWidget, QLineEdit, QFormLayout, QHBoxLayout, QPushButton,
                               QDialog, QSizePolicy, QFileDialog, QLabel, QCheckBox,
                               QSpinBox, QMessageBox)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from focusstack.config.gui_constants import gui_constants
from focusstack.config.constants import constants
from focusstack.core.core_utils import get_app_base_path


class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
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
        cancel_button = QPushButton("Cancel")
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        self.layout.addRow(button_box)
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

    def expert(self):
        return self.parent().expert_options

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
        self.input_folder = QLineEdit()
        self.input_folder .setPlaceholderText('input files folder')
        button = QPushButton("Browse...")

        def browse():
            path = QFileDialog.getExistingDirectory(None, "Select input files folder")
            if path:
                self.input_folder.setText(path)
        button.clicked.connect(browse)
        button.setAutoDefault(False)
        layout = QHBoxLayout()
        layout.addWidget(self.input_folder)
        layout.addWidget(button)
        layout.setContentsMargins(0, 0, 0, 0)
        container = QWidget()
        container.setLayout(layout)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.noise_detection = QCheckBox()
        self.noise_detection.setChecked(gui_constants.NEW_PROJECT_NOISE_DETECTION)
        self.vignetting_correction = QCheckBox()
        self.vignetting_correction.setChecked(gui_constants.NEW_PROJECT_VIGNETTING_CORRECTION)
        self.align_frames = QCheckBox()
        self.align_frames.setChecked(gui_constants.NEW_PROJECT_ALIGN_FRAMES)
        self.balance_frames = QCheckBox()
        self.balance_frames.setChecked(gui_constants.NEW_PROJECT_BALANCE_FRAMES)
        self.bunch_stack = QCheckBox()
        self.bunch_stack.setChecked(gui_constants.NEW_PROJECT_BUNCH_STACK)
        self.bunch_stack.toggled.connect(self.update_bunch_options)
        self.bunch_frames = QSpinBox()
        bunch_frames_range = gui_constants.NEW_PROJECT_BUNCH_FRAMES
        self.bunch_frames.setRange(bunch_frames_range['min'], bunch_frames_range['max'])
        self.bunch_frames.setValue(constants.DEFAULT_FRAMES)
        self.bunch_overlap = QSpinBox()
        bunch_overlap_range = gui_constants.NEW_PROJECT_BUNCH_OVERLAP
        self.bunch_overlap.setRange(bunch_overlap_range['min'], bunch_overlap_range['max'])
        self.bunch_overlap.setValue(constants.DEFAULT_OVERLAP)
        self.focus_stack_pyramid = QCheckBox()
        self.focus_stack_pyramid.setChecked(gui_constants.NEW_PROJECT_FOCUS_STACK_PYRAMID)
        self.focus_stack_depth_map = QCheckBox()
        self.focus_stack_depth_map.setChecked(gui_constants.NEW_PROJECT_FOCUS_STACK_DEPTH_MAP)
        self.multi_layer = QCheckBox()
        self.multi_layer.setChecked(gui_constants.NEW_PROJECT_MULTI_LAYER)

        self.add_bold_label("Select input:")
        self.layout.addRow("Input folder:", container)
        self.add_bold_label("Select actions:")
        if self.expert():
            self.layout.addRow("Automatic noise detection:", self.noise_detection)
            self.layout.addRow("Vignetting correction:", self.vignetting_correction)
        self.layout.addRow("Align layers:", self.align_frames)
        self.layout.addRow("Balance layers:", self.balance_frames)
        self.layout.addRow("Bunch stack:", self.bunch_stack)
        self.layout.addRow("Bunch frames:", self.bunch_frames)
        self.layout.addRow("Bunch frames:", self.bunch_overlap)
        if self.expert():
            self.layout.addRow("Focus stack (pyramid):", self.focus_stack_pyramid)
            self.layout.addRow("Focus stack (depth map):", self.focus_stack_depth_map)
        else:
            self.layout.addRow("Focus stack:", self.focus_stack_pyramid)
            self.layout.addRow("Save multi layer TIFF:", self.multi_layer)

    def update_bunch_options(self, checked):
        self.bunch_frames.setEnabled(checked)
        self.bunch_overlap.setEnabled(checked)

    def accept(self):
        input_folder = self.input_folder.text()
        if not input_folder:
            QMessageBox.warning(self, "Input Required", "Please select an input folder")
            return
        if not os.path.exists(input_folder):
            QMessageBox.warning(self, "Invalid Path", "The specified folder does not exist")
            return
        if not os.path.isdir(input_folder):
            QMessageBox.warning(self, "Invalid Path", "The specified path is not a folder")
            return
        if len(input_folder.split('/')) < 2:
            QMessageBox.warning(self, "Invalid Path", "The path must have a parent folder")
            return
        super().accept()

    def get_input_folder(self):
        return self.input_folder.text()

    def get_noise_detection(self):
        return self.noise_detection.isChecked()

    def get_vignetting_correction(self):
        return self.vignetting_correction.isChecked()

    def get_align_frames(self):
        return self.align_frames.isChecked()

    def get_balance_frames(self):
        return self.balance_frames.isChecked()

    def get_bunch_stack(self):
        return self.bunch_stack.isChecked()

    def get_bunch_frames(self):
        return self.bunch_frames.value()

    def get_bunch_overlap(self):
        return self.bunch_overlap.value()

    def get_focus_stack_pyramid(self):
        return self.focus_stack_pyramid.isChecked()

    def get_focus_stack_depth_map(self):
        return self.focus_stack_depth_map.isChecked()

    def get_multi_layer(self):
        return self.multi_layer.isChecked()
