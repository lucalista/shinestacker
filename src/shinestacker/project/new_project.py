# pylint: disable=C0114, C0115, C0116, E0611, R0915, R0902, R0914, R0911, R0912, R0904, W0718
import os
import numpy as np
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QCheckBox, QSpinBox, QDialog,
                               QMessageBox, QGroupBox, QVBoxLayout, QFormLayout, QSizePolicy)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer
from .. config.gui_constants import gui_constants
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. config.app_config import AppConfig
from .. algorithms.utils import read_img, extension_supported_input
from .. algorithms.stack import get_bunches
from .. gui.folder_file_selection import FolderFileSelectionWidget
from .. gui.base_form_dialog import BaseFormDialog
from .. gui.project_model import ActionConfig

DEFAULT_NO_COUNT_LABEL = " - "


class NewProjectDialog(BaseFormDialog):
    ram_threshold = 4

    def __init__(self, parent=None, initial_path=None):
        super().__init__("New Project", 600, parent)
        self.expert_widgets = []
        self.expert_labels = []
        self.expert_init = AppConfig.get('expert_options')
        self.create_form()
        self.create_ok_cancel()
        self.n_image_files = 0
        self.selected_filenames = []
        if initial_path:
            self.input_widget.set_path(initial_path)
        self.update_expert_visibility()

    def expert(self):
        return self.expert_init

    def add_bold_label(self, label):
        label = QLabel(label)
        label.setStyleSheet("font-weight: bold")
        self.form_layout.addRow(label)

    def create_form(self):
        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        expert_layout = QHBoxLayout()
        expert_layout.setContentsMargins(0, 0, 0, 0)
        expert_label = QLabel("Show expert options:")
        self.expert_cb = QCheckBox()
        self.expert_cb.setChecked(self.expert_init)
        self.expert_cb.stateChanged.connect(self.toggle_expert_options)
        expert_layout.addWidget(expert_label)
        expert_layout.addWidget(self.expert_cb)
        name_row.addStretch()
        name_row.addLayout(expert_layout)
        self.form_layout.addRow(name_row)
        self.input_widget = FolderFileSelectionWidget(AppConfig.get('input_folder_path'))
        self.input_widget.text_changed_connect(self.input_submitted)
        self.noise_detection = self.create_expert_widget(
            QCheckBox(), "noise_detection",
            checked=gui_constants.NEW_PROJECT_NOISE_DETECTION
        )
        self.vignetting_correction = self.create_expert_widget(
            QCheckBox(), "vignetting_correction",
            checked=gui_constants.NEW_PROJECT_VIGNETTING_CORRECTION
        )
        self.align_frames = QCheckBox()
        self.align_frames.setChecked(gui_constants.NEW_PROJECT_ALIGN_FRAMES)
        self.balance_frames = QCheckBox()
        self.balance_frames.setChecked(gui_constants.NEW_PROJECT_BALANCE_FRAMES)
        self.bunch_stack = QCheckBox()
        self.bunch_stack.setChecked(gui_constants.NEW_PROJECT_BUNCH_STACK)
        self.bunch_frames = QSpinBox()
        bunch_frames_range = gui_constants.NEW_PROJECT_BUNCH_FRAMES
        self.bunch_frames.setRange(bunch_frames_range['min'], bunch_frames_range['max'])
        self.bunch_frames.setValue(DEFAULTS['focus_stack_bunch_params']['frames'])
        self.bunch_overlap = QSpinBox()
        bunch_overlap_range = gui_constants.NEW_PROJECT_BUNCH_OVERLAP
        self.bunch_overlap.setRange(bunch_overlap_range['min'], bunch_overlap_range['max'])
        self.bunch_overlap.setValue(DEFAULTS['focus_stack_bunch_params']['overlap'])
        self.bunches_label = QLabel(DEFAULT_NO_COUNT_LABEL)
        self.frames_label = QLabel(DEFAULT_NO_COUNT_LABEL)
        self.update_bunch_options(gui_constants.NEW_PROJECT_BUNCH_STACK)
        self.bunch_stack.toggled.connect(self.update_bunch_options)
        self.bunch_frames.valueChanged.connect(self.update_bunches_label)
        self.bunch_overlap.valueChanged.connect(self.update_bunches_label)
        self.focus_stack_pyramid = QCheckBox()
        self.focus_stack_pyramid.setChecked(gui_constants.NEW_PROJECT_FOCUS_STACK_PYRAMID)
        self.focus_stack_depth_map = self.create_expert_widget(
            QCheckBox(), "focus_stack_depth_map",
            checked=gui_constants.NEW_PROJECT_FOCUS_STACK_DEPTH_MAP
        )
        self.multi_layer = self.create_expert_widget(
            QCheckBox(), "multi_layer",
            checked=gui_constants.NEW_PROJECT_MULTI_LAYER
        )
        step1_group = QGroupBox("1) Select Input")
        step1_layout = QVBoxLayout()
        step1_layout.setContentsMargins(15, 0, 15, 15)
        step1_layout.addWidget(
            QLabel("Select a folder containing all your images, or specific image files."))
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)
        input_label = QLabel("Input:")
        input_label.setFixedWidth(60)
        self.input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_widget)
        frames_layout = QHBoxLayout()
        frames_layout.setContentsMargins(0, 0, 0, 0)
        frames_layout.setSpacing(10)
        frames_label = QLabel("Number of selected frames:")
        frames_label.setFixedWidth(180)
        self.frames_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        frames_layout.addWidget(frames_label)
        frames_layout.addWidget(self.frames_label)
        frames_layout.addStretch()
        step1_layout.addLayout(input_layout)
        step1_layout.addLayout(frames_layout)
        step1_group.setLayout(step1_layout)
        self.form_layout.addRow(step1_group)
        step2_group = QGroupBox("2) Basic Options")
        step2_layout = QFormLayout()
        step2_layout.setContentsMargins(15, 0, 15, 15)
        step2_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        step2_layout.setFormAlignment(Qt.AlignLeft)
        step2_layout.setLabelAlignment(Qt.AlignLeft)
        for widget in [self.noise_detection, self.vignetting_correction, self.align_frames,
                       self.balance_frames, self.bunch_stack, self.bunch_frames,
                       self.bunch_overlap, self.focus_stack_pyramid,
                       self.focus_stack_depth_map, self.multi_layer]:
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        step2_layout.addRow(
            self.create_expert_label("Automatic noise detection:", "noise_detection"),
            self.noise_detection
        )
        step2_layout.addRow(
            self.create_expert_label("Vignetting correction:", "vignetting_correction"),
            self.vignetting_correction
        )
        step2_layout.addRow(
            QLabel("Align frames:"),
            self.align_frames
        )
        step2_layout.addRow(
            QLabel("Balance frames:"),
            self.balance_frames
        )
        step2_layout.addRow(
            QLabel("Create bunches:"),
            self.bunch_stack
        )
        self.bunch_stack.setToolTip(
            "Combine multiple frames into fewer, "
            "high-quality composite frames for easier retouching")
        step2_layout.addRow("Frames per bunch:", self.bunch_frames)
        step2_layout.addRow("Overlap between bunches:", self.bunch_overlap)
        self.bunches_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        step2_layout.addRow("Number of resulting bunches: ", self.bunches_label)
        step2_layout.addRow(
            QLabel("Focus stack (pyramid):"),
            self.focus_stack_pyramid
        )
        step2_layout.addRow(
            self.create_expert_label("Focus stack (depth map):", "focus_stack_depth_map"),
            self.focus_stack_depth_map
        )
        step2_layout.addRow(
            self.create_expert_label("Export as multilayer TIFF:", "multi_layer"),
            self.multi_layer
        )
        step2_group.setLayout(step2_layout)
        self.form_layout.addRow(step2_group)
        step3_group = QGroupBox("3) Confirm")
        step3_layout = QVBoxLayout()
        step3_layout.setContentsMargins(15, 0, 15, 15)
        step3_layout.addWidget(
            QLabel("Click 🆗 to create project with these settings."))
        step3_layout.addWidget(
            QLabel("Toggle 'Show expert options' above for advanced configuration."))
        step3_group.setLayout(step3_layout)
        self.form_layout.addRow(step3_group)
        step4_group = QGroupBox("4) Execute")
        step4_layout = QHBoxLayout()
        step4_layout.setContentsMargins(15, 0, 15, 15)
        step4_layout.addWidget(QLabel("Press ▶️ to run your job."))
        step4_layout.addStretch()
        icon_path = f"{os.path.dirname(__file__)}/ico/shinestacker.png"
        app_icon = QIcon(icon_path)
        icon_pixmap = app_icon.pixmap(80, 80)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignRight)
        step4_layout.addWidget(icon_label)
        step4_group.setLayout(step4_layout)
        self.form_layout.addRow(step4_group)
        for group in [step1_group, step2_group, step3_group, step4_group]:
            group.setStyleSheet(self.group_style)
            group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.form_layout.setFormAlignment(Qt.AlignLeft)
        self.form_layout.setLabelAlignment(Qt.AlignLeft)

    def create_expert_widget(self, widget, tag, checked=False):
        self.expert_widgets.append((widget, tag))
        widget.setChecked(checked)
        return widget

    def create_expert_label(self, text, tag):
        label = QLabel(text)
        self.expert_labels.append((label, tag))
        return label

    def update_expert_visibility(self):
        visible = self.expert_cb.isChecked() if self.expert_cb else self.expert_init
        for widget, _tag in self.expert_widgets:
            widget.setVisible(visible)
        for label, _tag in self.expert_labels:
            label.setVisible(visible)
        QTimer.singleShot(50, self._resize_dialog)

    def toggle_expert_options(self, _state):
        self.update_expert_visibility()

    def _resize_dialog(self):
        content_height = 0
        for group in self.findChildren(QGroupBox):
            content_height += group.sizeHint().height()
        margin = 40
        button_height = 50
        new_height = content_height + button_height + margin
        screen_geo = self.screen().availableGeometry()
        max_height = int(screen_geo.height() * 0.8)
        new_height = min(new_height, max_height)
        current_size = self.size()
        self.resize(current_size.width(), new_height)

    def update_bunch_options(self, checked):
        self.bunch_frames.setEnabled(checked)
        self.bunch_overlap.setEnabled(checked)
        self.update_bunches_label(check_ram=False)

    def update_bunches_label(self, check_ram=True):
        if not self.input_widget.get_path():
            return

        def count_image_files(path):
            if path == '' or not os.path.isdir(path):
                return 0
            count = 0
            for filename in os.listdir(path):
                if extension_supported_input(filename):
                    count += 1
            return count
        if self.input_widget.get_selection_mode() == 'files' and \
                self.input_widget.get_selected_files():
            self.n_image_files = self.input_widget.num_selected_files()
            self.selected_filenames = self.input_widget.get_selected_filenames()
        else:
            self.n_image_files = count_image_files(self.input_widget.get_path())
            self.selected_filenames = []
        if self.n_image_files == 0:
            self.bunches_label.setText(DEFAULT_NO_COUNT_LABEL)
            self.frames_label.setText(DEFAULT_NO_COUNT_LABEL)
            return
        self.frames_label.setText(f"{self.n_image_files}")
        if self.bunch_stack.isChecked():
            bunches = get_bunches(list(range(self.n_image_files)),
                                  self.bunch_frames.value(),
                                  self.bunch_overlap.value())
            self.bunches_label.setText(f"{max(1, len(bunches))}")
        else:
            self.bunches_label.setText(DEFAULT_NO_COUNT_LABEL)
        if check_ram and self.n_image_files > 0 and not self.bunch_stack.isChecked():
            n_gbytes, _width, _height, _n_bits = self.compute_required_ram()
            if n_gbytes > self.ram_threshold:
                self.bunch_stack.setChecked(True)

    def compute_required_ram(self):
        selection_mode = self.input_widget.get_selection_mode()
        selected_files = self.input_widget.get_selected_files()
        if selection_mode == 'files' and selected_files:
            file_path = selected_files[0]
        else:
            path = self.input_widget.get_path()
            files = os.listdir(path)
            file_path = None
            for filename in files:
                full_path = os.path.join(path, filename)
                if extension_supported_input(full_path):
                    file_path = full_path
                    break
        if file_path is None:
            QMessageBox.warning(
                self, "Invalid input", "Could not find images in the selected path")
            return 0, 0, 0, 0
        try:
            img = read_img(file_path)
        except Exception as e:
            QMessageBox.warning(
                self, "Invalid input", f"Could not read images file {file_path}:\n{str(e)}")
            return 0, 0, 0, 0
        if img is None:
            QMessageBox.warning(
                self, "Invalid input", f"Could not read images file {file_path}")
            return 0, 0, 0, 0
        height, width = img.shape[:2]
        n_bytes = 1 if img.dtype == np.uint8 else 2
        n_bits = 8 if img.dtype == np.uint8 else 16
        n_gbytes = 3.0 * n_bytes * height * width * self.n_image_files / constants.ONE_GIGA
        return n_gbytes, width, height, n_bits

    def input_submitted(self):
        self.update_bunches_label()
        self.ok_button.setFocus()

    def accept(self):
        input_path = self.input_widget.get_path()
        selection_mode = self.input_widget.get_selection_mode()
        selected_files = self.input_widget.get_selected_files()
        if not input_path:
            QMessageBox.warning(self, "Input Required", "Please select an input folder or files")
            return
        if selection_mode == 'files':
            if not selected_files:
                QMessageBox.warning(self, "Invalid Selection", "No files selected")
                return
            for file_path in selected_files:
                if not os.path.exists(file_path):
                    QMessageBox.warning(self, "Invalid Path",
                                        f"The file {file_path} does not exist")
                    return
        else:
            if not os.path.exists(input_path):
                QMessageBox.warning(self, "Invalid Path", "The specified folder does not exist")
                return
            if not os.path.isdir(input_path):
                QMessageBox.warning(self, "Invalid Path", "The specified path is not a folder")
                return
        parent_dir = os.path.dirname(input_path)
        if not parent_dir:
            parent_dir = input_path
        if len(parent_dir.split('/')) < 2:
            QMessageBox.warning(self, "Invalid Path", "The path must have a parent folder")
            return
        if self.n_image_files > 0 and not self.bunch_stack.isChecked():
            n_gbytes, width, height, n_bits = self.compute_required_ram()
            if n_gbytes > self.ram_threshold and not self.bunch_stack.isChecked():
                msg = QMessageBox()
                msg.setStyleSheet("""
                    QMessageBox {
                        min-width: 600px;
                        font-weight: bold;
                        font-size: 14px;
                    }
                    QMessageBox QLabel#qt_msgbox_informativelabel {
                        font-weight: normal;
                        font-size: 14px;
                        color: #555555;
                    }
                """)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Too many frames")
                msg.setText(
                    f"You selected {self.n_image_files} images "
                    f"with resolution {width}×{height} pixels, {n_bits} bits depth. "
                    "Processing may require a significant amount "
                    "of memory and temporary disk space.\n\n"
                    "Continue anyway?")
                msg.setInformativeText(
                    '<b>For better performance, set a scratch disk folder '
                    'on a fast drive:</b><br>'
                    '➡️ Go to "ShineStacker" → "Settings" → "Scratch disk folder".<br>'
                    '💡 Using an SSD with ample free space will speed up processing.<br><br>'
                    '<b>Reduce processing load:</b><br>'
                    '✅ Check "Create bunches" in the project wizard to combine frames.')
                msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                msg.setDefaultButton(QMessageBox.Cancel)
                if msg.exec_() != QMessageBox.Ok:
                    return
        super().accept()

    def get_input_folder(self):
        return self.input_widget.get_path()

    def get_selected_files(self):
        return self.input_widget.get_selected_files()

    def get_selected_filenames(self):
        return self.input_widget.get_selected_filenames()

    def get_selection_mode(self):
        return self.input_widget.get_selection_mode()

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


def fill_new_project(project, parent, initial_path=None):
    jobs = project.jobs
    dialog = NewProjectDialog(parent, initial_path=initial_path)
    if dialog.exec() == QDialog.Accepted:
        input_folder = dialog.get_input_folder()
        working_path, input_path = os.path.split(os.path.normpath(input_folder))
        base_name = input_path if input_path else 'shinestacker'
        selected_filenames = dialog.get_selected_filenames()
        if dialog.get_noise_detection():
            job_noise = ActionConfig(
                constants.ACTION_JOB,
                {'name': 'noise-job', 'working_path': working_path,
                 'input_path': input_path})
            noise_detection_name = 'detect-noise'
            noise_detection = ActionConfig(constants.ACTION_NOISEDETECTION,
                                           {'name': noise_detection_name})
            job_noise.add_sub_action(noise_detection)
            jobs.append(job_noise)
        job_params = {
            'name': f'{base_name}-stack-job',
            'working_path': working_path,
            'input_path': input_path
        }
        if len(selected_filenames) > 0:
            job_params['input_filepaths'] = selected_filenames
        job = ActionConfig(constants.ACTION_JOB, job_params)
        preprocess_name = ''
        if dialog.get_noise_detection() or dialog.get_vignetting_correction() or \
           dialog.get_align_frames() or dialog.get_balance_frames():
            preprocess_name = f'{base_name}-preprocess'
            combo_action = ActionConfig(
                constants.ACTION_COMBO, {'name': preprocess_name})
            if dialog.get_noise_detection():
                mask_noise = ActionConfig(
                    constants.ACTION_MASKNOISE,
                    {'name': 'mask-noise',
                     'noise_mask':
                        os.path.join(noise_detection_name,
                                     DEFAULTS['noise_detection_params']['noise_map_filename'])})
                combo_action.add_sub_action(mask_noise)
            if dialog.get_vignetting_correction():
                vignetting = ActionConfig(
                    constants.ACTION_VIGNETTING, {'name': 'vignetting'})
                combo_action.add_sub_action(vignetting)
            if dialog.get_align_frames():
                align = ActionConfig(
                    constants.ACTION_ALIGNFRAMES, {'name': 'align'})
                combo_action.add_sub_action(align)
            if dialog.get_balance_frames():
                balance = ActionConfig(
                    constants.ACTION_BALANCEFRAMES, {'name': 'balance'})
                combo_action.add_sub_action(balance)
            job.add_sub_action(combo_action)
        if dialog.get_bunch_stack():
            bunch_stack_name = f'{base_name}-bunches'
            bunch_stack = ActionConfig(
                constants.ACTION_FOCUSSTACKBUNCH,
                {'name': bunch_stack_name, 'frames': dialog.get_bunch_frames(),
                 'overlap': dialog.get_bunch_overlap()})
            job.add_sub_action(bunch_stack)
        stack_input_path = bunch_stack_name if dialog.get_bunch_stack() else preprocess_name
        if dialog.get_focus_stack_pyramid():
            focus_pyramid_name = f'{base_name}-focus-stack-pyramid'
            focus_pyramid_params = {'name': focus_pyramid_name,
                                    'stacker': constants.STACK_ALGO_PYRAMID,
                                    'exif_path': input_path}
            if dialog.get_focus_stack_depth_map():
                focus_pyramid_params['input_path'] = stack_input_path
            focus_pyramid = ActionConfig(constants.ACTION_FOCUSSTACK, focus_pyramid_params)
            job.add_sub_action(focus_pyramid)
        if dialog.get_focus_stack_depth_map():
            focus_depth_map_name = f'{base_name}-focus-stack-depth-map'
            focus_depth_map_params = {'name': focus_depth_map_name,
                                      'stacker': constants.STACK_ALGO_DEPTH_MAP,
                                      'exif_path': input_path}
            if dialog.get_focus_stack_pyramid():
                focus_depth_map_params['input_path'] = stack_input_path
            focus_depth_map = ActionConfig(constants.ACTION_FOCUSSTACK, focus_depth_map_params)
            job.add_sub_action(focus_depth_map)
        if dialog.get_multi_layer():
            multi_input_path = []
            if dialog.get_focus_stack_pyramid():
                multi_input_path.append(focus_pyramid_name)
            if dialog.get_focus_stack_depth_map():
                multi_input_path.append(focus_depth_map_name)
            if dialog.get_bunch_stack():
                multi_input_path.append(bunch_stack_name)
            elif preprocess_name:
                multi_input_path.append(preprocess_name)
            multi_layer = ActionConfig(
                constants.ACTION_MULTILAYER,
                {'name': f'{base_name}-multi-layer',
                 'input_path': constants.PATH_SEPARATOR.join(multi_input_path)})
            job.add_sub_action(multi_layer)
        jobs.append(job)
        return True
    return False
