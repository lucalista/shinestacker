# pylint: disable=R0904, E0611, R0914, R1702, W0718
import os
import shutil
import traceback
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QCheckBox, QDialog, QMessageBox, QGroupBox, QFormLayout, QSizePolicy)
from ..config.constants import constants
from ..gui.project_model import get_action_working_path, get_action_output_path
from ..gui.base_form_dialog import BaseFormDialog


class ClearImagesDialog(BaseFormDialog):
    def __init__(self, project, parent=None):
        super().__init__("Clear Project Images", 600, parent)
        self._project = project
        self.options = {}
        self.count_options = 0
        self.create_form()
        self.create_ok_cancel()
        self.adjust_height_to_content()

    def create_form(self):
        for job in self._project.jobs:
            self.make_group(job)

    def make_group(self, job):
        labels = {
            'output_path': 'Output path',
            'plot_path': 'Plots path'
        }
        job_name = job.params['name']
        options = self.options[job_name] = {}
        for action in job.sub_actions:
            type_name = action.type_name
            action_name = f"<b>{action.params['name']}</b> [{type_name}]"
            options[action_name] = {}
            wp = get_action_working_path(action)[0]
            for par, _val in labels.items():
                if par == 'output_path':
                    path = get_action_output_path(action)[0]
                else:
                    path = action.params.get(par, None)
                if path is not None:
                    path = os.path.join(wp, path)
                    if os.path.isdir(path):
                        checkbox = QCheckBox()
                        checked = type_name not in [
                            constants.ACTION_FOCUSSTACK, constants.ACTION_MULTILAYER]
                        checkbox.setChecked(checked)
                        self.options[job_name][action_name][par] = {
                            'checkbox': checkbox, 'path': path}
        job_options = self.options[job_name]
        if len(job_options) > 0:
            clear_group = QGroupBox(f"Job: {job_name}")
            clear_layout = QFormLayout()
            clear_layout.setContentsMargins(15, 0, 15, 15)
            clear_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            clear_layout.setFormAlignment(Qt.AlignLeft)
            clear_layout.setLabelAlignment(Qt.AlignLeft)
            for action_name, action_options in job_options.items():
                if len(action_options) > 0:
                    clear_layout.addRow(QLabel(f"Action: {action_name}"))
                    for par, checkbox_path in action_options.items():
                        clear_layout.addRow(QLabel(f"• {labels.get(par, par)} :"),
                                            checkbox_path['checkbox'])
                        self.count_options += 1
            if self.count_options > 0:
                clear_group.setLayout(clear_layout)
                clear_group.setStyleSheet(self.group_style)
                clear_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                self.form_layout.addRow(clear_group)

    def accept(self):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Confirm Deletion")
        msg_box.setText("Files will be deleted. Are you sure?")
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg_box.setDefaultButton(QMessageBox.Cancel)
        result = msg_box.exec()
        if result == QMessageBox.Ok:
            errors = self.delete_folders()
            if errors:
                error_msg = "Failed to delete folders:\n" + "\n".join(errors)
                QMessageBox.warning(self, "Deletion Errors", error_msg)
            super().accept()

    def delete_folders(self):
        errors = []
        deleted = []
        for _job_name, actions in self.options.items():
            for _action_name, paths in actions.items():
                for _key, data in paths.items():
                    if data['checkbox'].isChecked():
                        folder_path = data['path']
                        try:
                            if os.path.exists(folder_path):
                                shutil.rmtree(folder_path)
                                deleted.append(folder_path)
                        except Exception as e:
                            traceback.print_exc()
                            errors.append(f"{folder_path}: {str(e)}")
        return errors


def clear_project_images(project, parent):
    dialog = ClearImagesDialog(project, parent)
    if dialog.count_options == 0:
        return False, "No folders to clear."
    if dialog.exec() == QDialog.Accepted:
        return True, "Folders cleared successfully."
    return False, "Operation cancelled."
