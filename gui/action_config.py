from PySide6.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QFileDialog, QLabel, QComboBox,
                               QMessageBox, QSizePolicy, QStackedWidget, QDialog, QFormLayout,
                               QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QTreeView, QAbstractItemView, QListView)
from PySide6.QtCore import Qt
from gui.project_model import (ActionConfig,
                               ACTION_JOB, ACTION_COMBO, ACTION_NOISEDETECTION, ACTION_FOCUSSTACK,
                               ACTION_FOCUSSTACKBUNCH, ACTION_MULTILAYER,
                               ACTION_MASKNOISE, ACTION_VIGNETTING, ACTION_ALIGNFRAMES,
                               ACTION_BALANCEFRAMES)
from abc import ABC, abstractmethod
from typing import Dict, Any
import os.path
from focus_stack.align import VALID_BORDER_MODES, VALID_TRANSFORMS, VALID_MATCHING_METHODS
from focus_stack.noise_detection import DEFAULT_NOISE_MAP_FILENAME
from focus_stack.balance import VALID_BALANCE
from focus_stack.depth_map import VALID_MAP, VALID_ENERGY

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

    def make_convertion_map(self, ks, vs):
        return {k: v for k, v in zip(ks, vs)}


class FieldBuilder:
    def __init__(self, layout, action):
        self.layout = layout
        self.action = action
        self.fields = {}

    def add_field(self, tag: str, field_type: str, label: str,
                  required: bool = False, add_to_layout=None, **kwargs):
        if field_type == FIELD_TEXT:
            widget = self._create_text_field(tag, **kwargs)
        elif field_type == FIELD_ABS_PATH:
            widget = self._create_abs_path_field(tag, **kwargs)
        elif field_type == FIELD_REL_PATH:
            widget = self._create_rel_path_field(tag, **kwargs)
        elif field_type == FIELD_FLOAT:
            widget = self._create_float_field(tag, **kwargs)
        elif field_type == FIELD_INT:
            widget = self._create_int_field(tag, **kwargs)
        elif field_type == FIELD_INT_TUPLE:
            widget = self._create_int_tuple_field(tag, **kwargs)
        elif field_type == FIELD_BOOL:
            widget = self._create_bool_field(tag, **kwargs)
        elif field_type == FIELD_COMBO:
            widget = self._create_combo_field(tag, **kwargs)
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
                text = field['widget'].currentText()
                convertion_map = field.get('convertion_map', None)
                if convertion_map:
                    text = convertion_map[text]
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
                            paths = abs_path.split(";")
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

    def _create_text_field(self, tag, **kwargs):
        value = self.action.params.get(tag, '')
        edit = QLineEdit(value)
        edit.setPlaceholderText(kwargs.get('placeholder', ''))
        return edit

    def _create_abs_path_field(self, tag, **kwargs):
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

    def _create_rel_path_field(self, tag, **kwargs):
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
                            edit.setText(";".join(rel_paths))

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
                            edit.setText(";".join(rel_paths))
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

    def _create_float_field(self, tag, default=0.0, min=0.0, max=1.0, step=0.1, **kwargs):
        spin = QDoubleSpinBox()
        spin.setValue(self.action.params.get(tag, default))
        spin.setRange(min, max)
        spin.setSingleStep(step)
        return spin

    def _create_int_field(self, tag, default=0, min=0, max=100, **kwargs):
        spin = QSpinBox()
        spin.setRange(min, max)
        spin.setValue(self.action.params.get(tag, default))
        return spin

    def _create_int_tuple_field(self, tag, size=1, default=[0] * 100, min=[0] * 100, max=[100] * 100, **kwargs):
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

    def _create_combo_field(self, tag, options=None, default=None, **kwargs):
        options = options or []
        value = self.action.params.get(tag, default or options[0] if options else '')
        combo = QComboBox()
        combo.addItems(options)
        if value in options:
            combo.setCurrentText(value)
        return combo

    def _create_bool_field(self, tag, default=False, **kwargs):
        checkbox = QCheckBox()
        checkbox.setChecked(self.action.params.get(tag, default))
        return checkbox


class ActionConfigDialog(QDialog):
    def __init__(self, action: ActionConfig, parent=None):
        super().__init__(parent)
        self.action = action
        self.setWindowTitle(f"Configure {action.type_name}")
        self.resize(500, self.height())
        self.configurator = self._get_configurator(action.type_name)
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

    def _get_configurator(self, action_type: str) -> ActionConfigurator:
        configurators = {
            ACTION_JOB: JobConfigurator(),
            ACTION_COMBO: CombinedActionsConfigurator(),
            ACTION_NOISEDETECTION: NoiseDetectionConfigurator(),
            ACTION_FOCUSSTACK: FocusStackConfigurator(),
            ACTION_FOCUSSTACKBUNCH: FocusStackBunchConfigurator(),
            ACTION_MULTILAYER: MultiLayerConfigurator(),
            ACTION_MASKNOISE: MaskNoiseConfigurator(),
            ACTION_VIGNETTING: VignettingConfigurator(),
            ACTION_ALIGNFRAMES: AlignFramesConfigurator(),
            ACTION_BALANCEFRAMES: BalanceFramesConfigurator(),
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
        self.builder.add_field('input_path', FIELD_REL_PATH, 'Input path (separate by ;)', required=False, multiple_entries=True,
                               placeholder='relative to working path')
        self.builder.add_field('output_path', FIELD_REL_PATH, 'Output path', required=False,
                               placeholder='relative to working path')
        self.builder.add_field('channel_thresholds', FIELD_INT_TUPLE, 'Noise threshold', required=False, size=3,
                               default=[13, 13, 13], labels=['r', 'g', 'b'], min=[1] * 3, max=[1000] * 3)
        self.builder.add_field('blur_size', FIELD_INT, 'Blur size (px)', required=False,
                               default=5, min=1, max=50)
        self.builder.add_field('file_name', FIELD_TEXT, 'File name', required=False,
                               default="hot", placeholder="hot")
        self.add_bold_label("Miscellanea:")
        self.builder.add_field('plot_histograms', FIELD_BOOL, 'Plot histograms', required=False, default=False)
        self.builder.add_field('plot_path', FIELD_REL_PATH, 'Plots path', required=False, default="plots",
                               placeholder='relative to working path')
        self.builder.add_field('plot_range', FIELD_INT_TUPLE, 'Plot range', required=False, size=2,
                               default=[5, 30], labels=['min', 'max'], min=[0] * 2, max=[1000] * 2)


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

    def common_fields(self, layout, action):
        self.builder.add_field('denoise', FIELD_FLOAT, 'Denoise', required=False,
                               default=0, min=0, max=10)
        self.add_bold_label("Stacking algorithm:")
        combo = self.builder.add_field('stacker', FIELD_COMBO, 'Stacking algorithm', required=True,
                                       options=['Pyramid', 'Depth map'], default='Pyramid')
        combo.setCurrentIndex(0)
        combo.setCurrentText('Pyramid')
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
                               default=32, min=2, max=256)
        self.builder.add_field('pyramid_kernel_size', FIELD_INT, 'Kernel size (px)',
                               required=False, add_to_layout=q_pyramid.layout(),
                               default=5, min=3, max=21)
        self.builder.add_field('pyramid_gen_kernel', FIELD_FLOAT, 'Gen. kernel',
                               required=False, add_to_layout=q_pyramid.layout(),
                               default=0.4, min=0.0, max=2.0)
        energy_map = self.make_convertion_map(self.ENERGY_OPTIONS, VALID_ENERGY)
        self.builder.add_field('depthmap_energy', FIELD_COMBO, 'Energy', required=False,
                               add_to_layout=q_depthmap.layout(),
                               options=self.ENERGY_OPTIONS, default='Laplacian', convertion_map=energy_map)
        map_type_map = self.make_convertion_map(self.MAP_TYPE_OPTIONS, VALID_MAP)
        self.builder.add_field('map_type', FIELD_COMBO, 'Map type', required=False,
                               add_to_layout=q_depthmap.layout(),
                               options=self.MAP_TYPE_OPTIONS, default='Average', convertion_map=map_type_map)
        self.builder.add_field('depthmap_kernel_size', FIELD_INT, 'Kernel size (px)',
                               required=False, add_to_layout=q_depthmap.layout(),
                               default=5, min=3, max=21)
        self.builder.add_field('depthmap_blur_size', FIELD_INT, 'Blurl size (px)',
                               required=False, add_to_layout=q_depthmap.layout(),
                               default=5, min=1, max=21)
        self.builder.add_field('depthmap_smooth_size', FIELD_INT, 'Smooth size (px)',
                               required=False, add_to_layout=q_depthmap.layout(),
                               default=32, min=1, max=256)
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
                               default=10, min=1, max=100)
        self.builder.add_field('overlap', FIELD_INT, 'Overlapping frames', required=False,
                               default=2, min=0, max=100)
        super().common_fields(layout, action)


class MultiLayerConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=True)
        self.builder.add_field('input_path', FIELD_REL_PATH, 'Input path (separate by ;)', required=False, multiple_entries=True,
                               placeholder='relative to working path')
        self.builder.add_field('output_path', FIELD_REL_PATH, 'Output path', required=False,
                               placeholder='relative to working path')
        self.builder.add_field('exif_path', FIELD_REL_PATH, 'Exif data path', required=False,
                               placeholder='relative to working path')


class CombinedActionsConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        DefaultActionConfigurator.create_form(self, layout, action)
        self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=True)
        self.builder.add_field('input_path', FIELD_REL_PATH, 'Input path', required=False,
                               must_exist=True, placeholder='relative to working path')
        self.builder.add_field('output_path', FIELD_REL_PATH, 'Output path', required=False,
                               placeholder='relative to working path')
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
                               default=DEFAULT_NOISE_MAP_FILENAME, placeholder=DEFAULT_NOISE_MAP_FILENAME)
        self.builder.add_field('kernel_size', FIELD_INT, 'Kernel size', required=False,
                               default=3, min=1, max=10)
        self.builder.add_field('method', FIELD_COMBO, 'Interpolation method', required=False,
                               options=['Mean', 'Median'], default='Mean')


class VignettingConfigurator(NoNameActionConfigurator):
    def create_form(self, layout, action):
        DefaultActionConfigurator.create_form(self, layout, action)
        self.builder.add_field('r_steps', FIELD_INT, 'Radial steps', required=False,
                               default=100, min=1, max=1000)
        self.builder.add_field('black_threshold', FIELD_INT, 'Black intensity threshold', required=False,
                               default=1, min=0, max=1000)
        self.builder.add_field('max_correction', FIELD_FLOAT, 'Max. correction', required=False,
                               default=1, min=0, max=1, step=0.05)
        self.add_bold_label("Miscellanea:")
        self.builder.add_field('plot_histograms', FIELD_BOOL, 'Plot histograms', required=False, default=False)
        self.builder.add_field('apply_correction', FIELD_BOOL, 'Apply correction', required=False, default=True)


class AlignFramesConfigurator(NoNameActionConfigurator):
    BORDER_MODE_OPTIONS = ['Constant', 'Replicate', 'Replicate and blur']
    TRANSFORM_OPTIONS = ['Rigid', 'Homography']
    MATCHING_METHOD_OPTIONS = ['K-nearest neighbors', 'Hamming distance']
    def create_form(self, layout, action):
        DefaultActionConfigurator.create_form(self, layout, action)
        self.add_bold_label("Feature identification:")
        self.builder.add_field('detector', FIELD_COMBO, 'Detector', required=False,
                               options=['SIFT', 'ORB', 'SURF', 'AKAZE'], default='SIFT')
        self.builder.add_field('descriptor', FIELD_COMBO, 'Descriptor', required=False,
                               options=['SIFT', 'ORB', 'AKAZE'], default='SIFT')
        self.add_bold_label("Feature matching:")
        matching_method_map = self.make_convertion_map(self.MATCHING_METHOD_OPTIONS, VALID_MATCHING_METHODS)
        self.builder.add_field('method', FIELD_COMBO, 'Method', required=False,
                               options=self.MATCHING_METHOD_OPTIONS, default='KNN',
                               convertion_map=matching_method_map)
        self.builder.add_field('flann_idx_kdtree', FIELD_INT, 'Flann idx kdtree', required=False,
                               default=2, min=0, max=10)
        self.builder.add_field('flann_trees', FIELD_INT, 'Flann trees', required=False,
                               default=5, min=0, max=10)
        self.builder.add_field('flann_checks', FIELD_INT, 'Flann checks', required=False,
                               default=50, min=0, max=1000)
        self.builder.add_field('threshold', FIELD_FLOAT, 'Threshold', required=False,
                               default=0.75, min=0, max=1, step=0.05)
        self.add_bold_label("Transform:")
        transform_convertion_map = self.make_convertion_map(self.TRANSFORM_OPTIONS, VALID_TRANSFORMS)
        self.builder.add_field('transform', FIELD_COMBO, 'Transform', required=False,
                               options=self.TRANSFORM_OPTIONS, default='Rigid',
                               convertion_map=transform_convertion_map)
        self.builder.add_field('rans_threshold', FIELD_FLOAT, 'Homography RANS threshold', required=False,
                               default=5.0, min=0, max=20, step=0.1)
        self.add_bold_label("Border:")
        border_mode_convertion_map = self.make_convertion_map(self.BORDER_MODE_OPTIONS, VALID_BORDER_MODES)
        self.builder.add_field('border_mode', FIELD_COMBO, 'Border mode', required=False,
                               options=self.BORDER_MODE_OPTIONS, default='Replicate and blur',
                               convertion_map=border_mode_convertion_map)
        self.builder.add_field('border_value', FIELD_INT_TUPLE, 'Border value (if constant)', required=False, size=4,
                               default=[0] * 4, labels=['r', 'g', 'b', 'a'], min=[0] * 4, max=[255] * 4)
        self.builder.add_field('border_blur', FIELD_FLOAT, 'Border blur', required=False,
                               default=50, min=0, max=1000, step=1)
        self.add_bold_label("Miscellanea:")
        self.builder.add_field('plot_histograms', FIELD_BOOL, 'Plot histograms', required=False, default=False)


class BalanceFramesConfigurator(NoNameActionConfigurator):
    CORRECTION_MAP_OPTIONS = ['Linear', 'Gamma', 'Match histograms']
    def create_form(self, layout, action):
        DefaultActionConfigurator.create_form(self, layout, action)
        self.builder.add_field('mask_size', FIELD_FLOAT, 'Mask size', required=False,
                               default=0, min=0, max=5, step=0.1)
        self.builder.add_field('intensity_interval', FIELD_INT_TUPLE, 'Intensity range', required=False, size=2,
                               default=[0, -1], labels=['min', 'max'], min=[-1] * 2, max=[65536] * 2)
        self.builder.add_field('img_scale', FIELD_INT, 'Image resample', required=False,
                               default=8, min=1, max=256)
        correction_map_convertion_map = self.make_convertion_map(self.CORRECTION_MAP_OPTIONS, VALID_BALANCE)
        self.builder.add_field('corr_map', FIELD_COMBO, 'Correction map', required=False,
                               options=self.CORRECTION_MAP_OPTIONS, default='Linear',
                               convertion_map=correction_map_convertion_map)
        self.add_bold_label("Miscellanea:")
        self.builder.add_field('plot_histograms', FIELD_BOOL, 'Plot histograms', required=False, default=False)
