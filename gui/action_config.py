from PySide6.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QFileDialog, QLabel, QComboBox,
                               QMessageBox, QSizePolicy, QStackedWidget, QDialog, QFormLayout,
                               QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QTreeView, QAbstractItemView, QListView)
from PySide6.QtCore import Qt
from config.constants import constants
from gui.project_model import ActionConfig
from abc import ABC, abstractmethod
from typing import Dict, Any
import os.path
from focus_stack.stack import DEFAULT_FRAMES, DEFAULT_OVERLAP


FIELD_TEXT = 'text'
FIELD_ABS_PATH = 'abs_path'
FIELD_REL_PATH = 'rel_path'
FIELD_FLOAT = 'float'
FIELD_INT = 'int'
FIELD_INT_TUPLE = 'int_tuple'
FIELD_BOOL = 'bool'
FIELD_COMBO = 'combo'
FIELD_TYPES = [FIELD_TEXT, FIELD_ABS_PATH, FIELD_REL_PATH, FIELD_FLOAT,
               FIELD_INT, FIELD_INT_TUPLE, FIELD_BOOL, FIELD_COMBO]


class ActionConfigurator(ABC):
    @abstractmethod
    def create_form(self, layout: QFormLayout, params: Dict[str, Any]):
        pass

    @abstractmethod
    def update_params(self, params: Dict[str, Any]):
        pass


class FieldBuilder:
    def __init__(self, layout, action):
        self.layout = layout
        self.action = action
        self.fields = {}

    def add_field(self, tag: str, field_type: str, label: str,
                  required: bool = False, add_to_layout=None, **kwargs):
        if field_type == FIELD_TEXT:
            widget = self.create_text_field(tag, **kwargs)
        elif field_type == FIELD_ABS_PATH:
            widget = self.create_abs_path_field(tag, **kwargs)
        elif field_type == FIELD_REL_PATH:
            widget = self.create_rel_path_field(tag, **kwargs)
        elif field_type == FIELD_FLOAT:
            widget = self.create_float_field(tag, **kwargs)
        elif field_type == FIELD_INT:
            widget = self.create_int_field(tag, **kwargs)
        elif field_type == FIELD_INT_TUPLE:
            widget = self.create_int_tuple_field(tag, **kwargs)
        elif field_type == FIELD_BOOL:
            widget = self.create_bool_field(tag, **kwargs)
        elif field_type == FIELD_COMBO:
            widget = self.create_combo_field(tag, **kwargs)
        else:
            raise ValueError(f"Unknown field type: {field_type}")
        self.fields[tag] = {
            'widget': widget,
            'type': field_type,
            'label': label,
            'required': required,
            **kwargs
        }
        if add_to_layout is None:
            add_to_layout = self.layout
        add_to_layout.addRow(f"{label}:", widget)
        return widget

    def get_path_widget(self, widget):
        return widget.layout().itemAt(0).widget()

    def get_working_path(self):
        if 'working_path' in self.fields.keys():
            working_path = self.get_path_widget(self.fields['working_path']['widget']).text()
            if working_path != '':
                return working_path
        parent = self.action.parent
        while parent is not None:
            if 'working_path' in parent.params.keys() and parent.params['working_path'] != '':
                return parent.params['working_path']
            parent = parent.parent
        else:
            return ''

    def update_params(self, params: Dict[str, Any]) -> bool:
        for tag, field in self.fields.items():
            if field['type'] == FIELD_TEXT:
                params[tag] = field['widget'].text()
            elif field['type'] in (FIELD_ABS_PATH, FIELD_REL_PATH):
                params[tag] = self.get_path_widget(field['widget']).text()
            elif field['type'] == FIELD_FLOAT:
                params[tag] = field['widget'].value()
            elif field['type'] == FIELD_BOOL:
                params[tag] = field['widget'].isChecked()
            elif field['type'] == FIELD_INT:
                params[tag] = field['widget'].value()
            elif field['type'] == FIELD_INT_TUPLE:
                params[tag] = [field['widget'].layout().itemAt(1 + i * 2).widget().value() for i in range(field['size'])]
            elif field['type'] == FIELD_COMBO:
                values = field.get('values', None)
                options = field.get('options', None)
                text = field['widget'].currentText()
                if values is not None and options is not None:
                    text = {k: v for k, v in zip(options, values)}[text]
                params[tag] = text
            if field['required'] and not params[tag]:
                required = True
                if tag == 'working_path' and self.get_working_path() != '':
                    required = False
                if required:
                    QMessageBox.warning(None, "Error", f"{field['label']} is required")
                    return False
            if field['type'] == FIELD_REL_PATH and 'working_path' in params:
                try:
                    working_path = self.get_working_path()
                    abs_path = os.path.normpath(os.path.join(working_path, params[tag]))
                    if not abs_path.startswith(os.path.normpath(working_path)):
                        QMessageBox.warning(None, "Invalid Path",
                                            f"{field['label']} must be a subdirectory of working path")
                        return False
                    if field.get('must_exist', False):
                        paths = [abs_path]
                        if field.get('multiple_entries', False):
                            paths = abs_path.split(constants.PATH_SEPARATOR)
                        for p in paths:
                            p = p.strip()
                            if not os.path.exists(p):
                                QMessageBox.warning(None, "Invalid Path",
                                                    f"{field['label']} {p} does not exist")
                                return False
                except Exception as e:
                    QMessageBox.warning(None, "Error", f"Invalid path: {str(e)}")
                    return False
        return True

    def create_text_field(self, tag, **kwargs):
        value = self.action.params.get(tag, '')
        edit = QLineEdit(value)
        edit.setPlaceholderText(kwargs.get('placeholder', ''))
        return edit

    def create_abs_path_field(self, tag, **kwargs):
        value = self.action.params.get(tag, '')
        edit = QLineEdit(value)
        edit.setPlaceholderText(kwargs.get('placeholder', ''))
        button = QPushButton("Browse...")

        def browse():
            path = QFileDialog.getExistingDirectory(None, f"Select {tag.replace('_', ' ')}")
            if path:
                edit.setText(path)
        button.clicked.connect(browse)
        button.setAutoDefault(False)
        layout = QHBoxLayout()
        layout.addWidget(edit)
        layout.addWidget(button)
        layout.setContentsMargins(0, 0, 0, 0)
        container = QWidget()
        container.setLayout(layout)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return container

    def create_rel_path_field(self, tag, **kwargs):
        value = self.action.params.get(tag, kwargs.get('default', ''))
        edit = QLineEdit(value)
        edit.setPlaceholderText(kwargs.get('placeholder', ''))
        button = QPushButton("Browse...")
        path_type = kwargs.get('path_type', 'directory')
        label = kwargs.get('label', tag).replace('_', ' ')

        if kwargs.get('multiple_entries', False):
            def browse():
                working_path = self.get_working_path()
                if not working_path:
                    QMessageBox.warning(None, "Error", "Please set working path first")
                    return

                if path_type == 'directory':
                    dialog = QFileDialog()
                    dialog.setWindowTitle(f"Select {label} (multiple selection allowed)")
                    dialog.setDirectory(working_path)

                    # Configurazione per la selezione di directory multiple
                    dialog.setFileMode(QFileDialog.Directory)
                    dialog.setOption(QFileDialog.DontUseNativeDialog, True)
                    dialog.setOption(QFileDialog.ShowDirsOnly, True)

                    # Abilita esplicitamente la selezione multipla
                    if hasattr(dialog, 'setSupportedSchemes'):
                        dialog.setSupportedSchemes(['file'])

                    # Modifica la vista per permettere selezione multipla
                    tree_view = dialog.findChild(QTreeView)
                    if tree_view:
                        tree_view.setSelectionMode(QAbstractItemView.ExtendedSelection)

                    list_view = dialog.findChild(QListView)
                    if list_view:
                        list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)

                    if dialog.exec_():
                        paths = dialog.selectedFiles()
                        rel_paths = []
                        for path in paths:
                            try:
                                rel_path = os.path.relpath(path, working_path)
                                if rel_path.startswith('..'):
                                    QMessageBox.warning(None, "Invalid Path",
                                                        f"{label} must be a subdirectory of working path")
                                    return
                                rel_paths.append(rel_path)
                            except ValueError:
                                QMessageBox.warning(None, "Error", "Could not compute relative path")
                                return

                        if rel_paths:
                            edit.setText(constants.PATH_SEPARATOR.join(rel_paths))

                elif path_type == 'file':
                    paths, _ = QFileDialog.getOpenFileNames(None, f"Select {label}", working_path)
                    if paths:
                        rel_paths = []
                        for path in paths:
                            try:
                                rel_path = os.path.relpath(path, working_path)
                                if rel_path.startswith('..'):
                                    QMessageBox.warning(None, "Invalid Path",
                                                        f"{label} must be within working path")
                                    return
                                rel_paths.append(rel_path)
                            except ValueError:
                                QMessageBox.warning(None, "Error", "Could not compute relative path")
                                return
                            edit.setText(constants.PATH_SEPARATOR.join(rel_paths))
                else:
                    raise ValueError("path_type must be 'directory' (default) or 'file'.")
        else:
            def browse():
                working_path = self.get_working_path()
                if not working_path:
                    QMessageBox.warning(None, "Error", "Please set working path first")
                    return
                if path_type == 'directory':
                    dialog = QFileDialog()
                    dialog.setDirectory(working_path)
                    path = dialog.getExistingDirectory(None, f"Select {label}", working_path)
                elif path_type == 'file':
                    dialog = QFileDialog()
                    dialog.setDirectory(working_path)
                    path = dialog.getOpenFileName(None, f"Select {label}", working_path)[0]
                else:
                    raise ValueError("path_type must be 'directory' (default) or 'file'.")
                if path:
                    try:
                        rel_path = os.path.relpath(path, working_path)
                        if rel_path.startswith('..'):
                            QMessageBox.warning(None, "Invalid Path",
                                                f"{label} must be a subdirectory of working path")
                            return
                        edit.setText(rel_path)
                    except ValueError:
                        QMessageBox.warning(None, "Error", "Could not compute relative path")

        button.clicked.connect(browse)
        button.setAutoDefault(False)
        layout = QHBoxLayout()
        layout.addWidget(edit)
        layout.addWidget(button)
        layout.setContentsMargins(0, 0, 0, 0)
        container = QWidget()
        container.setLayout(layout)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return container

    def create_float_field(self, tag, default=0.0, min=0.0, max=1.0, step=0.1, **kwargs):
        spin = QDoubleSpinBox()
        spin.setValue(self.action.params.get(tag, default))
        spin.setRange(min, max)
        spin.setSingleStep(step)
        return spin

    def create_int_field(self, tag, default=0, min=0, max=100, **kwargs):
        spin = QSpinBox()
        spin.setRange(min, max)
        spin.setValue(self.action.params.get(tag, default))
        return spin

    def create_int_tuple_field(self, tag, size=1, default=[0] * 100, min=[0] * 100, max=[100] * 100, **kwargs):
        layout = QHBoxLayout()
        spins = [QSpinBox() for i in range(size)]
        labels = kwargs.get('labels', ('') * size)
        value = self.action.params.get(tag, default)
        for i, spin in enumerate(spins):
            spin.setRange(min[i], max[i])
            spin.setValue(value[i])
            spin.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            label = QLabel(labels[i] + ":")
            label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            layout.addWidget(label)
            layout.addWidget(spin)
            layout.setStretch(layout.count() - 1, 1)
        layout.setContentsMargins(0, 0, 0, 0)
        container = QWidget()
        container.setLayout(layout)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return container

    def create_combo_field(self, tag, options=None, default=None, **kwargs):
        options = options or []
        values = kwargs.get('values', None)
        combo = QComboBox()
        combo.addItems(options)
        value = self.action.params.get(tag, default or options[0] if options else '')
        if values is not None and len(options) > 0:
            value = {k: v for k, v in zip(values, options)}.get(value, value)
        combo.setCurrentText(value)
        return combo

    def create_bool_field(self, tag, default=False, **kwargs):
        checkbox = QCheckBox()
        checkbox.setChecked(self.action.params.get(tag, default))
        return checkbox


class ActionConfigDialog(QDialog):
    def __init__(self, action: ActionConfig, parent=None):
        super().__init__(parent)
        self.action = action
        self.setWindowTitle(f"Configure {action.type_name}")
        self.resize(500, self.height())
        self.configurator = self.get_configurator(action.type_name)
        self.layout = QFormLayout(self)
        self.layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        self.layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.layout.setLabelAlignment(Qt.AlignLeft)
        self.configurator.create_form(self.layout, action)
        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.setFocus()
        cancel_button = QPushButton("Cancel")
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        self.layout.addRow(button_box)
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

    def get_configurator(self, action_type: str) -> ActionConfigurator:
        configurators = {
            constants.ACTION_JOB: JobConfigurator(),
            constants.ACTION_COMBO: CombinedActionsConfigurator(),
            constants.ACTION_NOISEDETECTION: NoiseDetectionConfigurator(),
            constants.ACTION_FOCUSSTACK: FocusStackConfigurator(),
            constants.ACTION_FOCUSSTACKBUNCH: FocusStackBunchConfigurator(),
            constants.ACTION_MULTILAYER: MultiLayerConfigurator(),
            constants.ACTION_MASKNOISE: MaskNoiseConfigurator(),
            constants.ACTION_VIGNETTING: VignettingConfigurator(),
            constants.ACTION_ALIGNFRAMES: AlignFramesConfigurator(),
            constants.ACTION_BALANCEFRAMES: BalanceFramesConfigurator(),
        }
        return configurators.get(action_type, DefaultActionConfigurator())

    def accept(self):
        if self.configurator.update_params(self.action.params):
            super().accept()


class NoNameActionConfigurator(ActionConfigurator):
    def update_params(self, params):
        return self.builder.update_params(params)

    def add_bold_label(self, label):
        label = QLabel(label)
        label.setStyleSheet("font-weight: bold")
        self.builder.layout.addRow(label)


class DefaultActionConfigurator(NoNameActionConfigurator):
    def create_form(self, layout, action, tag='Action'):
        self.builder = FieldBuilder(layout, action)
        self.builder.add_field('name', FIELD_TEXT, f'{tag} name', required=True)


class JobConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action, "Job")
        self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=True)
        self.builder.add_field('input_path', FIELD_REL_PATH, 'Input path', required=False,
                               must_exist=True, placeholder='relative to working path')


class NoiseDetectionConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=True,
                               placeholder='inherit from job')
        self.builder.add_field('input_path', FIELD_REL_PATH, 'Input path (separate by {constants.PATH_SEPARATOR})', required=False,
                               multiple_entries=True, placeholder='relative to working path')
        self.builder.add_field('output_path', FIELD_REL_PATH, 'Output path', required=False,
                               placeholder='relative to working path')
        self.builder.add_field('channel_thresholds', FIELD_INT_TUPLE, 'Noise threshold', required=False, size=3,
                               default=constants.DEFAULT_CHANNEL_THRESHOLDS, labels=constants.RGB_LABELS, min=[1] * 3, max=[1000] * 3)
        self.builder.add_field('blur_size', FIELD_INT, 'Blur size (px)', required=False,
                               default=constants.DEFAULT_BLUR_SIZE, min=1, max=50)
        self.builder.add_field('file_name', FIELD_TEXT, 'File name', required=False,
                               default="hot", placeholder="hot")
        self.add_bold_label("Miscellanea:")
        self.builder.add_field('plot_histograms', FIELD_BOOL, 'Plot histograms', required=False, default=False)
        self.builder.add_field('plot_path', FIELD_REL_PATH, 'Plots path', required=False, default=constants.DEFAULT_PLOTS_PATH,
                               placeholder='relative to working path')
        self.builder.add_field('plot_range', FIELD_INT_TUPLE, 'Plot range', required=False, size=2,
                               default=constants.DEFAULT_NOISE_PLOT_RANGE, labels=['min', 'max'], min=[0] * 2, max=[1000] * 2)


class FocusStackBaseConfigurator(DefaultActionConfigurator):
    ENERGY_OPTIONS = ['Laplacian', 'Sobel']
    MAP_TYPE_OPTIONS = ['Average', 'Maximum']

    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=True)
        self.builder.add_field('input_path', FIELD_REL_PATH, 'Input path', required=False,
                               placeholder='relative to working path')
        self.builder.add_field('output_path', FIELD_REL_PATH, 'Output path', required=False,
                               placeholder='relative to working path')
        self.builder.add_field('scratch_output_dir', FIELD_BOOL, 'Scratch output dir.',
                               required=False, default=True)
        self.builder.add_field('plot_stack', FIELD_BOOL, 'Plot stack', required=False, default=False)

    def common_fields(self, layout, action):
        self.builder.add_field('denoise', FIELD_FLOAT, 'Denoise', required=False,
                               default=0, min=0, max=10)
        self.add_bold_label("Stacking algorithm:")
        combo = self.builder.add_field('stacker', FIELD_COMBO, 'Stacking algorithm', required=True,
                                       options=['Pyramid', 'Depth map'], default='Pyramid')
        q_pyramid, q_depthmap = QWidget(), QWidget()
        for q in [q_pyramid, q_depthmap]:
            layout = QFormLayout()
            layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
            layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
            layout.setLabelAlignment(Qt.AlignLeft)
            q.setLayout(layout)
        stacked = QStackedWidget()
        stacked.addWidget(q_pyramid)
        stacked.addWidget(q_depthmap)

        def change():
            text = combo.currentText()
            if text == 'Pyramid':
                stacked.setCurrentWidget(q_pyramid)
            elif text == 'Depth map':
                stacked.setCurrentWidget(q_depthmap)
        change()
        self.builder.add_field('pyramid_min_size', FIELD_INT, 'Minimum size (px)',
                               required=False, add_to_layout=q_pyramid.layout(),
                               default=constants.DEFAULT_PY_MIN_SIZE, min=2, max=256)
        self.builder.add_field('pyramid_kernel_size', FIELD_INT, 'Kernel size (px)',
                               required=False, add_to_layout=q_pyramid.layout(),
                               default=constants.DEFAULT_PY_KERNEL_SIZE, min=3, max=21)
        self.builder.add_field('pyramid_gen_kernel', FIELD_FLOAT, 'Gen. kernel',
                               required=False, add_to_layout=q_pyramid.layout(),
                               default=constants.DEFAULT_PY_GEN_KERNEL, min=0.0, max=2.0)
        self.builder.add_field('depthmap_energy', FIELD_COMBO, 'Energy', required=False,
                               add_to_layout=q_depthmap.layout(),
                               options=self.ENERGY_OPTIONS, values=constants.VALID_DM_ENERGY,
                               default={k: v for k, v in
                                        zip(constants.VALID_DM_ENERGY, self.ENERGY_OPTIONS)}[constants.DEFAULT_DM_ENERGY])
        self.builder.add_field('map_type', FIELD_COMBO, 'Map type', required=False,
                               add_to_layout=q_depthmap.layout(),
                               options=self.MAP_TYPE_OPTIONS, values=constants.VALID_DM_MAP,
                               default={k: v for k, v in
                                        zip(constants.VALID_DM_MAP, self.MAP_TYPE_OPTIONS)}[constants.DEFAULT_DM_MAP])
        self.builder.add_field('depthmap_kernel_size', FIELD_INT, 'Kernel size (px)',
                               required=False, add_to_layout=q_depthmap.layout(),
                               default=constants.DEFAULT_DM_KERNEL_SIZE, min=3, max=21)
        self.builder.add_field('depthmap_blur_size', FIELD_INT, 'Blurl size (px)',
                               required=False, add_to_layout=q_depthmap.layout(),
                               default=constants.DEFAULT_DM_BLUR_SIZE, min=1, max=21)
        self.builder.add_field('depthmap_smooth_size', FIELD_INT, 'Smooth size (px)',
                               required=False, add_to_layout=q_depthmap.layout(),
                               default=constants.DEFAULT_DM_SMOOTH_SIZE, min=1, max=256)
        self.builder.layout.addRow(stacked)
        combo.currentIndexChanged.connect(change)


class FocusStackConfigurator(FocusStackBaseConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.builder.add_field('exif_path', FIELD_REL_PATH, 'Exif data path', required=False,
                               placeholder='relative to working path')
        self.builder.add_field('postfix', FIELD_TEXT, 'Ouptut filename postfix', required=False,
                               default="_stack", placeholder="_stack")
        super().common_fields(layout, action)


class FocusStackBunchConfigurator(FocusStackBaseConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.builder.add_field('frames', FIELD_INT, 'Frames', required=False,
                               default=DEFAULT_FRAMES, min=1, max=100)
        self.builder.add_field('overlap', FIELD_INT, 'Overlapping frames', required=False,
                               default=DEFAULT_OVERLAP, min=0, max=100)
        super().common_fields(layout, action)


class MultiLayerConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=True)
        self.builder.add_field('input_path', FIELD_REL_PATH, 'Input path (separate by {constants.PATH_SEPARATOR})', required=False,
                               multiple_entries=True, placeholder='relative to working path')
        self.builder.add_field('output_path', FIELD_REL_PATH, 'Output path', required=False,
                               placeholder='relative to working path')
        self.builder.add_field('exif_path', FIELD_REL_PATH, 'Exif data path', required=False,
                               placeholder='relative to working path')
        self.builder.add_field('scratch_output_dir', FIELD_BOOL, 'Scratch output dir.',
                               required=False, default=True)


class CombinedActionsConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        DefaultActionConfigurator.create_form(self, layout, action)
        self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=True)
        self.builder.add_field('input_path', FIELD_REL_PATH, 'Input path', required=False,
                               must_exist=True, placeholder='relative to working path')
        self.builder.add_field('output_path', FIELD_REL_PATH, 'Output path', required=False,
                               placeholder='relative to working path')
        self.builder.add_field('scratch_output_dir', FIELD_BOOL, 'Scratch output dir.',
                               required=False, default=True)
        self.builder.add_field('plot_path', FIELD_REL_PATH, 'Plots path', required=False, default="plots",
                               placeholder='relative to working path')
        self.builder.add_field('resample', FIELD_INT, 'Resample frame stack', required=False,
                               default=1, min=1, max=100)
        self.builder.add_field('ref_idx', FIELD_INT, 'Reference frame index', required=False,
                               default=-1, min=-1, max=1000)
        self.builder.add_field('step_process', FIELD_BOOL, 'Step process', required=False, default=True)


class MaskNoiseConfigurator(NoNameActionConfigurator):
    def create_form(self, layout, action):
        DefaultActionConfigurator.create_form(self, layout, action)
        self.builder.add_field('noise_mask', FIELD_REL_PATH, 'Noise mask file', required=False,
                               path_type='file', must_exist=True,
                               default=constants.DEFAULT_NOISE_MAP_FILENAME, placeholder=constants.DEFAULT_NOISE_MAP_FILENAME)
        self.builder.add_field('kernel_size', FIELD_INT, 'Kernel size', required=False,
                               default=constants.DEFAULT_MN_KERNEL_SIZE, min=1, max=10)
        self.builder.add_field('method', FIELD_COMBO, 'Interpolation method', required=False,
                               options=['Mean', 'Median'], default='Mean')


class VignettingConfigurator(NoNameActionConfigurator):
    def create_form(self, layout, action):
        DefaultActionConfigurator.create_form(self, layout, action)
        self.builder.add_field('r_steps', FIELD_INT, 'Radial steps', required=False,
                               default=constants.DEFAULT_R_STEPS, min=1, max=1000)
        self.builder.add_field('black_threshold', FIELD_INT, 'Black intensity threshold', required=False,
                               default=constants.DEFAULT_BLACK_THRESHOLD, min=0, max=1000)
        self.builder.add_field('max_correction', FIELD_FLOAT, 'Max. correction', required=False,
                               default=constants.DEFAULT_MAX_CORRECTION, min=0, max=1, step=0.05)
        self.add_bold_label("Miscellanea:")
        self.builder.add_field('plot_correction', FIELD_BOOL, 'Plot correction', required=False, default=False)
        self.builder.add_field('plot_summary', FIELD_BOOL, 'Plot summary', required=False, default=False)
        self.builder.add_field('apply_correction', FIELD_BOOL, 'Apply correction', required=False, default=True)


class AlignFramesConfigurator(NoNameActionConfigurator):
    BORDER_MODE_OPTIONS = ['Constant', 'Replicate', 'Replicate and blur']
    TRANSFORM_OPTIONS = ['Rigid', 'Homography']
    MATCHING_METHOD_OPTIONS = ['K-nearest neighbors', 'Hamming distance']

    def create_form(self, layout, action):
        DefaultActionConfigurator.create_form(self, layout, action)
        self.add_bold_label("Feature identification:")
        self.builder.add_field('detector', FIELD_COMBO, 'Detector', required=False,
                               options=['SIFT', 'ORB', 'SURF', 'AKAZE'], default=constants.DEFAULT_DETECTOR)
        self.builder.add_field('descriptor', FIELD_COMBO, 'Descriptor', required=False,
                               options=['SIFT', 'ORB', 'AKAZE'], default=constants.DEFAULT_DESCRIPTOR)
        self.add_bold_label("Feature matching:")
        self.builder.add_field('method', FIELD_COMBO, 'Method', required=False,
                               options=self.MATCHING_METHOD_OPTIONS, values=constants.VALID_MATCHING_METHODS,
                               default=constants.DEFAULT_MATCHING_METHOD)
        self.builder.add_field('flann_idx_kdtree', FIELD_INT, 'Flann idx kdtree', required=False,
                               default=constants.DEFAULT_FLANN_IDX_KDTREE, min=0, max=10)
        self.builder.add_field('flann_trees', FIELD_INT, 'Flann trees', required=False,
                               default=constants.DEFAULT_FLANN_TREES, min=0, max=10)
        self.builder.add_field('flann_checks', FIELD_INT, 'Flann checks', required=False,
                               default=constants.DEFAULT_FLANN_CHECKS, min=0, max=1000)
        self.builder.add_field('threshold', FIELD_FLOAT, 'Threshold', required=False,
                               default=constants.DEFAULT_ALIGN_THRESHOLD, min=0, max=1, step=0.05)
        self.add_bold_label("Transform:")
        self.builder.add_field('transform', FIELD_COMBO, 'Transform', required=False,
                               options=self.TRANSFORM_OPTIONS, values=constants.VALID_TRANSFORMS,
                               default=constants.DEFAULT_TRANSFORM)
        self.builder.add_field('rans_threshold', FIELD_FLOAT, 'Homography RANS threshold', required=False,
                               default=constants.DEFAULT_RANS_THRESHOLD, min=0, max=20, step=0.1)
        self.add_bold_label("Border:")
        self.builder.add_field('border_mode', FIELD_COMBO, 'Border mode', required=False,
                               options=self.BORDER_MODE_OPTIONS, values=constants.VALID_BORDER_MODES,
                               default=constants.DEFAULT_BORDER_MODE)
        self.builder.add_field('border_value', FIELD_INT_TUPLE, 'Border value (if constant)', required=False, size=4,
                               default=constants.DEFAULT_BORDER_VALUE, labels=constants.RGBA_LABELS,
                               min=constants.DEFAULT_BORDER_VALUE, max=[255] * 4)
        self.builder.add_field('border_blur', FIELD_FLOAT, 'Border blur', required=False,
                               default=constants.DEFAULT_BORDER_BLUR, min=0, max=1000, step=1)
        self.add_bold_label("Miscellanea:")
        self.builder.add_field('plot_summary', FIELD_BOOL, 'Plot summary', required=False, default=False)
        self.builder.add_field('plot_matches', FIELD_BOOL, 'Plot matches', required=False, default=False)


class BalanceFramesConfigurator(NoNameActionConfigurator):
    CORRECTION_MAP_OPTIONS = ['Linear', 'Gamma', 'Match histograms']
    CHANNEL_OPTIONS = ['Luminosity', 'RGB', 'HSV', 'HLS']

    def create_form(self, layout, action):
        DefaultActionConfigurator.create_form(self, layout, action)
        self.builder.add_field('mask_size', FIELD_FLOAT, 'Mask size', required=False,
                               default=0, min=0, max=5, step=0.1)
        self.builder.add_field('intensity_interval', FIELD_INT_TUPLE, 'Intensity range', required=False, size=2,
                               default=[v for k, v in constants.DEFAULT_INTENSITY_INTERVAL.items()],
                               labels=['min', 'max'], min=[-1] * 2, max=[65536] * 2)
        self.builder.add_field('img_scale', FIELD_INT, 'Image resample', required=False,
                               default=constants.DEFAULT_IMG_SCALE, min=1, max=256)
        self.builder.add_field('corr_map', FIELD_COMBO, 'Correction map', required=False,
                               options=self.CORRECTION_MAP_OPTIONS, values=constants.VALID_BALANCE,
                               default='Linear')
        self.builder.add_field('channel', FIELD_COMBO, 'Channel', required=False,
                               options=self.CHANNEL_OPTIONS, values=constants.VALID_BALANCE_CHANNELS,
                               default='Luminosity')
        self.add_bold_label("Miscellanea:")
        self.builder.add_field('plot_summary', FIELD_BOOL, 'Plot summary', required=False, default=False)
        self.builder.add_field('plot_histograms', FIELD_BOOL, 'Plot histograms', required=False, default=False)
