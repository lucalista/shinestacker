# pylint: disable=C0114, C0115, C0116, E0611, R0913, R0917, E1121
import os
from abc import ABC, abstractmethod
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel, QCheckBox, QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit, QPushButton,
    QHBoxLayout, QWidget, QFileDialog)
from .. config.settings import Settings
from .. config.constants import constants
from .. config.gui_constants import gui_constants
from .. config.defaults import DEFAULTS
from .. gui.config_dialog import ConfigDialog
from .. gui.action_config import add_tab, create_tab_widget
from .. gui.action_config_dialog import AlignFramesConfigBase


class BaseParameter(ABC):
    def __init__(self, key, label, tooltip=""):
        self.key = key
        self.label = label
        self.tooltip = tooltip
        self.widget = None

    @abstractmethod
    def create_widget(self, parent):
        pass

    @abstractmethod
    def get_value(self):
        pass

    @abstractmethod
    def set_value(self, value):
        pass

    @abstractmethod
    def set_default(self):
        pass


class NestedParameter(BaseParameter):
    def __init__(self, parent_key, key, label, tooltip=""):
        super().__init__(key, label, tooltip)
        self.parent_key = parent_key

    def get_nested_value(self, settings):
        return settings.get(self.parent_key).get(self.key)

    def set_nested_value(self, settings, value):
        nested_dict = settings.get(self.parent_key).copy()
        nested_dict[self.key] = value
        settings.set(self.parent_key, nested_dict)


class CheckBoxParameter(BaseParameter):
    def __init__(self, key, label, default_value, tooltip=""):
        super().__init__(key, label, tooltip)
        self.default_value = default_value

    def create_widget(self, parent):
        self.widget = QCheckBox(parent)
        if self.tooltip:
            self.widget.setToolTip(self.tooltip)
        return self.widget

    def get_value(self):
        return self.widget.isChecked()

    def set_value(self, value):
        self.widget.setChecked(value)

    def set_default(self):
        self.widget.setChecked(self.default_value)


class SpinBoxParameter(BaseParameter):
    def __init__(self, key, label, default_value, min_val, max_val, step=1, tooltip=""):
        super().__init__(key, label, tooltip)
        self.default_value = default_value
        self.min_val = min_val
        self.max_val = max_val
        self.step = step

    def create_widget(self, parent):
        self.widget = QSpinBox(parent)
        self.widget.setRange(self.min_val, self.max_val)
        self.widget.setSingleStep(self.step)
        if self.tooltip:
            self.widget.setToolTip(self.tooltip)
        return self.widget

    def get_value(self):
        return self.widget.value()

    def set_value(self, value):
        self.widget.setValue(value)

    def set_default(self):
        self.widget.setValue(self.default_value)


class DoubleSpinBoxParameter(SpinBoxParameter):
    def create_widget(self, parent):
        self.widget = QDoubleSpinBox(parent)
        self.widget.setRange(self.min_val, self.max_val)
        self.widget.setSingleStep(self.step)
        if self.tooltip:
            self.widget.setToolTip(self.tooltip)
        return self.widget


class ComboBoxParameter(BaseParameter):
    def __init__(self, key, label, default_value, options, tooltip=""):
        super().__init__(key, label, tooltip)
        self.default_value = default_value
        self.options = options

    def create_widget(self, parent):
        self.widget = QComboBox(parent)
        for display_text, data in self.options:
            self.widget.addItem(display_text, data)
        if self.tooltip:
            self.widget.setToolTip(self.tooltip)
        return self.widget

    def get_value(self):
        return self.widget.itemData(self.widget.currentIndex())

    def set_value(self, value):
        idx = self.widget.findData(value)
        if idx >= 0:
            self.widget.setCurrentIndex(idx)

    def set_default(self):
        idx = self.widget.findData(self.default_value)
        if idx >= 0:
            self.widget.setCurrentIndex(idx)


class CallbackComboBoxParameter(ComboBoxParameter):
    def __init__(self, key, label, default_value, options, tooltip="", on_change=None):
        super().__init__(key, label, default_value, options, tooltip)
        self.on_change = on_change

    def create_widget(self, parent):
        widget = super().create_widget(parent)
        if self.on_change:
            widget.currentIndexChanged.connect(self.on_change)
        return widget


class NestedSpinBoxParameter(SpinBoxParameter, NestedParameter):
    def __init__(self, parent_key, key, label, default_value, min_val, max_val, step=1, tooltip=""):
        SpinBoxParameter.__init__(
            self, key, label, default_value, min_val, max_val, step, tooltip)
        NestedParameter.__init__(
            self, parent_key, key, label, tooltip)


class NestedDoubleSpinBoxParameter(DoubleSpinBoxParameter, NestedParameter):
    def __init__(self, parent_key, key, label, default_value, min_val, max_val, step=1, tooltip=""):
        DoubleSpinBoxParameter.__init__(
            self, key, label, default_value, min_val, max_val, step, tooltip)
        NestedParameter.__init__(
            self, parent_key, key, label, tooltip)


class NestedCallbackComboBoxParameter(CallbackComboBoxParameter, NestedParameter):
    def __init__(self, parent_key, key, label, default_value,
                 options, tooltip="", on_change=None):
        CallbackComboBoxParameter.__init__(
            self, key, label, default_value, options, tooltip, on_change)
        NestedParameter.__init__(self, parent_key, key, label, tooltip)


class NestedCheckBoxParameter(CheckBoxParameter, NestedParameter):
    def __init__(self, parent_key, key, label, default_value,
                 tooltip=""):
        CheckBoxParameter.__init__(
            self, key, label, default_value, tooltip)
        NestedParameter.__init__(self, parent_key, key, label, tooltip)


class FolderParameter(BaseParameter):
    def __init__(self, key, label, default_value="", tooltip=""):
        super().__init__(key, label, tooltip)
        self.default_value = default_value
        self.line_edit = None
        self.browse_button = None

    def create_widget(self, parent):
        container = QWidget(parent)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        self.line_edit = QLineEdit(container)
        if self.tooltip:
            self.line_edit.setToolTip(self.tooltip)
        self.browse_button = QPushButton("Browse...", container)
        self.browse_button.clicked.connect(self._browse_folder)
        layout.addWidget(self.line_edit)
        layout.addWidget(self.browse_button)
        self.widget = container
        return self.widget

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self.widget,
            f"Select {self.label}",
            self.line_edit.text() or os.path.expanduser("~")
        )
        if folder:
            self.line_edit.setText(os.path.normpath(folder))

    def get_value(self):
        return self.line_edit.text()

    def set_value(self, value):
        self.line_edit.setText(value)

    def set_default(self):
        self.line_edit.setText(self.default_value)


class NestedFolderParameter(FolderParameter, NestedParameter):
    def __init__(self, parent_key, key, label, default_value="", tooltip=""):
        FolderParameter.__init__(self, key, label, default_value, tooltip)
        NestedParameter.__init__(self, parent_key, key, label, tooltip)


class SettingsDialog(ConfigDialog, AlignFramesConfigBase):
    update_project_config_requested = Signal()
    update_retouch_config_requested = Signal()

    def __init__(self, parent=None, project_settings=True, retouch_settings=True):
        AlignFramesConfigBase.__init__(self)
        self.project_settings = project_settings
        self.retouch_settings = retouch_settings
        self.settings = Settings.instance()
        self.project_parameters = []
        self.retouch_parameters = []
        self._init_parameters()
        super().__init__("Settings", parent)

    def _init_parameters(self):
        if self.project_settings:
            self.project_parameters = [
                ("General", [
                    CheckBoxParameter(
                        'check_for_updates', 'Check for updates:',
                        DEFAULTS['check_for_updates']),
                    ComboBoxParameter(
                        'project_view_strategy', 'View strategy:',
                        DEFAULTS['project_view_strategy'],
                        [
                            ("Modern Horizontal", "modern_horizontal"),
                            ("Modern Vertical", "modern_vertical"),
                            ("Classic", "classic"),
                        ]),
                    CheckBoxParameter(
                        'expert_options', 'Expert options:',
                        DEFAULTS['expert_options']),
                    ComboBoxParameter(
                        'plots_format', 'Plots format:',
                        DEFAULTS['plots_format'],
                        [
                            ("PNG", "png"),
                            ("JPEG", "jpg"),
                            ("PDF", "pdf")
                        ]
                    ),
                    FolderParameter(
                        'input_folder_path', 'Input folder path:',
                        DEFAULTS['input_folder_path'],
                        'Path of the folder that is opened by default '
                        'when a new project is created.'),
                    FolderParameter(
                        'temp_folder_path', 'Scratch disk folder:',
                        DEFAULTS['temp_folder_path'],
                        'Temporary folder for processing files.\n'
                        'Using a fast drive (SSD recommended) \n'
                        'with ample free space will improve\nperformance.'),
                    CheckBoxParameter(
                        'retouch_after_run', 'Run retouch after run',
                        DEFAULTS['retouch_after_run'])
                ]),
                ("Raw Formats", [
                    NestedCheckBoxParameter(
                        'raw_formats', 'auto_bright', 'Automatic brightness:',
                        DEFAULTS['raw_formats']['auto_bright']),
                    NestedDoubleSpinBoxParameter(
                        'raw_formats', 'auto_bright_thr', 'Auto-brightness threshold (%)',
                        DEFAULTS['raw_formats']['auto_bright'], 0.0, 100.0, 0.1)
                ]),
                ("Combined Actions", [
                    NestedSpinBoxParameter(
                        'combined_actions_params', 'max_threads',
                        'Max num. of cores:',
                        DEFAULTS['combined_actions_params']['max_threads'], 0, 256)
                ]),
                ("Align Frames", [
                    NestedDoubleSpinBoxParameter(
                        'align_frames_params', 'memory_limit',
                        'Mem. limit (approx., GBytes):',
                        DEFAULTS['align_frames_params']['memory_limit'], 1.0, 1024.0, 1.0),
                    NestedSpinBoxParameter(
                        'align_frames_params', 'max_threads',
                        'Max num. of cores:',
                        DEFAULTS['align_frames_params']['max_threads'], 0, 256),
                    NestedCallbackComboBoxParameter(
                        'align_frames_params', 'transform', 'Transform:',
                        DEFAULTS['align_frames_params']['transform'],
                        list(zip(self.TRANSFORM_OPTIONS, constants.VALID_TRANSFORMS))),
                    NestedCallbackComboBoxParameter(
                        'align_frames_params', 'detector', 'Detector:',
                        DEFAULTS['align_frames_params']['detector'],
                        [(d, d) for d in constants.VALID_DETECTORS],
                        tooltip=self.DETECTOR_DESCRIPTOR_TOOLTIPS['detector'],
                        on_change=self.change_match_config_settings),
                    NestedCallbackComboBoxParameter(
                        'align_frames_params', 'descriptor', 'Descriptor:',
                        DEFAULTS['align_frames_params']['descriptor'],
                        [(d, d) for d in constants.VALID_DESCRIPTORS],
                        tooltip=self.DETECTOR_DESCRIPTOR_TOOLTIPS['descriptor'],
                        on_change=self.change_match_config_settings),
                    NestedCallbackComboBoxParameter(
                        'align_frames_params', 'match_method', 'Match method:',
                        DEFAULTS['align_frames_params']['match_method'],
                        list(zip(self.MATCHING_METHOD_OPTIONS, constants.VALID_MATCHING_METHODS)),
                        tooltip=self.DETECTOR_DESCRIPTOR_TOOLTIPS['match_method']),
                    NestedCallbackComboBoxParameter(
                        'align_frames_params', 'subsample', 'Subsample:',
                        DEFAULTS['align_frames_params']['subsample'],
                        list(zip(constants.FIELD_SUBSAMPLE_OPTIONS,
                                 constants.FIELD_SUBSAMPLE_VALUES)))
                ]),
                ("Focus Stacking", [
                    NestedDoubleSpinBoxParameter(
                        'focus_stack_params', 'memory_limit',
                        'Mem. limit (approx., GBytes):',
                        DEFAULTS['focus_stack_params']['memory_limit'], 1.0, 1024.0, 1.0),
                    NestedSpinBoxParameter(
                        'focus_stack_params', 'max_threads', 'Max. num. of cores:',
                        DEFAULTS['focus_stack_params']['max_threads'], 0, 256)
                ])
            ]
        if self.retouch_settings:
            self.retouch_parameters = [
                ("General", [
                    ComboBoxParameter(
                        'retouch_view_strategy', 'View strategy:',
                        DEFAULTS['retouch_view_strategy'],
                        [
                            ("Overlaid", "overlaid"),
                            ("Side by side", "sidebyside"),
                            ("Top-Bottom", "topbottom")
                        ])
                ]),
                ("Brush Options", [
                    SpinBoxParameter(
                        'brush_size', 'Brush initial size:',
                        DEFAULTS['brush_size'],
                        gui_constants.BRUSH_SIZES['min'], gui_constants.BRUSH_SIZES['max']),
                    DoubleSpinBoxParameter(
                        'min_mouse_step_brush_fraction', 'Min. mouse step in brush units:',
                        DEFAULTS['min_mouse_step_brush_fraction'], 0, 1, 0.02)
                ]),
                ("Refresh Times", [
                    SpinBoxParameter(
                        'paint_refresh_time', 'Paint refresh time:',
                        DEFAULTS['paint_refresh_time'], 0, 1000),
                    SpinBoxParameter(
                        'display_refresh_time', 'Display refresh time:',
                        DEFAULTS['display_refresh_time'], 0, 200),
                    SpinBoxParameter(
                        'cursor_update_time', 'Cursor refresh time:',
                        DEFAULTS['cursor_update_time'], 0, 50)
                ])
            ]

    def create_form_content(self):
        self.tab_widget = create_tab_widget(self.container_layout)
        if self.project_settings:
            project_tab_layout = add_tab(self.tab_widget, "Project Settings")
            self.create_project_settings(project_tab_layout)
        if self.retouch_settings:
            retouch_tab_layout = add_tab(self.tab_widget, "Retouch Settings")
            self.create_retouch_settings(retouch_tab_layout)

    def create_project_settings(self, layout=None):
        if layout is None:
            layout = self.container_layout
        for group_name, parameters in self.project_parameters:
            label = QLabel(group_name + ":")
            label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            layout.addRow(label)
            for param in parameters:
                widget = param.create_widget(self)
                param.set_value(self._get_current_value(param))
                layout.addRow(param.label, widget)
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: orange; font-style: italic;")
        layout.addRow(self.info_label)

    def create_retouch_settings(self, layout=None):
        if layout is None:
            layout = self.container_layout
        for group_name, parameters in self.retouch_parameters:
            label = QLabel(group_name + ":")
            label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            layout.addRow(label)
            for param in parameters:
                widget = param.create_widget(self)
                param.set_value(self._get_current_value(param))
                layout.addRow(param.label, widget)

    def _get_current_value(self, param):
        if isinstance(param, NestedParameter):
            return param.get_nested_value(self.settings)
        return self.settings.get(param.key)

    def _set_current_value(self, param, value):
        if isinstance(param, NestedParameter):
            param.set_nested_value(self.settings, value)
        else:
            self.settings.set(param.key, value)

    def change_match_config_settings(self):
        detector_widget = None
        descriptor_widget = None
        matching_method_widget = None
        for _group_name, parameters in self.project_parameters:
            for param in parameters:
                if (isinstance(param, NestedParameter) and
                        param.parent_key == 'align_frames_params'):
                    if param.key == 'detector':
                        detector_widget = param.widget
                    elif param.key == 'descriptor':
                        descriptor_widget = param.widget
                    elif param.key == 'match_method':
                        matching_method_widget = param.widget
        if detector_widget and descriptor_widget and matching_method_widget:
            self.change_match_config(
                detector_widget, descriptor_widget, matching_method_widget, self.show_info)

    def accept(self):
        for _group_name, parameters in self.project_parameters:
            for param in parameters:
                self._set_current_value(param, param.get_value())
        for _group_name, parameters in self.retouch_parameters:
            for param in parameters:
                self._set_current_value(param, param.get_value())
        self.settings.update()
        if self.project_settings:
            self.update_project_config_requested.emit()
        if self.retouch_settings:
            self.update_retouch_config_requested.emit()
        super().accept()

    def reset_to_defaults(self):
        for _group_name, parameters in self.project_parameters:
            for param in parameters:
                param.set_default()
        for _group_name, parameters in self.retouch_parameters:
            for param in parameters:
                param.set_default()


def show_settings_dialog(
        parent, project_settings, retouch_settings, handle_project_config, handle_retouch_config):
    dialog = SettingsDialog(parent, project_settings, retouch_settings)
    dialog.update_project_config_requested.connect(handle_project_config)
    dialog.update_retouch_config_requested.connect(handle_retouch_config)
    dialog.exec()
