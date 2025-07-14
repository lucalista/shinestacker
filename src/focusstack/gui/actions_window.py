import os.path
import os
import json
import jsonpickle
import subprocess
from PySide6.QtWidgets import QMessageBox, QFileDialog, QListWidgetItem, QDialog
from PySide6.QtGui import QColor, QIcon
from focusstack.core.core_utils import running_under_windows, running_under_macos
from focusstack.gui.project_model import Project
from focusstack.config.constants import constants
from focusstack.gui.gui_run import ColorPalette
from focusstack.gui.action_config import ActionConfigDialog
from focusstack.gui.project_editor import ProjectEditor

ENABLED_LIST_ITEM_COLOR = ColorPalette.DARK_BLUE.tuple()
DISABLED_LIST_ITEM_COLOR = ColorPalette.DARK_RED.tuple()


class ActionsWindow(ProjectEditor):
    def __init__(self):
        super().__init__()
        self.script_dir = os.path.dirname(__file__)
        self._current_file = None
        self._modified_project = False
        self.update_title()

    def update_title(self):
        title = constants.APP_TITLE
        if self._current_file:
            title += f" - {os.path.basename(self._current_file)}"
            if self._modified_project:
                title += " *"
        self.window().setWindowTitle(title)

    def get_icon(self, icon):
        return QIcon(os.path.join(self.script_dir, f"img/{icon}.png"))

    def list_item(self, text, enabled):
        if enabled:
            color = QColor(*ENABLED_LIST_ITEM_COLOR)
            icon = self.get_icon("on")
        else:
            color = QColor(*DISABLED_LIST_ITEM_COLOR)
            icon = self.get_icon("off")
        item = QListWidgetItem(icon, text)
        item.setForeground(color)
        return item

    def mark_as_modified(self):
        self._modified_project = True
        self._project_buffer.append(self.project.clone())
        self.update_title()

    def new_project(self):
        if self._check_unsaved_changes():
            self.set_project(Project())
            self._current_file = None
            self.update_title()
            self.job_list.clear()
            self.action_list.clear()
            self._modified_project = False

    def open_project(self, file_path=False):
        if not self._check_unsaved_changes():
            return
        if file_path is False:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "Project Files (*.fsp);;All Files (*)")
        if file_path:
            try:
                file = open(file_path, 'r')
                json_obj = json.load(file)
                self.set_project(Project.from_dict(json_obj['project']))
                self._modified_project = False
                self._current_file = file_path
                self.update_title()
                self.refresh_ui(0, -1)
                if self.job_list.count() > 0:
                    self.job_list.setCurrentRow(0)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot open file {file_path}:\n{str(e)}")
            if len(self.project.jobs) > 0:
                self.job_list.setCurrentRow(0)
                self.activateWindow()
            for job in self.project.jobs:
                if 'working_path' in job.params.keys():
                    working_path = job.params['working_path']
                    if not os.path.isdir(working_path):
                        QMessageBox.warning(self, "Working path not found",
                                            f'''The working path specified in the project file for the job:
                                            "{job.params['name']}"
                                            was not found.\n
                                            Please, select a valid working path.''')
                        self.edit_action(job)
                for action in job.sub_actions:
                    if 'working_path' in job.params.keys():
                        working_path = job.params['working_path']
                        if working_path != '' and not os.path.isdir(working_path):
                            QMessageBox.warning(self, "Working path not found",
                                                f'''The working path specified in the project file for the job:
                                                "{job.params['name']}"
                                                was not found.\n
                                                Please, select a valid working path.''')
                            self.edit_action(action)

    def current_file_name(self):
        return os.path.basename(self._current_file) if self._current_file else ''

    def save_project(self):
        if self._current_file:
            self.do_save(self._current_file)
        else:
            self.save_project_as()

    def save_project_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Project As", "", "Project Files (*.fsp);;All Files (*)")
        if file_path:
            if not file_path.endswith('.fsp'):
                file_path += '.fsp'
            self.do_save(file_path)
            self._current_file = file_path
            self._modified_project = False
            self.update_title()

    def do_save(self, file_path):
        try:
            json_obj = jsonpickle.encode({
                'project': self.project.to_dict(),
                'version': 1
            })
            f = open(file_path, 'w')
            f.write(json_obj)
            self._modified_project = False
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot save file:\n{str(e)}")

    def _check_unsaved_changes(self) -> bool:
        if self._modified_project:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "The project has unsaved changes. Do you want to continue?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self._save_project()
                return True
            elif reply == QMessageBox.Discard:
                return True
            else:
                return False
        else:
            return True

    def get_action_working_path(self, action, get_name=False):
        if action is None:
            return '', ''
        if action in constants.SUB_ACTION_TYPES:
            return self.get_action_working_path(action.parent, True)
        wp = action.params.get('working_path', '')
        if wp != '':
            return wp, (f" {action.params.get('name', '')} [{action.type_name}]" if get_name else '')
        else:
            return self.get_action_working_path(action.parent, True)

    def get_action_output_path(self, action, get_name=False):
        if action is None:
            return '', ''
        if action.type_name in constants.SUB_ACTION_TYPES:
            return self.get_action_output_path(action.parent, True)
        name = action.params.get('name', '')
        path = action.params.get('output_path', '')
        if path == '':
            path = name
        return path, (f" {action.params.get('name', '')} [{action.type_name}]" if get_name else '')

    def get_action_input_path(self, action, get_name=False):
        if action is None:
            return '', ''
        type_name = action.type_name
        if type_name in constants.SUB_ACTION_TYPES:
            return self.get_action_input_path(action.parent, True)
        path = action.params.get('input_path', '')
        if path == '':
            if action.parent is None:
                if type_name == constants.ACTION_JOB and len(action.sub_actions) > 0:
                    action = action.sub_actions[0]
                    path = action.params.get('input_path', '')
                    return path, f" {action.params.get('name', '')} [{action.type_name}]"
                else:
                    return '', ''
            else:
                actions = action.parent.sub_actions
                if action in actions:
                    i = actions.index(action)
                    if i == 0:
                        return self.get_action_input_path(action.parent, True)
                    else:
                        return self.get_action_output_path(actions[i - 1], True)
                else:
                    return '', ''
        else:
            return path, (f" {action.params.get('name', '')} [{action.type_name}]" if get_name else '')

    def browse_path(self, path):
        ps = path.split(constants.PATH_SEPARATOR)
        for p in ps:
            if os.path.exists(p):
                if running_under_windows():
                    os.startfile(os.path.normpath(p))
                elif running_under_macos():
                    subprocess.run(['open', p])
                else:
                    subprocess.run(['xdg-open', p])

    def browse_working_path_path(self):
        self.browse_path(self.current_action_working_path)

    def browse_input_path_path(self):
        self.browse_path(self.current_action_input_path)

    def browse_output_path_path(self):
        self.browse_path(self.current_action_output_path)

    def on_job_edit(self, item):
        index = self.job_list.row(item)
        if 0 <= index < len(self.project.jobs):
            job = self.project.jobs[index]
            dialog = ActionConfigDialog(job, self)
            if dialog.exec() == QDialog.Accepted:
                current_row = self.job_list.currentRow()
                if current_row >= 0:
                    self.job_list.item(current_row).setText(job.params['name'])

    def on_action_edit(self, item):
        job_index = self.job_list.currentRow()
        if 0 <= job_index < len(self.project.jobs):
            job = self.project.jobs[job_index]
            action_index = self.action_list.row(item)
            action_counter = -1
            current_action = None
            is_sub_action = False
            for action in job.sub_actions:
                action_counter += 1
                if action_counter == action_index:
                    current_action = action
                    break
                if len(action.type_name) > 0:
                    for sub_action in action.sub_actions:
                        action_counter += 1
                        if action_counter == action_index:
                            current_action = sub_action
                            is_sub_action = True
                            break
                    if current_action:
                        break
            if current_action:
                if not is_sub_action:
                    self.set_enabled_sub_actions_gui(current_action.type_name == constants.ACTION_COMBO)
                dialog = ActionConfigDialog(current_action, self)
                if dialog.exec():
                    current_job_index = self.job_list.currentRow()
                    self.on_job_selected(current_job_index)

    def edit_current_action(self):
        current_action = None
        job_row = self.job_list.currentRow()
        sub_action_index = -1
        if 0 <= job_row < len(self.project.jobs):
            job = self.project.jobs[job_row]
            if self.job_list.hasFocus():
                current_action = job
            elif self.action_list.hasFocus():
                job_row, action_row, actions, sub_actions, action_index, sub_action_index = self.get_current_action()
                if actions is not None:
                    action = actions[action_index]
                    current_action = action if sub_action_index == -1 else sub_actions[sub_action_index]
        if current_action is not None:
            self.edit_action(current_action)

    def edit_action(self, action):
        dialog = ActionConfigDialog(action, self)
        if dialog.exec():
            self.on_job_selected(self.job_list.currentRow())
            self.mark_as_modified()
