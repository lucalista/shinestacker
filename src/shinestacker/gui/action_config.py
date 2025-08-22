# pylint: disable=C0114, C0115, C0116, E0611, R0913, R0917, R0915, R0912
# pylint: disable=E0606, W0718, R1702, W0102, W0221
import traceback
from abc import ABC, abstractmethod
from typing import Dict, Any
import os.path
from PySide6.QtWidgets import (QPushButton, QHBoxLayout, QFileDialog, QLabel, QComboBox,
                               QMessageBox, QSizePolicy, QLineEdit, QSpinBox,
                               QDoubleSpinBox, QCheckBox, QTreeView, QAbstractItemView, QListView)
from .. config.constants import constants
from .select_path_widget import (create_select_file_paths_widget, create_layout_widget_no_margins,
                                 create_layout_widget_and_connect)
from .project_model import ActionConfig

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
    def create_form(self, layout, action: ActionConfig, tag="Action"):
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
