# pylint: disable=C0114, C0115, C0116, E0611, R0913, R0917, R0915, R0912
# pylint: disable=E0606, W0718, R1702, W0102, W0221, R0914, E1121, R0911
import traceback
from abc import ABC, abstractmethod
import os.path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QPushButton, QHBoxLayout, QFileDialog, QLabel, QComboBox,
                               QMessageBox, QSizePolicy, QLineEdit, QSpinBox, QFrame,
                               QDoubleSpinBox, QCheckBox, QTreeView, QAbstractItemView, QListView,
                               QWidget, QScrollArea, QFormLayout, QDialog, QTabWidget)
from .. config.constants import constants
from .select_path_widget import (create_select_file_paths_widget, create_layout_widget_no_margins,
                                 create_layout_widget_and_connect)

FIELD_TEXT = 'text'
FIELD_ABS_PATH = 'abs_path'
FIELD_REL_PATH = 'rel_path'
FIELD_FLOAT = 'float'
FIELD_INT = 'int'
FIELD_REF_IDX = 'ref_idx'
FIELD_INT_TUPLE = 'int_tuple'
FIELD_BOOL = 'bool'
FIELD_COMBO = 'combo'
FIELD_TYPES = [FIELD_TEXT, FIELD_ABS_PATH, FIELD_REL_PATH, FIELD_FLOAT,
               FIELD_INT, FIELD_INT_TUPLE, FIELD_BOOL, FIELD_COMBO]

FIELD_REF_IDX_OPTIONS = ['Median frame', 'First frame', 'Last frame', 'Specify index']
FIELD_REF_IDX_MAX = 1000


class ActionConfigurator(ABC):
    def __init__(self, current_wd):
        self.current_wd = current_wd

    @abstractmethod
    def create_form(self, main_layout, action, tag="Action"):
        pass

    @abstractmethod
    def update_params(self, params):
        pass


class FieldBuilder:
    def __init__(self, main_layout, action, current_wd):
        self.main_layout = main_layout
        self.action = action
        self.current_wd = current_wd
        self.fields = {}

    def add_field(self, tag, field_type, label,
                  required=False, add_to_layout=None, do_add=True, **kwargs):
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
        elif field_type == FIELD_REF_IDX:
            widget = self.create_ref_idx_field(tag, **kwargs)
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
            elif field_type == FIELD_REF_IDX:
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
        if do_add:
            if add_to_layout is None:
                add_to_layout = self.main_layout
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
                elif field['type'] == FIELD_REF_IDX:
                    widget.layout().itemAt(2).widget().setValue(default)
                    widget.layout().itemAt(0).widget().setCurrentText(FIELD_REF_IDX_OPTIONS[0])
                elif field['type'] == FIELD_INT_TUPLE:
                    for i in range(field['size']):
                        spinbox = widget.layout().itemAt(1 + i * 2).widget()
                        spinbox.setValue(default[i])
                elif field['type'] == FIELD_COMBO:
                    widget.setCurrentText(str(default))

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

    def update_params(self, params):
        has_relative_paths = any(
            field['type'] == FIELD_REL_PATH
            and not field.get('skip_working_path_check', False)
            for field in self.fields.values()
        )
        if has_relative_paths:
            working_path = self.get_working_path()
            if not working_path:
                QMessageBox.warning(
                    None, "Error",
                    "This job contains relative paths but no working path is set. "
                    "Please set a working path first."
                )
                return False
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
            elif field['type'] == FIELD_REF_IDX:
                wl = field['widget'].layout()
                txt = wl.itemAt(0).widget().currentText()
                if txt == FIELD_REF_IDX_OPTIONS[0]:
                    params[tag] = 0
                elif txt == FIELD_REF_IDX_OPTIONS[1]:
                    params[tag] = 1
                elif txt == FIELD_REF_IDX_OPTIONS[2]:
                    params[tag] = -1
                else:
                    params[tag] = wl.itemAt(2).widget().value()
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
                if field.get('skip_working_path_check', False):
                    continue
                try:
                    working_path = self.get_working_path()
                    if not working_path:
                        QMessageBox.warning(
                            None, "Error",
                            f"{field['label']} requires a valid working path to be set"
                        )
                        return False
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
                    traceback.print_exc()
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
        )

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
                if not os.path.exists(working_path):
                    QMessageBox.warning(None, "Error",
                                        f"Working path '{working_path}' does not exist.")
                    return
                if path_type == 'directory':
                    dialog = QFileDialog()
                    dialog.setWindowTitle(f"Select {label} (multiple selection allowed)")
                    dialog.setDirectory(working_path)
                    dialog.setFileMode(QFileDialog.Directory)
                    dialog.setOption(QFileDialog.DontUseNativeDialog, True)
                    dialog.setOption(QFileDialog.ShowDirsOnly, True)
                    if hasattr(dialog, 'setSupportedSchemes'):
                        dialog.setSupportedSchemes(['file'])
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
                            except ValueError:
                                traceback.print_exc()
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
                            except ValueError:
                                traceback.print_exc()
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
                if not os.path.exists(working_path):
                    QMessageBox.warning(None, "Error",
                                        f"Working path '{working_path}' does not exist.")
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
                        traceback.print_exc()
                        QMessageBox.warning(None, "Error", "Could not compute relative path")
        return create_layout_widget_and_connect(button, edit, browse)

    def create_float_field(self, tag, default=0.0, min_val=0.0, max_val=1.0,
                           step=0.1, decimals=2):
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(self.action.params.get(tag, default))
        spin.setDecimals(decimals)
        spin.setSingleStep(step)
        return spin

    def create_int_field(self, tag, default=0, min_val=0, max_val=100):
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(self.action.params.get(tag, default))
        return spin

    def create_ref_idx_field(self, tag, default=0):
        layout = QHBoxLayout()
        combo = QComboBox()
        combo.addItems(FIELD_REF_IDX_OPTIONS)
        label = QLabel("index [1, ..., N]: ")
        spin = QSpinBox()
        spin.setRange(1, FIELD_REF_IDX_MAX)
        value = self.action.params.get(tag, default)
        if value == 0:
            combo.setCurrentText(FIELD_REF_IDX_OPTIONS[0])
            spin.setValue(1)
        elif value == 1:
            combo.setCurrentText(FIELD_REF_IDX_OPTIONS[1])
            spin.setValue(1)
        elif value == -1:
            combo.setCurrentText(FIELD_REF_IDX_OPTIONS[2])
            spin.setValue(1)
        else:
            combo.setCurrentText(FIELD_REF_IDX_OPTIONS[3])
            spin.setValue(value)

        def set_enabled():
            spin.setEnabled(combo.currentText() == FIELD_REF_IDX_OPTIONS[-1])

        combo.currentTextChanged.connect(set_enabled)
        set_enabled()
        layout.addWidget(combo)
        layout.addWidget(label)
        layout.addWidget(spin)
        return create_layout_widget_no_margins(layout)

    def create_int_tuple_field(self, tag, size=1,
                               default=[0] * 100, min_val=[0] * 100, max_val=[100] * 100,
                               **kwargs):
        layout = QHBoxLayout()
        spins = [QSpinBox() for i in range(size)]
        labels = kwargs.get('labels', ('') * size)
        value = self.action.params.get(tag, default)
        vals = list(value.values()) if isinstance(value, dict) else value
        for i, spin in enumerate(spins):
            spin.setRange(min_val[i], max_val[i])
            spin.setValue(vals[i])
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


def create_tab_layout():
    tab_layout = QFormLayout()
    tab_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    tab_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
    tab_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
    tab_layout.setLabelAlignment(Qt.AlignLeft)
    return tab_layout


def add_tab(tab_widget, title):
    tab = QWidget()
    tab_layout = create_tab_layout()
    tab.setLayout(tab_layout)
    tab_widget.addTab(tab, title)
    return tab_layout


def create_tab_widget(main_layout):
    tab_widget = QTabWidget()
    main_layout.addRow(tab_widget)
    return tab_widget


class NoNameActionConfigurator(ActionConfigurator):
    def __init__(self, current_wd):
        super().__init__(current_wd)
        self.builder = None

    def get_builder(self):
        return self.builder

    def update_params(self, params):
        return self.builder.update_params(params)

    def add_bold_label(self, label):
        label = QLabel(label)
        label.setStyleSheet("font-weight: bold")
        self.add_row(label)

    def add_row(self, row):
        self.builder.main_layout.addRow(row)

    def add_field(self, tag, field_type, label, required=False, add_to_layout=None,
                  **kwargs):
        return self.builder.add_field(tag, field_type, label, required, add_to_layout, **kwargs)

    def labelled_widget(self, label, widget):
        row = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(8)
        label_widget = QLabel(label)
        label_widget.setFixedWidth(120)
        label_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        main_layout.addWidget(label_widget)
        main_layout.addWidget(widget)
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 3)
        row.setLayout(main_layout)
        return row

    def add_labelled_row(self, label, widget):
        self.add_row(self.labelled_widget(label, widget))

    def add_field_to_layout(self, main_layout, tag, field_type, label, required=False, **kwargs):
        return self.add_field(tag, field_type, label, required, add_to_layout=main_layout, **kwargs)

    def add_bold_label_to_layout(self, main_layout, label):
        label_widget = QLabel(label)
        label_widget.setStyleSheet("font-weight: bold")
        main_layout.addRow(label_widget)
        return label_widget


class DefaultActionConfigurator(NoNameActionConfigurator):
    def __init__(self, expert_init, current_wd, expert_toggle=True):
        super().__init__(current_wd)
        self.expert_toggle = expert_toggle
        self._expert_init = expert_init
        self.expert_cb = None
        self.expert_widgets = []

    def create_form(self, main_layout, action, tag='Action'):
        self.builder = FieldBuilder(main_layout, action, self.current_wd)
        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        name_label = QLabel(f"{tag} name:")
        name_field = self.add_field('name', FIELD_TEXT, f"{tag} name", required=False, do_add=False)
        name_row.addWidget(name_label)
        name_row.addWidget(name_field, 1)
        name_row.addStretch()
        if self.expert_toggle:
            expert_layout = QHBoxLayout()
            expert_layout.setContentsMargins(0, 0, 0, 0)
            expert_label = QLabel("Show expert options:")
            self.expert_cb = QCheckBox()
            self.expert_cb.setChecked(self._expert_init)
            self.expert_cb.stateChanged.connect(self.toggle_expert_options)
            expert_layout.addWidget(expert_label)
            expert_layout.addWidget(self.expert_cb)
            name_row.addLayout(expert_layout)
        main_layout.addRow(name_row)
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setLineWidth(1)
        main_layout.addRow(separator)

    def main_layout(self):
        return self.builder.main_layout

    def add_field(self, tag, field_type, label, required=False, add_to_layout=None,
                  expert=False, **kwargs):
        current_layout = add_to_layout if add_to_layout is not None else self.main_layout()
        widget = super().add_field(tag, field_type, label, required, add_to_layout, **kwargs)
        if expert:
            label_widget = None
            if hasattr(current_layout, 'labelForField'):
                label_widget = current_layout.labelForField(widget)
            if label_widget is None:
                for i in range(current_layout.rowCount()):
                    item = current_layout.itemAt(i, QFormLayout.LabelRole)
                    if item and item.widget() and \
                            current_layout.itemAt(i, QFormLayout.FieldRole).widget() == widget:
                        label_widget = item.widget()
                        break
            self.expert_widgets.append((widget, label_widget))
            visible = self.expert_cb.isChecked() if self.expert_cb else self._expert_init
            widget.setVisible(visible)
            if label_widget:
                label_widget.setVisible(visible)
        return widget

    def toggle_expert_options(self, state):
        visible = state == Qt.CheckState.Checked.value
        for widget, label_widget in self.expert_widgets:
            widget.setVisible(visible)
            if label_widget:
                label_widget.setVisible(visible)
        self.main_layout().invalidate()
        self.main_layout().activate()
        parent = self.main_layout().parent()
        while parent and not isinstance(parent, QDialog):
            parent = parent.parent()
        if parent and isinstance(parent, QDialog):
            QTimer.singleShot(50, lambda: self._resize_dialog(parent))

    def _resize_dialog(self, dialog):
        scroll_area = dialog.findChild(QScrollArea)
        if not scroll_area:
            return
        container = scroll_area.widget()
        content_size = container.sizeHint()
        margin = 40
        button_height = 50
        new_height = content_size.height() + button_height + margin
        screen_geo = dialog.screen().availableGeometry()
        max_height = int(screen_geo.height() * 0.8)
        current_size = dialog.size()
        new_height = min(new_height, max_height)
        dialog.resize(current_size.width(), new_height)
        if content_size.height() <= max_height - button_height - margin:
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
