# pylint: disable=R0904, E0611, R0914, R1702, W0718
from PySide6.QtWidgets import QLabel, QLineEdit, QGroupBox, QHBoxLayout, QVBoxLayout
from ..gui.base_form_dialog import BaseFormDialog


class RenameDialog(BaseFormDialog):
    def __init__(self, element, parent=None):
        super().__init__("Rename Element", 600, parent)
        self._element = element
        self.options = {}
        self.lines = {}
        self.create_form()
        self.create_ok_cancel()
        self.adjust_height_to_content()

    def create_form(self):
        self.lines = {}
        root_group = self._create_element_group(self._element, self.lines)
        self.form_layout.addRow(root_group)

    def _create_element_group(self, element, lines_dict):
        group = QGroupBox(element.type_name)
        layout = QVBoxLayout(group)

        name_layout = QHBoxLayout()
        name_label = QLabel("Name:")
        line_edit = QLineEdit(element.params['name'], group)
        name_layout.addWidget(name_label)
        name_layout.addWidget(line_edit)
        layout.addLayout(name_layout)

        lines_dict['name'] = line_edit

        if element.sub_actions:
            lines_dict['sub'] = []
            sub_layout = QVBoxLayout()
            for sub in element.sub_actions:
                sub_lines = {}
                sub_group = self._create_element_group(sub, sub_lines)
                sub_layout.addWidget(sub_group)
                lines_dict['sub'].append(sub_lines)
            layout.addLayout(sub_layout)

        return group

    def set_options(self, options, lines):
        options['name'] = lines['name'].text()
        subs = lines.get('sub')
        if subs:
            options['sub'] = []
            for sub in subs:
                options['sub'].append({})
                self.set_options(options['sub'][-1], sub)

    def accept(self):
        self.set_options(self.options, self.lines)
        super().accept()
