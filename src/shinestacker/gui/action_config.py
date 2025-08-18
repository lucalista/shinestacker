# pylint: disable=C0114, C0115, C0116, E0611, R0913, R0917, R0915, R0912
# pylint: disable=E0606, W0718, R1702, W0102, W0221
import traceback
from abc import ABC, abstractmethod
from typing import Dict, Any
import os.path
from PySide6.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QFileDialog, QLabel, QComboBox,
                               QMessageBox, QSizePolicy, QStackedWidget, QDialog, QFormLayout,
                               QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QTreeView,
                               QAbstractItemView, QListView)
from PySide6.QtCore import Qt, QTimer
from .. config.constants import constants
from .. algorithms.align import validate_align_config
from .project_model import ActionConfig
from .select_path_widget import (create_select_file_paths_widget, create_layout_widget_no_margins,
                                 create_layout_widget_and_connect)

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
    def __init__(self, expert, current_wd):
        self.expert = expert
        self.current_wd = current_wd

    @abstractmethod
    def create_form(self, layout: QFormLayout, action: ActionConfig, tag: str = "Action"):
        pass

    @abstractmethod
    def update_params(self, params: Dict[str, Any]) -> bool:
        pass


class FieldBuilder:
    def __init__(self, layout, action, current_wd):
        self.layout = layout
        self.action = action
        self.current_wd = current_wd
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
        if 'default' in kwargs:
            default_value = kwargs['default']
        else:
            if field_type == FIELD_TEXT:
                default_value = kwargs.get('placeholder', '')
            elif field_type in (FIELD_ABS_PATH, FIELD_REL_PATH):
                default_value = ''
            elif field_type == FIELD_FLOAT:
                default_value = kwargs.get('default', 0.0)
            elif field_type == FIELD_INT:
                default_value = kwargs.get('default', 0)
            elif field_type == FIELD_INT_TUPLE:
                default_value = kwargs.get('default', [0] * kwargs.get('size', 1))
            elif field_type == FIELD_BOOL:
                default_value = kwargs.get('default', False)
            elif field_type == FIELD_COMBO:
                default_value = kwargs.get(
                    'default',
                    kwargs.get('options', [''])[0] if 'options' in kwargs else '')
        self.fields[tag] = {
            'widget': widget,
            'type': field_type,
            'label': label,
            'required': required,
            'default_value': default_value,
            **kwargs
        }
        if add_to_layout is None:
            add_to_layout = self.layout
        add_to_layout.addRow(f"{label}:", widget)
        return widget

    def reset_to_defaults(self):
        for tag, field in self.fields.items():
            if tag not in ['name', 'working_path', 'input_path', 'output_path',
                           'exif_path', 'plot_path']:
                default = field['default_value']
                widget = field['widget']
                if field['type'] == FIELD_TEXT:
                    widget.setText(default)
                elif field['type'] in (FIELD_ABS_PATH, FIELD_REL_PATH):
                    self.get_path_widget(widget).setText(default)
                elif field['type'] == FIELD_FLOAT:
                    widget.setValue(default)
                elif field['type'] == FIELD_BOOL:
                    widget.setChecked(default)
                elif field['type'] == FIELD_INT:
                    widget.setValue(default)
                elif field['type'] == FIELD_INT_TUPLE:
                    for i in range(field['size']):
                        spinbox = widget.layout().itemAt(1 + i * 2).widget()
                        spinbox.setValue(default[i])
                elif field['type'] == FIELD_COMBO:
                    widget.setCurrentText(default)

    def get_path_widget(self, widget):
        return widget.layout().itemAt(0).widget()

    def get_working_path(self):
        if 'working_path' in self.fields:
            working_path = self.get_path_widget(self.fields['working_path']['widget']).text()
            if working_path != '':
                return working_path
        parent = self.action.parent
        while parent is not None:
            if 'working_path' in parent.params and parent.params['working_path'] != '':
                return parent.params['working_path']
            parent = parent.parent
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
                params[tag] = [field['widget'].layout().itemAt(1 + i * 2).widget().value()
                               for i in range(field['size'])]
            elif field['type'] == FIELD_COMBO:
                values = field.get('values', None)
                options = field.get('options', None)
                text = field['widget'].currentText()
                if values is not None and options is not None:
                    text = dict(zip(options, values))[text]
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
                    working_path_abs = os.path.isabs(working_path)
                    if not working_path_abs:
                        working_path = os.path.join(self.current_wd, working_path)
                    abs_path = os.path.normpath(os.path.join(working_path, params[tag]))
                    if not abs_path.startswith(os.path.normpath(working_path)):
                        QMessageBox.warning(
                            None, "Invalid Path",
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
                    traceback.print_tb(e.__traceback__)
                    QMessageBox.warning(None, "Error", f"Invalid path: {str(e)}")
                    return False
        return True

    def create_text_field(self, tag, **kwargs):
        value = self.action.params.get(tag, '')
        edit = QLineEdit(value)
        edit.setPlaceholderText(kwargs.get('placeholder', ''))
        return edit

    def create_abs_path_field(self, tag, **kwargs):
        return create_select_file_paths_widget(
            self.action.params.get(tag, ''),
            kwargs.get('placeholder', ''),
            tag.replace('_', ' ')
        )[1]

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
                                    QMessageBox.warning(
                                        None, "Invalid Path",
                                        f"{label} must be a subdirectory of working path")
                                    return
                                rel_paths.append(rel_path)
                            except ValueError as e:
                                traceback.print_tb(e.__traceback__)
                                QMessageBox.warning(None, "Error",
                                                    "Could not compute relative path")
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
                            except ValueError as e:
                                traceback.print_tb(e.__traceback__)
                                QMessageBox.warning(None, "Error",
                                                    "Could not compute relative path")
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
                    except ValueError as e:
                        traceback.print_tb(e.__traceback__)
                        QMessageBox.warning(None, "Error", "Could not compute relative path")
        return create_layout_widget_and_connect(button, edit, browse)

    def create_float_field(self, tag, default=0.0, min_val=0.0, max_val=1.0,
                           step=0.1, decimals=2):
        spin = QDoubleSpinBox()
        spin.setValue(self.action.params.get(tag, default))
        spin.setRange(min_val, max_val)
        spin.setDecimals(decimals)
        spin.setSingleStep(step)
        return spin

    def create_int_field(self, tag, default=0, min_val=0, max_val=100):
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(self.action.params.get(tag, default))
        return spin

    def create_int_tuple_field(self, tag, size=1,
                               default=[0] * 100, min_val=[0] * 100, max_val=[100] * 100,
                               **kwargs):
        layout = QHBoxLayout()
        spins = [QSpinBox() for i in range(size)]
        labels = kwargs.get('labels', ('') * size)
        value = self.action.params.get(tag, default)
        for i, spin in enumerate(spins):
            spin.setRange(min_val[i], max_val[i])
            spin.setValue(value[i])
            spin.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            label = QLabel(labels[i] + ":")
            label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            layout.addWidget(label)
            layout.addWidget(spin)
            layout.setStretch(layout.count() - 1, 1)
        return create_layout_widget_no_margins(layout)

    def create_combo_field(self, tag, options=None, default=None, **kwargs):
        options = options or []
        values = kwargs.get('values', None)
        combo = QComboBox()
        combo.addItems(options)
        value = self.action.params.get(tag, default or options[0] if options else '')
        if values is not None and len(options) > 0:
            value = dict(zip(values, options)).get(value, value)
        combo.setCurrentText(value)
        return combo

    def create_bool_field(self, tag, default=False):
        checkbox = QCheckBox()
        checkbox.setChecked(self.action.params.get(tag, default))
        return checkbox


class ActionConfigDialog(QDialog):
    def __init__(self, action: ActionConfig, current_wd, parent=None):
        super().__init__(parent)
        self.current_wd = current_wd
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
        reset_button = QPushButton("Reset")
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        button_box.addWidget(reset_button)
        reset_button.clicked.connect(self.reset_to_defaults)
        self.layout.addRow(button_box)
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

    def get_configurator(self, action_type: str) -> ActionConfigurator:
        configurators = {
            constants.ACTION_JOB: JobConfigurator,
            constants.ACTION_COMBO: CombinedActionsConfigurator,
            constants.ACTION_NOISEDETECTION: NoiseDetectionConfigurator,
            constants.ACTION_FOCUSSTACK: FocusStackConfigurator,
            constants.ACTION_FOCUSSTACKBUNCH: FocusStackBunchConfigurator,
            constants.ACTION_MULTILAYER: MultiLayerConfigurator,
            constants.ACTION_MASKNOISE: MaskNoiseConfigurator,
            constants.ACTION_VIGNETTING: VignettingConfigurator,
            constants.ACTION_ALIGNFRAMES: AlignFramesConfigurator,
            constants.ACTION_BALANCEFRAMES: BalanceFramesConfigurator,
        }
        return configurators.get(
            action_type, DefaultActionConfigurator)(self.expert(), self.current_wd)

    def accept(self):
        self.parent().project_buffer.append(self.parent().project.clone())
        if self.configurator.update_params(self.action.params):
            self.parent().mark_as_modified()
            super().accept()
        else:
            self.parent().project_buffer.pop()

    def reset_to_defaults(self):
        builder = self.configurator.get_builder()
        if builder:
            builder.reset_to_defaults()

    def expert(self):
        return self.parent().expert_options


class NoNameActionConfigurator(ActionConfigurator):
    def __init__(self, expert, current_wd):
        super().__init__(expert, current_wd)
        self.builder = None

    def get_builder(self):
        return self.builder

    def update_params(self, params: Dict[str, Any]) -> bool:
        return self.builder.update_params(params)

    def add_bold_label(self, label):
        label = QLabel(label)
        label.setStyleSheet("font-weight: bold")
        self.builder.layout.addRow(label)


class DefaultActionConfigurator(NoNameActionConfigurator):
    def create_form(self, layout, action, tag='Action'):
        self.builder = FieldBuilder(layout, action, self.current_wd)
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
        self.builder.add_field('input_path', FIELD_REL_PATH,
                               f'Input path (separate by {constants.PATH_SEPARATOR})',
                               required=False, multiple_entries=True,
                               placeholder='relative to working path')
        self.builder.add_field('max_frames', FIELD_INT, 'Max. num. of frames', required=False,
                               default=-1, min_val=-1, max_val=1000)
        self.builder.add_field('channel_thresholds', FIELD_INT_TUPLE, 'Noise threshold',
                               required=False, size=3,
                               default=constants.DEFAULT_CHANNEL_THRESHOLDS,
                               labels=constants.RGB_LABELS, min_val=[1] * 3,
                               max_val=[1000] * 3)
        if self.expert:
            self.builder.add_field('blur_size', FIELD_INT, 'Blur size (px)', required=False,
                                   default=constants.DEFAULT_BLUR_SIZE, min_val=1, max_val=50)
        self.builder.add_field('file_name', FIELD_TEXT, 'File name', required=False,
                               default=constants.DEFAULT_NOISE_MAP_FILENAME,
                               placeholder=constants.DEFAULT_NOISE_MAP_FILENAME)
        self.add_bold_label("Miscellanea:")
        self.builder.add_field('plot_histograms', FIELD_BOOL, 'Plot histograms', required=False,
                               default=False)
        self.builder.add_field('plot_path', FIELD_REL_PATH, 'Plots path', required=False,
                               default=constants.DEFAULT_PLOTS_PATH,
                               placeholder='relative to working path')
        self.builder.add_field('plot_range', FIELD_INT_TUPLE, 'Plot range', required=False,
                               size=2, default=constants.DEFAULT_NOISE_PLOT_RANGE,
                               labels=['min', 'max'], min_val=[0] * 2, max_val=[1000] * 2)


class FocusStackBaseConfigurator(DefaultActionConfigurator):
    ENERGY_OPTIONS = ['Laplacian', 'Sobel']
    MAP_TYPE_OPTIONS = ['Average', 'Maximum']
    FLOAT_OPTIONS = ['float 32 bits', 'float 64 bits']

    def create_form(self, layout, action):
        super().create_form(layout, action)
        if self.expert:
            self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=False)
            self.builder.add_field('input_path', FIELD_REL_PATH, 'Input path', required=False,
                                   placeholder='relative to working path')
            self.builder.add_field('output_path', FIELD_REL_PATH, 'Output path', required=False,
                                   placeholder='relative to working path')
        self.builder.add_field('scratch_output_dir', FIELD_BOOL, 'Scratch output dir.',
                               required=False, default=True)

    def common_fields(self, layout):
        self.builder.add_field('denoise_amount', FIELD_FLOAT, 'Denoise', required=False,
                               default=0, min_val=0, max_val=10)
        self.add_bold_label("Stacking algorithm:")
        combo = self.builder.add_field('stacker', FIELD_COMBO, 'Stacking algorithm', required=True,
                                       options=constants.STACK_ALGO_OPTIONS,
                                       default=constants.STACK_ALGO_DEFAULT)
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
        if self.expert:
            self.builder.add_field('pyramid_min_size', FIELD_INT, 'Minimum size (px)',
                                   required=False, add_to_layout=q_pyramid.layout(),
                                   default=constants.DEFAULT_PY_MIN_SIZE, min_val=2, max_val=256)
            self.builder.add_field('pyramid_kernel_size', FIELD_INT, 'Kernel size (px)',
                                   required=False, add_to_layout=q_pyramid.layout(),
                                   default=constants.DEFAULT_PY_KERNEL_SIZE, min_val=3, max_val=21)
            self.builder.add_field('pyramid_gen_kernel', FIELD_FLOAT, 'Gen. kernel',
                                   required=False, add_to_layout=q_pyramid.layout(),
                                   default=constants.DEFAULT_PY_GEN_KERNEL,
                                   min_val=0.0, max_val=2.0)
            self.builder.add_field('pyramid_float_type', FIELD_COMBO, 'Precision', required=False,
                                   add_to_layout=q_pyramid.layout(),
                                   options=self.FLOAT_OPTIONS, values=constants.VALID_FLOATS,
                                   default=dict(zip(constants.VALID_FLOATS,
                                                self.FLOAT_OPTIONS))[constants.DEFAULT_PY_FLOAT])
        self.builder.add_field('depthmap_energy', FIELD_COMBO, 'Energy', required=False,
                               add_to_layout=q_depthmap.layout(),
                               options=self.ENERGY_OPTIONS, values=constants.VALID_DM_ENERGY,
                               default=dict(zip(constants.VALID_DM_ENERGY,
                                            self.ENERGY_OPTIONS))[constants.DEFAULT_DM_ENERGY])
        self.builder.add_field('map_type', FIELD_COMBO, 'Map type', required=False,
                               add_to_layout=q_depthmap.layout(),
                               options=self.MAP_TYPE_OPTIONS, values=constants.VALID_DM_MAP,
                               default=dict(zip(constants.VALID_DM_MAP,
                                            self.MAP_TYPE_OPTIONS))[constants.DEFAULT_DM_MAP])
        if self.expert:
            self.builder.add_field('depthmap_kernel_size', FIELD_INT, 'Kernel size (px)',
                                   required=False, add_to_layout=q_depthmap.layout(),
                                   default=constants.DEFAULT_DM_KERNEL_SIZE, min_val=3, max_val=21)
            self.builder.add_field('depthmap_blur_size', FIELD_INT, 'Blurl size (px)',
                                   required=False, add_to_layout=q_depthmap.layout(),
                                   default=constants.DEFAULT_DM_BLUR_SIZE, min_val=1, max_val=21)
            self.builder.add_field('depthmap_smooth_size', FIELD_INT, 'Smooth size (px)',
                                   required=False, add_to_layout=q_depthmap.layout(),
                                   default=constants.DEFAULT_DM_SMOOTH_SIZE, min_val=0, max_val=256)
            self.builder.add_field('depthmap_temperature', FIELD_FLOAT, 'Temperature',
                                   required=False,
                                   add_to_layout=q_depthmap.layout(),
                                   default=constants.DEFAULT_DM_TEMPERATURE,
                                   min_val=0, max_val=1, step=0.05)
            self.builder.add_field('depthmap_levels', FIELD_INT, 'Levels', required=False,
                                   add_to_layout=q_depthmap.layout(),
                                   default=constants.DEFAULT_DM_LEVELS, min_val=2, max_val=6)
            self.builder.add_field('depthmap_float_type', FIELD_COMBO, 'Precision', required=False,
                                   add_to_layout=q_depthmap.layout(), options=self.FLOAT_OPTIONS,
                                   values=constants.VALID_FLOATS,
                                   default=dict(zip(constants.VALID_FLOATS,
                                                self.FLOAT_OPTIONS))[constants.DEFAULT_DM_FLOAT])
        self.builder.layout.addRow(stacked)
        combo.currentIndexChanged.connect(change)


class FocusStackConfigurator(FocusStackBaseConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        if self.expert:
            self.builder.add_field('exif_path', FIELD_REL_PATH, 'Exif data path', required=False,
                                   placeholder='relative to working path')
            self.builder.add_field('prefix', FIELD_TEXT, 'Ouptut filename prefix', required=False,
                                   default=constants.DEFAULT_STACK_PREFIX,
                                   placeholder=constants.DEFAULT_STACK_PREFIX)
        self.builder.add_field('plot_stack', FIELD_BOOL, 'Plot stack', required=False,
                               default=constants.DEFAULT_PLOT_STACK)
        super().common_fields(layout)


class FocusStackBunchConfigurator(FocusStackBaseConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.builder.add_field('frames', FIELD_INT, 'Frames', required=False,
                               default=constants.DEFAULT_FRAMES, min_val=1, max_val=100)
        self.builder.add_field('overlap', FIELD_INT, 'Overlapping frames', required=False,
                               default=constants.DEFAULT_OVERLAP, min_val=0, max_val=100)
        self.builder.add_field('plot_stack', FIELD_BOOL, 'Plot stack', required=False,
                               default=constants.DEFAULT_PLOT_STACK_BUNCH)
        super().common_fields(layout)


class MultiLayerConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        if self.expert:
            self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=False)
        self.builder.add_field('input_path', FIELD_REL_PATH,
                               f'Input path (separate by {constants.PATH_SEPARATOR})',
                               required=False, multiple_entries=True,
                               placeholder='relative to working path')
        if self.expert:
            self.builder.add_field('output_path', FIELD_REL_PATH, 'Output path', required=False,
                                   placeholder='relative to working path')
            self.builder.add_field('exif_path', FIELD_REL_PATH, 'Exif data path', required=False,
                                   placeholder='relative to working path')
        self.builder.add_field('scratch_output_dir', FIELD_BOOL, 'Scratch output dir.',
                               required=False, default=True)
        self.builder.add_field('reverse_order', FIELD_BOOL, 'Reverse file order',
                               required=False,
                               default=constants.DEFAULT_MULTILAYER_FILE_REVERSE_ORDER)


class CombinedActionsConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        if self.expert:
            self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=False)
            self.builder.add_field('input_path', FIELD_REL_PATH, 'Input path', required=False,
                                   must_exist=True, placeholder='relative to working path')
            self.builder.add_field('output_path', FIELD_REL_PATH, 'Output path', required=False,
                                   placeholder='relative to working path')
        self.builder.add_field('scratch_output_dir', FIELD_BOOL, 'Scratch output dir.',
                               required=False, default=True)
        if self.expert:
            self.builder.add_field('plot_path', FIELD_REL_PATH, 'Plots path', required=False,
                                   default="plots", placeholder='relative to working path')
            self.builder.add_field('resample', FIELD_INT, 'Resample frame stack', required=False,
                                   default=1, min_val=1, max_val=100)
            self.builder.add_field('ref_idx', FIELD_INT, 'Reference frame index', required=False,
                                   default=-1, min_val=-1, max_val=1000)
            self.builder.add_field('step_process', FIELD_BOOL, 'Step process', required=False,
                                   default=True)


class MaskNoiseConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.builder.add_field('noise_mask', FIELD_REL_PATH, 'Noise mask file', required=False,
                               path_type='file', must_exist=True,
                               default=constants.DEFAULT_NOISE_MAP_FILENAME,
                               placeholder=constants.DEFAULT_NOISE_MAP_FILENAME)
        if self.expert:
            self.builder.add_field('kernel_size', FIELD_INT, 'Kernel size', required=False,
                                   default=constants.DEFAULT_MN_KERNEL_SIZE, min_va=1, max_val=10)
            self.builder.add_field('method', FIELD_COMBO, 'Interpolation method', required=False,
                                   options=['Mean', 'Median'], default='Mean')


class VignettingConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        if self.expert:
            self.builder.add_field('r_steps', FIELD_INT, 'Radial steps', required=False,
                                   default=constants.DEFAULT_R_STEPS, min_val=1, max_val=1000)
            self.builder.add_field('black_threshold', FIELD_INT, 'Black intensity threshold',
                                   required=False, default=constants.DEFAULT_BLACK_THRESHOLD,
                                   min_val=0, max_val=1000)
        self.builder.add_field('max_correction', FIELD_FLOAT, 'Max. correction', required=False,
                               default=constants.DEFAULT_MAX_CORRECTION,
                               min_val=0, max_val=1, step=0.05)
        self.add_bold_label("Miscellanea:")
        self.builder.add_field('plot_correction', FIELD_BOOL, 'Plot correction', required=False,
                               default=False)
        self.builder.add_field('plot_summary', FIELD_BOOL, 'Plot summary', required=False,
                               default=False)
        self.builder.add_field('apply_correction', FIELD_BOOL, 'Apply correction', required=False,
                               default=True)


class AlignFramesConfigurator(DefaultActionConfigurator):
    BORDER_MODE_OPTIONS = ['Constant', 'Replicate', 'Replicate and blur']
    TRANSFORM_OPTIONS = ['Rigid', 'Homography']
    METHOD_OPTIONS = ['Random Sample Consensus (RANSAC)', 'Least Median (LMEDS)']
    MATCHING_METHOD_OPTIONS = ['K-nearest neighbors', 'Hamming distance']

    def __init__(self, expert, current_wd):
        super().__init__(expert, current_wd)
        self.matching_method_field = None
        self.info_label = None
        self.detector_field = None
        self.descriptor_field = None
        self.matching_method_field = None

    def show_info(self, message, timeout=3000):
        self.info_label.setText(message)
        self.info_label.setVisible(True)
        timer = QTimer(self.info_label)
        timer.setSingleShot(True)
        timer.timeout.connect(self.info_label.hide)
        timer.start(timeout)

    def change_match_config(self):
        detector = self.detector_field.currentText()
        descriptor = self.descriptor_field.currentText()
        match_method = dict(
            zip(self.MATCHING_METHOD_OPTIONS,
                constants.VALID_MATCHING_METHODS))[self.matching_method_field.currentText()]
        try:
            validate_align_config(detector, descriptor, match_method)
        except Exception as e:
            self.show_info(str(e))
            if descriptor == constants.DETECTOR_SIFT and \
               match_method == constants.MATCHING_NORM_HAMMING:
                self.matching_method_field.setCurrentText(self.MATCHING_METHOD_OPTIONS[0])
            if detector == constants.DETECTOR_ORB and descriptor == constants.DESCRIPTOR_AKAZE and \
                    match_method == constants.MATCHING_NORM_HAMMING:
                self.matching_method_field.setCurrentText(constants.MATCHING_NORM_HAMMING)
            if detector == constants.DETECTOR_BRISK and descriptor == constants.DESCRIPTOR_AKAZE:
                self.descriptor_field.setCurrentText('BRISK')
            if detector == constants.DETECTOR_SURF and descriptor == constants.DESCRIPTOR_AKAZE:
                self.descriptor_field.setCurrentText('SIFT')
            if detector == constants.DETECTOR_SIFT and descriptor != constants.DESCRIPTOR_SIFT:
                self.descriptor_field.setCurrentText('SIFT')
            if detector in constants.NOKNN_METHODS['detectors'] and \
               descriptor in constants.NOKNN_METHODS['descriptors']:
                if match_method == constants.MATCHING_KNN:
                    self.matching_method_field.setCurrentText(self.MATCHING_METHOD_OPTIONS[1])

    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.detector_field = None
        self.descriptor_field = None
        self.matching_method_field = None
        if self.expert:
            self.add_bold_label("Feature identification:")

            self.info_label = QLabel()
            self.info_label.setStyleSheet("color: orange; font-style: italic;")
            self.info_label.setVisible(False)
            layout.addRow(self.info_label)

            self.detector_field = self.builder.add_field(
                'detector', FIELD_COMBO, 'Detector', required=False,
                options=constants.VALID_DETECTORS, default=constants.DEFAULT_DETECTOR)
            self.descriptor_field = self.builder.add_field(
                'descriptor', FIELD_COMBO, 'Descriptor', required=False,
                options=constants.VALID_DESCRIPTORS, default=constants.DEFAULT_DESCRIPTOR)

            self.add_bold_label("Feature matching:")
            self.matching_method_field = self.builder.add_field(
                'match_method', FIELD_COMBO, 'Match method', required=False,
                options=self.MATCHING_METHOD_OPTIONS, values=constants.VALID_MATCHING_METHODS,
                default=constants.DEFAULT_MATCHING_METHOD)
            self.detector_field.setToolTip(
                "SIFT: Requires SIFT descriptor and K-NN matching\n"
                "ORB/AKAZE: Work best with Hamming distance"
            )

            self.descriptor_field.setToolTip(
                "SIFT: Requires K-NN matching\n"
                "ORB/AKAZE: Require Hamming distance with ORB/AKAZE detectors"
            )

            self.matching_method_field.setToolTip(
                "Automatically selected based on detector/descriptor combination"
            )

            self.detector_field.currentIndexChanged.connect(self.change_match_config)
            self.descriptor_field.currentIndexChanged.connect(self.change_match_config)
            self.matching_method_field.currentIndexChanged.connect(self.change_match_config)
            self.builder.add_field('flann_idx_kdtree', FIELD_INT, 'Flann idx kdtree',
                                   required=False,
                                   default=constants.DEFAULT_FLANN_IDX_KDTREE,
                                   min_val=0, max_val=10)
            self.builder.add_field('flann_trees', FIELD_INT, 'Flann trees', required=False,
                                   default=constants.DEFAULT_FLANN_TREES,
                                   min_val=0, max_val=10)
            self.builder.add_field('flann_checks', FIELD_INT, 'Flann checks', required=False,
                                   default=constants.DEFAULT_FLANN_CHECKS,
                                   min_val=0, max_val=1000)
            self.builder.add_field('threshold', FIELD_FLOAT, 'Threshold', required=False,
                                   default=constants.DEFAULT_ALIGN_THRESHOLD,
                                   min_val=0, max_val=1, step=0.05)

            self.add_bold_label("Transform:")
            transform = self.builder.add_field(
                'transform', FIELD_COMBO, 'Transform', required=False,
                options=self.TRANSFORM_OPTIONS, values=constants.VALID_TRANSFORMS,
                default=constants.DEFAULT_TRANSFORM)
            method = self.builder.add_field(
                'align_method', FIELD_COMBO, 'Align method', required=False,
                options=self.METHOD_OPTIONS, values=constants.VALID_ALIGN_METHODS,
                default=constants.DEFAULT_ALIGN_METHOD)
            rans_threshold = self.builder.add_field(
                'rans_threshold', FIELD_FLOAT, 'RANSAC threshold (px)', required=False,
                default=constants.DEFAULT_RANS_THRESHOLD, min_val=0, max_val=20, step=0.1)
            self.builder.add_field(
                'min_good_matches', FIELD_INT, "Min. good matches", required=False,
                default=constants.DEFAULT_ALIGN_MIN_GOOD_MATCHES, min_val=0, max_val=500)

            def change_method():
                text = method.currentText()
                if text == self.METHOD_OPTIONS[0]:
                    rans_threshold.setEnabled(True)
                elif text == self.METHOD_OPTIONS[1]:
                    rans_threshold.setEnabled(False)
            method.currentIndexChanged.connect(change_method)
            change_method()
            self.builder.add_field('align_confidence', FIELD_FLOAT, 'Confidence (%)',
                                   required=False, decimals=1,
                                   default=constants.DEFAULT_ALIGN_CONFIDENCE,
                                   min_val=70.0, max_val=100.0, step=0.1)

            refine_iters = self.builder.add_field(
                'refine_iters', FIELD_INT, 'Refinement iterations (Rigid)', required=False,
                default=constants.DEFAULT_REFINE_ITERS, min_val=0, max_val=1000)
            max_iters = self.builder.add_field(
                'max_iters', FIELD_INT, 'Max. iterations (Homography)', required=False,
                default=constants.DEFAULT_ALIGN_MAX_ITERS, min_val=0, max_val=5000)

            def change_transform():
                text = transform.currentText()
                if text == self.TRANSFORM_OPTIONS[0]:
                    refine_iters.setEnabled(True)
                    max_iters.setEnabled(False)
                elif text == self.TRANSFORM_OPTIONS[1]:
                    refine_iters.setEnabled(False)
                    max_iters.setEnabled(True)
            transform.currentIndexChanged.connect(change_transform)
            change_transform()
            subsample = self.builder.add_field(
                'subsample', FIELD_INT, 'Subsample factor', required=False,
                default=constants.DEFAULT_ALIGN_SUBSAMPLE, min_val=1, max_val=256)
            fast_subsampling = self.builder.add_field(
                'fast_subsampling', FIELD_BOOL, 'Fast subsampling', required=False,
                default=constants.DEFAULT_ALIGN_FAST_SUBSAMPLING)

            def change_subsample():
                fast_subsampling.setEnabled(subsample.value() > 1)
            subsample.valueChanged.connect(change_subsample)
            change_subsample()
            self.add_bold_label("Border:")
            self.builder.add_field('border_mode', FIELD_COMBO, 'Border mode', required=False,
                                   options=self.BORDER_MODE_OPTIONS,
                                   values=constants.VALID_BORDER_MODES,
                                   default=constants.DEFAULT_BORDER_MODE)
            self.builder.add_field('border_value', FIELD_INT_TUPLE,
                                   'Border value (if constant)', required=False, size=4,
                                   default=constants.DEFAULT_BORDER_VALUE,
                                   labels=constants.RGBA_LABELS,
                                   min_val=constants.DEFAULT_BORDER_VALUE, max_val=[255] * 4)
            self.builder.add_field('border_blur', FIELD_FLOAT, 'Border blur', required=False,
                                   default=constants.DEFAULT_BORDER_BLUR,
                                   min_val=0, max_val=1000, step=1)
        self.add_bold_label("Miscellanea:")
        self.builder.add_field('plot_summary', FIELD_BOOL, 'Plot summary',
                               required=False, default=False)
        self.builder.add_field('plot_matches', FIELD_BOOL, 'Plot matches',
                               required=False, default=False)

    def update_params(self, params: Dict[str, Any]) -> bool:
        if self.detector_field and self.descriptor_field and self.matching_method_field:
            try:
                detector = self.detector_field.currentText()
                descriptor = self.descriptor_field.currentText()
                match_method = dict(
                    zip(self.MATCHING_METHOD_OPTIONS,
                        constants.VALID_MATCHING_METHODS))[
                            self.matching_method_field.currentText()]
                validate_align_config(detector, descriptor, match_method)
                return super().update_params(params)
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                QMessageBox.warning(None, "Error", f"{str(e)}")
                return False
        return super().update_params(params)


class BalanceFramesConfigurator(DefaultActionConfigurator):
    CORRECTION_MAP_OPTIONS = ['Linear', 'Gamma', 'Match histograms']
    CHANNEL_OPTIONS = ['Luminosity', 'RGB', 'HSV', 'HLS']

    def create_form(self, layout, action):
        super().create_form(layout, action)
        if self.expert:
            self.builder.add_field('mask_size', FIELD_FLOAT, 'Mask size', required=False,
                                   default=0, min_val=0, max_val=5, step=0.1)
            self.builder.add_field('intensity_interval', FIELD_INT_TUPLE, 'Intensity range',
                                   required=False, size=2,
                                   default=[v for k, v in
                                            constants.DEFAULT_INTENSITY_INTERVAL.items()],
                                   labels=['min', 'max'], min_val=[-1] * 2, max_val=[65536] * 2)
            self.builder.add_field('subsample', FIELD_INT, 'Subsample factor', required=False,
                                   default=constants.DEFAULT_BALANCE_SUBSAMPLE,
                                   min_val=1, max_val=256)
        self.builder.add_field('corr_map', FIELD_COMBO, 'Correction map', required=False,
                               options=self.CORRECTION_MAP_OPTIONS, values=constants.VALID_BALANCE,
                               default='Linear')
        self.builder.add_field('channel', FIELD_COMBO, 'Channel', required=False,
                               options=self.CHANNEL_OPTIONS,
                               values=constants.VALID_BALANCE_CHANNELS,
                               default='Luminosity')
        self.add_bold_label("Miscellanea:")
        self.builder.add_field('plot_summary', FIELD_BOOL, 'Plot summary',
                               required=False, default=False)
        self.builder.add_field('plot_histograms', FIELD_BOOL, 'Plot histograms',
                               required=False, default=False)
