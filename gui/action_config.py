from PySide6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QVBoxLayout, QListWidget, QHBoxLayout,
    QFileDialog, QLabel, QComboBox, QMessageBox, QInputDialog,
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox)
from gui.project_model import Project, ActionConfig
from abc import ABC, abstractmethod
from typing import Dict, Any
import os.path

COMBO_ACTIONS = "Combined Actions"
ACTION_TYPES = [COMBO_ACTIONS, "FocusStackBunch", "FocusStack", "MultiLayer", "NoiseDetection"]
SUB_ACTION_TYPES = ["MaskNoise", "Vignetting", "AlignFrames", "BalanceFrames"]
FIELD_TEXT = 'text'
FIELD_ABS_PATH = 'abs_path'
FIELD_REL_PATH = 'rel_path'
FIELD_FLOAT = 'float'
FIELD_INT = 'int'
FIELD_COMBO = 'combo'
FIELD_TYPES = [FIELD_TEXT, FIELD_ABS_PATH, FIELD_REL_PATH, FIELD_FLOAT, FIELD_INT, FIELD_COMBO]

class ActionConfigurator(ABC):
    @abstractmethod
    def create_form(self, layout: QFormLayout, params: Dict[str, Any]):
        pass

    @abstractmethod
    def update_params(self, params: Dict[str, Any]):
        pass

class FieldBuilder:
    def __init__(self, layout, params):
        self.layout = layout
        self.params = params
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
        elif field_type == FIELD_COMBO:
            widget = self._create_combo_field(tag, **kwargs)
        else:
            raise ValueError(f"Unknown field type: {field_type}")
        
        self.fields[tag] = {
            'widget': widget,
            'type': field_type,
            'required': required,
            **kwargs
        }
        self.layout.addRow(f"{label}:", widget)
        return widget

    def get_working_path(self):
        if 'working_path' not in self.fields.keys():
            return ''
        return self.fields['working_path']['widget'].itemAt(0).widget().text()
    
    def update_params(self, params: Dict[str, Any]) -> bool:
        for tag, field in self.fields.items():
            if field['type'] == FIELD_TEXT:
                params[tag] = field['widget'].text()
            elif field['type'] in (FIELD_ABS_PATH, FIELD_REL_PATH):
                params[tag] = field['widget'].itemAt(0).widget().text()
            elif field['type'] == FIELD_FLOAT:
                params[tag] = field['widget'].value()
            elif field['type'] == FIELD_INT:
                params[tag] = field['widget'].value()
            elif field['type'] == FIELD_COMBO:
                params[tag] = field['widget'].currentText()
            if field['required'] and not params[tag]:
                QMessageBox.warning(None, "Error", f"{tag} is required")
                return False
            if field['type'] == FIELD_REL_PATH and 'working_path' in params:
                try:
                    working_path = self.get_working_path()
                    abs_path = os.path.normpath(os.path.join(working_path, params[tag]))
                    if not abs_path.startswith(os.path.normpath(working_path)):
                        QMessageBox.warning(None, "Invalid Path", 
                                           f"{tag} must be a subdirectory of working path")
                        return False
                except Exception as e:
                    QMessageBox.warning(None, "Error", f"Invalid path: {str(e)}")
                    return False
        return True
    
    def _create_text_field(self, tag, **kwargs):
        value = self.params.get(tag, '')
        edit = QLineEdit(value)
        return edit
        
    def _create_abs_path_field(self, tag, **kwargs):
        value = self.params.get(tag, '')
        edit = QLineEdit(value)
        button = QPushButton("Browse...")
        def browse():
            path = QFileDialog.getExistingDirectory(None, f"Select {tag.replace('_', ' ')}")
            if path:
                edit.setText(path)
        button.clicked.connect(browse)
        layout = QHBoxLayout()
        layout.addWidget(edit)
        layout.addWidget(button)
        return layout
    
    def _create_rel_path_field(self, tag, **kwargs):
        value = self.params.get(tag, '')
        edit = QLineEdit(value)
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
                                          f"{tag} must be a subdirectory of working path")
                        return
                    edit.setText(rel_path)
                except ValueError:
                    QMessageBox.warning(None, "Error", "Could not compute relative path")
        
        button.clicked.connect(browse)
        layout = QHBoxLayout()
        layout.addWidget(edit)
        layout.addWidget(button)
        return layout
    
    def _create_float_field(self, tag, default=0.0, min=0.0, max=1.0, step=0.1, **kwargs):
        value = self.params.get(tag, default)
        spin = QDoubleSpinBox()
        spin.setValue(value)
        spin.setRange(min, max)
        spin.setSingleStep(step)
        return spin
    
    def _create_int_field(self, tag, default=1, min=1, max=10, **kwargs):
        value = self.params.get(tag, default)
        spin = QSpinBox()
        spin.setValue(value)
        spin.setRange(min, max)
        return spin
    
    def _create_combo_field(self, tag, options=None, default=None, **kwargs):
        options = options or []
        value = self.params.get(tag, default or options[0] if options else '')
        combo = QComboBox()
        combo.addItems(options)
        if value in options:
            combo.setCurrentText(value)
        return combo


class ActionConfigDialog(QDialog):
    def __init__(self, action: ActionConfig, parent=None):
        super().__init__(parent)
        self.action = action
        self.setWindowTitle(f"Configure {action.type_name}")
        self.configurator = self._get_configurator(action.type_name)
        self.layout = QFormLayout(self)
        self.configurator.create_form(self.layout, action.params)
        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        self.layout.addRow(button_box)
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

    def _get_configurator(self, action_type: str) -> ActionConfigurator:
        configurators = {
            "Job": JobConfigurator(),
            COMBO_ACTIONS: CombinedActionsConfigurator(),
            "NoiseDetection": NoiseDetectionConfigurator(),
            "FocusStack": FocusStackConfigurator(),
            "MultiLayer": MultiLayerConfigurator(),
            # add more configurators here
        }
        return configurators.get(action_type, DefaultActionConfigurator())

    def accept(self):
        if self.configurator.update_params(self.action.params):
            super().accept()


class DefaultActionConfigurator(ActionConfigurator):
    def create_form(self, layout, params, tag='Action'):
        self.builder = FieldBuilder(layout, params)
        self.builder.add_field('name', FIELD_TEXT, f'{tag} name', required=True)
    
    def update_params(self, params):
        return self.builder.update_params(params)

class JobConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, params):
        super().create_form(layout, params, "Job")
        self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=True)
        self.builder.add_field('input_path', FIELD_REL_PATH, 'Input rel. path', required=False)

class NoiseDetectionConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, params):
        super().create_form(layout, params, "Job")
        self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=True)
        self.builder.add_field('input_path', FIELD_REL_PATH, 'Input rel. path', required=False)

class FocusStackConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, params):
        super().create_form(layout, params, "Job")
        self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=True)
        self.builder.add_field('input_path', FIELD_REL_PATH, 'Input rel. path', required=False)
        self.builder.add_field('output_path', FIELD_REL_PATH, 'Output rel. path', required=False)

class MultiLayerConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, params):
        super().create_form(layout, params, "Job")
        self.builder.add_field('working_path', FIELD_ABS_PATH, 'Working path', required=True)
        self.builder.add_field('input_path', FIELD_ABS_PATH, 'Input rel. path', required=False)
        self.builder.add_field('output_path', FIELD_REL_PATH, 'Output rel. path', required=False)

class CombinedActionsConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, params):
        DefaultActionConfigurator.create_form(self, layout, params)
