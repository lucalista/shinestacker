from PySide6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QVBoxLayout, QListWidget, QHBoxLayout,
    QFileDialog, QLabel, QComboBox, QMessageBox, QInputDialog, QSizePolicy,
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox)
from PySide6.QtCore import Qt
from gui.project_model import Project, ActionConfig
from abc import ABC, abstractmethod
from typing import Dict, Any
import os.path

ACTION_JOB = "Job"
ACTION_COMBO = "Combined Actions"
ACTION_NOISEDETECTION = "NoiseDetection"
ACTION_FOCUSSTACK = "FocusStack"
ACTION_FOCUSSTACKBUNCH = "FocusStackBunch"
ACTION_MULTILAYER = "MultiLayer"
ACTION_TYPES = [ACTION_COMBO, ACTION_FOCUSSTACKBUNCH, ACTION_FOCUSSTACK, ACTION_MULTILAYER, ACTION_NOISEDETECTION]
SUB_ACTION_TYPES = ["MaskNoise", "Vignetting", "AlignFrames", "BalanceFrames"]
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
                 required: bool = False, **kwargs):
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
        self.layout.addRow(f"{label}:", widget)
        return widget

    def get_path_widget(self, widget):
        return widget.layout().itemAt(0).widget()

    def get_working_path(self):
        if 'working_path' in self.fields.keys():
            working_path = self.get_path_widget(self.fields['working_path']['widget']).text()
            if working_path != '':
                return working_path
        parent = self.action.parent
        if parent is not None and 'working_path' in parent.params.keys():
            return parent.params['working_path']
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
            elif field['type'] == FIELD_INT:
                params[tag] = field['widget'].value()
            elif field['type'] == FIELD_INT_TUPLE:
                params[tag] = [field['widget'].layout().itemAt(1 + i * 2).widget().value() for i in range(field['size'])]
            elif field['type'] == FIELD_COMBO:
                params[tag] = field['widget'].currentText()
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
                    if field.get('must_exist', False) and not os.path.exists(abs_path):
                        QMessageBox.warning(None, "Invalid Path",
                                            f"{field['label']} {abs_path} does not exist")
                        return                                  
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
        value = self.action.params.get(tag, '')
        edit = QLineEdit(value)
        edit.setPlaceholderText(kwargs.get('placeholder', ''))        
        button = QPushButton("Browse...")
        def browse():
            working_path = self.get_working_path()
            if not working_path:
                QMessageBox.warning(None, "Error", "Please set working path first")
                return
            path = QFileDialog.getExistingDirectory(
                None, 
                f"Select {tag.replace('_', ' ')}",
                working_path
            )
            if path:
                try:
                    rel_path = os.path.relpath(path, working_path)
                    if rel_path.startswith('..'):
                        QMessageBox.warning(None, "Invalid Path",
                                          f"{self.field['tag']['label']} must be a subdirectory of working path")
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

    def _create_int_tuple_field(self, tag, size=1, default=[0]*100, min=[0]*100, max=[100]*100, **kwargs):
        layout = QHBoxLayout()
        spins = [QSpinBox() for i in range(size)]
        labels = kwargs.get('labels', ('')*size)
        value = self.action.params.get(tag, default)
        for i, spin in enumerate(spins):
            spin.setRange(min[i], max[i])
            spin.setValue(value[i])
            spin.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            label = QLabel(labels[i] + ":")
            label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            layout.addWidget(label)
            layout.addWidget(spin)
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
        self.resize(500, self.height());
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
            # add more configurators here
        }
        return configurators.get(action_type, DefaultActionConfigurator())

    def accept(self):
        if self.configurator.update_params(self.action.params):
            super().accept()


class DefaultActionConfigurator(ActionConfigurator):
    def create_form(self, layout, action, tag='Action'):
        self.builder = FieldBuilder(layout, action)
        self.builder.add_field('name', FIELD_TEXT, f'{tag} name', required=True)
    
    def update_params(self, params):
        return self.builder.update_params(params)

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
        self.builder.add_field('input_path', FIELD_REL_PATH, 'Input path', required=False,
                               must_exist=True, placeholder='relative to working path')
        self.builder.add_field('output_path', FIELD_REL_PATH, 'Output path', required=False,
                               placeholder='relative to working path')
        self.builder.add_field('plot_path', FIELD_REL_PATH, 'Plots path', required=False,
                               placeholder='relative to working path')
        self.builder.add_field('channel_thresholds', FIELD_INT_TUPLE, 'Noise threshold', required=False, size=3,
                               default=[13, 13, 13], labels=['r', 'g', 'b'], min=[1]*3, max=[1000]*3)
        self.builder.add_field('blur_size', FIELD_INT, 'Blur size (px)', required=False,
                               default=5, min=1, max=50)
        self.builder.add_field('file_name', FIELD_TEXT, 'File name', required=False,
                               default="hot", placeholder="hot")
        self.builder.add_field('plot_range', FIELD_INT_TUPLE, 'Plot range', required=False, size=2, 
                               default=[5, 30], labels=['min', 'max'], min=[0]*2, max=[1000]*2)

class FocusStackConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=True)
        self.builder.add_field('input_path', FIELD_REL_PATH, 'Input path', required=False,
                               must_exist=True, placeholder='relative to working path')
        self.builder.add_field('output_path', FIELD_REL_PATH, 'Output path', required=False,
                               placeholder='relative to working path')

class FocusStackBunchConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=True)
        self.builder.add_field('input_path', FIELD_REL_PATH, 'Input path', required=False,
                               must_exist=True, placeholder='relative to working path')
        self.builder.add_field('output_path', FIELD_REL_PATH, 'Output path', required=False,
                               placeholder='relative to working path')
        
class MultiLayerConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=True)
        self.builder.add_field('input_path', FIELD_ABS_PATH, 'Input path', required=False,
                               must_exist=True, placeholder='relative to working path')
        self.builder.add_field('output_path', FIELD_REL_PATH, 'Output path', required=False,
                               placeholder='relative to working path')

class CombinedActionsConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        DefaultActionConfigurator.create_form(self, layout, action)
        self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=True)
        self.builder.add_field('input_path', FIELD_ABS_PATH, 'Input path', required=False,
                               must_exist=True, placeholder='relative to working path')
        self.builder.add_field('output_path', FIELD_REL_PATH, 'Output path', required=False,
                               placeholder='relative to working path')
        self.builder.add_field('plot_path', FIELD_REL_PATH, 'Plots path', required=False,
                               placeholder='relative to working path')
        self.builder.add_field('resample', FIELD_INT, 'Resample frames', required=False,
                              default=1, min=1, max=100)
        self.builder.add_field('ref_idx', FIELD_INT, 'Reference frame index', required=False,
                              default=-1, min=-1, max=1000)
        self.builder.add_field('step_process', FIELD_BOOL, 'Step process', required=False, default=True)
