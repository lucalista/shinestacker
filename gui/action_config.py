from PySide6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QVBoxLayout, QListWidget, QHBoxLayout,
    QFileDialog, QLabel, QComboBox, QMessageBox, QInputDialog,
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox)
from gui.project_model import Project, Job, ActionConfig
from abc import ABC, abstractmethod
from typing import Dict, Any
import os.path

COMBO_ACTIONS = "Combined Actions"
ACTION_TYPES = [COMBO_ACTIONS, "FocusStackBunch", "FocusStack", "MultiLayer", "NoiseDetection"]
SUB_ACTION_TYPES = ["MaskNoise", "Vignetting", "AlignFrames", "BalanceFrames"]


class ActionConfigurator(ABC):
    @abstractmethod
    def create_form(self, layout: QFormLayout, params: Dict[str, Any]):
        pass

    @abstractmethod
    def update_params(self, params: Dict[str, Any]):
        pass


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


class PathConfiguratorMixin:
    def add_path_fields(self, layout, params, fields):
        self.path_fields = {}   
        for param_name, label, required in fields:
            path_value = params.get(param_name, '')
            path_edit = QLineEdit(path_value)
            browse_button = QPushButton("Browse...")
            self.path_fields[param_name] = {
                'edit': path_edit,
                'button': browse_button,
                'required': required
            }
            path_layout = QHBoxLayout()
            path_layout.addWidget(path_edit)
            path_layout.addWidget(browse_button)
            layout.addRow(f"{label} (relative):", path_layout)
            browse_button.clicked.connect(
                lambda _, p=param_name: self._browse_path(p)
            )

    def _browse_path(self, param_name):
        working_path = self.working_path_edit.text() if hasattr(self, 'working_path_edit') else ""
        if not working_path and self.path_fields[param_name]['required']:
            QMessageBox.warning(None, "Error", "Please set working path first")
            return
        path = QFileDialog.getExistingDirectory(
            None, 
            f"Select {param_name.replace('_', ' ')} directory",
            working_path
        )
        if path:
            try:
                rel_path = os.path.relpath(path, working_path) if working_path else path
                if working_path and rel_path.startswith('..'):
                    QMessageBox.warning(None, "Invalid Path",
                                        f"{param_name} must be a subdirectory of working path")
                    return
                self.path_fields[param_name]['edit'].setText(rel_path)
            except ValueError:
                QMessageBox.warning(None, "Error", "Could not compute relative path")

    def update_path_params(self, params, working_path_field='working_path'):
        working_path = ""
        if hasattr(self, working_path_field + '_edit'):
            working_path = getattr(self, working_path_field + '_edit').text()
            params[working_path_field] = working_path   
        for param_name, widgets in self.path_fields.items():
            rel_path = widgets['edit'].text()
            params[param_name] = rel_path
            if widgets['required'] and not rel_path:
                QMessageBox.warning(None, "Error", f"{param_name} is required")
                return False
            if working_path and rel_path:
                try:
                    abs_path = os.path.normpath(os.path.join(working_path, rel_path))
                    if not abs_path.startswith(os.path.normpath(working_path)):
                        QMessageBox.warning(None, "Invalid Path", 
                                           f"{param_name} must be a subdirectory of working path")
                        return False
                except Exception as e:
                    QMessageBox.warning(None, "Error", f"Invalid path: {str(e)}")
                    return False
        return True


class BasicPathConfigurator(ActionConfigurator, PathConfiguratorMixin):
    def create_form(self, layout, params):
        working_path = params.get('working_path', '')
        self.working_path_edit = QLineEdit(working_path)
        working_path_button = QPushButton("Browse...")
        working_path_button.clicked.connect(self._browse_working_path)
        working_layout = QHBoxLayout()
        working_layout.addWidget(self.working_path_edit)
        working_layout.addWidget(working_path_button)
        layout.addRow("Working Path:", working_layout)
        self.add_path_fields(layout, params, [
            ('input_path', 'Input Path', True),
            ('plot_path', 'Plot Path', False),
            ('exif_path', 'EXIF Path', False)
        ])
    
    def update_params(self, params):
        return self.update_path_params(params)
    
    def _browse_working_path(self):
        path = QFileDialog.getExistingDirectory(None, "Select Working Directory")
        if path:
            self.working_path_edit.setText(path)


class OutputOnlyConfigurator(ActionConfigurator, PathConfiguratorMixin):
    def create_form(self, layout, params):
        self.add_path_fields(layout, params, [
            ('output_path', 'Output Path', True)
        ])
    
    def update_params(self, params):
        return self.update_path_params(params, working_path_field=None)


class DefaultActionConfigurator(ActionConfigurator):
    def create_form(self, layout, params, label="Action"):
        if 'name' not in params:
            params['name'] = ''
        self.name_edit = QLineEdit(params['name'])
        layout.addRow(f"{label} name:", self.name_edit)

    def update_params(self, params):
        params['name'] = self.name_edit.text()
        return True


class JobConfigurator(DefaultActionConfigurator, PathConfiguratorMixin):
    def create_form(self, layout, params):
        DefaultActionConfigurator.create_form(self, layout, params, "Job")
        working_path = params.get('working_path', '')
        self.working_path_edit = QLineEdit(working_path)
        working_path_button = QPushButton("Browse...")
        working_path_button.clicked.connect(self._browse_working_path)
        working_layout = QHBoxLayout()
        working_layout.addWidget(self.working_path_edit)
        working_layout.addWidget(working_path_button)
        layout.addRow("Working Path:", working_layout)
        self.add_path_fields(layout, params, [
            ('input_path', 'Input Path', False),
        ])

    def update_params(self, params):
        DefaultActionConfigurator.update_params(self, params)
        return self.update_path_params(params)
    
    def _browse_working_path(self):
        path = QFileDialog.getExistingDirectory(None, "Select Working Directory")
        if path:
            self.working_path_edit.setText(path)

class NoiseDetectionConfigurator(ActionConfigurator, PathConfiguratorMixin):
    def create_form(self, layout, params):
        DefaultActionConfigurator().create_form(layout, params)
        working_path = params.get('working_path', '')
        self.working_path_edit = QLineEdit(working_path)
        working_path_button = QPushButton("Browse...")
        working_path_button.clicked.connect(self._browse_working_path)
        working_layout = QHBoxLayout()
        working_layout.addWidget(self.working_path_edit)
        working_layout.addWidget(working_path_button)
        layout.addRow("Working Path:", working_layout)
        self.add_path_fields(layout, params, [
            ('input_path', 'Input Path', True),
            ('noise_map_path', 'Noise Map Path', False)
        ])
        threshold = params.get('threshold', 0.5)
        threshold_spin = QDoubleSpinBox()
        threshold_spin.setValue(threshold)
        threshold_spin.setRange(0, 1)
        threshold_spin.setSingleStep(0.1)
        layout.addRow("Noise threshold:", threshold_spin)
        self.threshold_spin = threshold_spin
    
    def update_params(self, params):
        if not self.update_path_params(params):
            return False
        params['threshold'] = self.threshold_spin.value()
        return True
    
    def _browse_working_path(self):
        path = QFileDialog.getExistingDirectory(None, "Select Working Directory")
        if path:
            self.working_path_edit.setText(path)


class FocusStackConfigurator(ActionConfigurator):
    def create_form(self, layout, params):
        DefaultActionConfigurator().create_form(layout, params)
        method = params.get('method', 'pyramids')
        method_combo = QComboBox()
        method_combo.addItems(['pyramids', 'depth map'])
        method_combo.setCurrentText(method)
        layout.addRow("Stacking method:", method_combo)
        self.method_combo = method_combo

    def update_params(self, params):
        params['method'] = self.method_combo.currentText()
        return True

class MultiLayerConfigurator(ActionConfigurator):
    def create_form(self, layout, params):
        DefaultActionConfigurator().create_form(layout, params)

        layers = params.get('layers', 3)
        layers_spin = QSpinBox()
        layers_spin.setValue(layers)
        layers_spin.setRange(1, 10)
        layout.addRow("Number of layers:", layers_spin)
        self.layers_spin = layers_spin

        blend_mode = params.get('blend_mode', 'normal')
        blend_combo = QComboBox()
        blend_combo.addItems(['normal', 'multiply', 'screen'])
        blend_combo.setCurrentText(blend_mode)
        layout.addRow("Blend mode:", blend_combo)
        self.blend_combo = blend_combo

    def update_params(self, params):
        params['layers'] = self.layers_spin.value()
        params['blend_mode'] = self.blend_combo.currentText()
        return True

class CombinedActionsConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, params):
        DefaultActionConfigurator.create_form(self, layout, params)
