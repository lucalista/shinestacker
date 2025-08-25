# pylint: disable=C0114, C0115, C0116, E0611, R0913, R0917, R0914, R0912, R0904, R0915, W0718
import os
import os.path
import traceback
import json
import jsonpickle
from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QMessageBox, QFileDialog, QDialog
from .. config.constants import constants
from .. core.core_utils import get_app_base_path
from .project_model import ActionConfig
from .new_project import NewProjectDialog
from .project_model import Project
from .project_editor import ProjectEditor


class ProjectController(QObject):
    update_title_requested = Signal()
    refresh_ui_requested = Signal(int, int)
    activate_window_requested = Signal()
    enable_save_actions_requested = Signal(bool)

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.project_editor = ProjectEditor(parent)

    def refresh_ui(self, job_row=-1, action_row=-1):
        self.refresh_ui_requested.emit(job_row, action_row)

    def mark_as_modified(self, modified=True):
        self.project_editor.mark_as_modified(modified)

    def modified(self):
        return self.project_editor.modified()

    def set_project(self, project):
        self.project_editor.set_project(project)

    def project(self):
        return self.project_editor.project()

    def project_jobs(self):
        return self.project_editor.project_jobs()

    def project_job(self, i):
        return self.project_editor.project_job(i)

    def add_job_to_project(self, job):
        self.project_editor.add_job_to_project(job)

    def num_project_jobs(self):
        return self.project_editor.num_project_jobs()

    def save_actions_set_enabled(self, enabled):
        self.enable_save_actions_requested.emit(enabled)

    def current_file_path(self):
        return self.project_editor.current_file_path()

    def current_file_directory(self):
        return self.project_editor.current_file_directory()

    def current_file_name(self):
        return self.project_editor.current_file_name()

    def set_current_file_path(self, path):
        self.project_editor.set_current_file_path(path)

    def job_list(self):
        return self.project_editor.job_list()

    def action_list(self):
        return self.project_editor.action_list()

    def current_job_index(self):
        return self.project_editor.current_job_index()

    def current_action_index(self):
        return self.project_editor.current_action_index()

    def set_current_job(self, index):
        return self.project_editor.set_current_job(index)

    def set_current_action(self, index):
        return self.project_editor.set_current_action(index)

    def job_list_count(self):
        return self.project_editor.job_list_count()

    def action_list_count(self):
        return self.project_editor.action_list_count()

    def job_list_item(self, index):
        return self.project_editor.job_list_item(index)

    def action_list_item(self, index):
        return self.project_editor.action_list_item(index)

    def job_list_has_focus(self):
        return self.project_editor.job_list_has_focus()

    def action_list_has_focus(self):
        return self.project_editor.action_list_has_focus()

    def clear_job_list(self):
        self.project_editor.clear_job_list()

    def clear_action_list(self):
        self.project_editor.clear_action_list()

    def num_selected_jobs(self):
        return self.project_editor.num_selected_jobs()

    def num_selected_actions(self):
        return self.project_editor.num_selected_actions()

    def get_current_action_at(self, job, action_index):
        return self.project_editor.get_current_action_at(job, action_index)

    def action_config_dialog(self, action):
        return self.project_editor.action_config_dialog(action)

    def on_job_selected(self, index):
        return self.project_editor.on_job_selected(index)

    def update_title(self):
        self.update_title_requested.emit()

    def close_project(self):
        if self.check_unsaved_changes():
            self.set_project(Project())
            self.set_current_file_path('')
            self.update_title()
            self.clear_job_list()
            self.clear_action_list()
            self.mark_as_modified(False)

    def new_project(self):
        if not self.check_unsaved_changes():
            return
        os.chdir(get_app_base_path())
        self.set_current_file_path('')
        self.mark_as_modified(False)
        self.update_title()
        self.clear_job_list()
        self.clear_action_list()
        self.set_project(Project())
        self.save_actions_set_enabled(False)
        dialog = NewProjectDialog(self.parent)
        if dialog.exec() == QDialog.Accepted:
            self.save_actions_set_enabled(True)
            input_folder = dialog.get_input_folder().split('/')
            working_path = '/'.join(input_folder[:-1])
            input_path = input_folder[-1]
            if dialog.get_noise_detection():
                job_noise = ActionConfig(constants.ACTION_JOB,
                                         {'name': 'detect-noise', 'working_path': working_path,
                                          'input_path': input_path})
                noise_detection = ActionConfig(constants.ACTION_NOISEDETECTION,
                                               {'name': 'detect-noise'})
                job_noise.add_sub_action(noise_detection)
                self.add_job_to_project(job_noise)
            job = ActionConfig(constants.ACTION_JOB,
                               {'name': 'focus-stack', 'working_path': working_path,
                                'input_path': input_path})
            if dialog.get_noise_detection() or dialog.get_vignetting_correction() or \
               dialog.get_align_frames() or dialog.get_balance_frames():
                combo_action = ActionConfig(constants.ACTION_COMBO, {'name': 'align'})
                if dialog.get_noise_detection():
                    mask_noise = ActionConfig(constants.ACTION_MASKNOISE, {'name': 'mask-noise'})
                    combo_action.add_sub_action(mask_noise)
                if dialog.get_vignetting_correction():
                    vignetting = ActionConfig(constants.ACTION_VIGNETTING, {'name': 'vignetting'})
                    combo_action.add_sub_action(vignetting)
                if dialog.get_align_frames():
                    align = ActionConfig(constants.ACTION_ALIGNFRAMES, {'name': 'align'})
                    combo_action.add_sub_action(align)
                if dialog.get_balance_frames():
                    balance = ActionConfig(constants.ACTION_BALANCEFRAMES, {'name': 'balance'})
                    combo_action.add_sub_action(balance)
                job.add_sub_action(combo_action)
            if dialog.get_bunch_stack():
                bunch_stack = ActionConfig(constants.ACTION_FOCUSSTACKBUNCH,
                                           {'name': 'bunches', 'frames': dialog.get_bunch_frames(),
                                            'overlap': dialog.get_bunch_overlap()})
                job.add_sub_action(bunch_stack)
            if dialog.get_focus_stack_pyramid():
                focus_pyramid = ActionConfig(constants.ACTION_FOCUSSTACK,
                                             {'name': 'focus-stack-pyramid',
                                              'stacker': constants.STACK_ALGO_PYRAMID})
                job.add_sub_action(focus_pyramid)
            if dialog.get_focus_stack_depth_map():
                focus_depth_map = ActionConfig(constants.ACTION_FOCUSSTACK,
                                               {'name': 'focus-stack-depth-map',
                                                'stacker': constants.STACK_ALGO_DEPTH_MAP})
                job.add_sub_action(focus_depth_map)
            if dialog.get_multi_layer():
                input_path = []
                if dialog.get_focus_stack_pyramid():
                    input_path.append("focus-stack-pyramid")
                if dialog.get_focus_stack_depth_map():
                    input_path.append("focus-stack-depth-map")
                if dialog.get_bunch_stack():
                    input_path.append("bunches")
                else:
                    input_path.append(input_path)
                multi_layer = ActionConfig(constants.ACTION_MULTILAYER,
                                           {'name': 'multi-layer',
                                            'input_path': ','.join(input_path)})
                job.add_sub_action(multi_layer)
            self.add_job_to_project(job)
            self.mark_as_modified(True)
            self.refresh_ui(0, -1)

    def open_project(self, file_path=False):
        if not self.check_unsaved_changes():
            return
        if file_path is False:
            file_path, _ = QFileDialog.getOpenFileName(
                self.parent, "Open Project", "", "Project Files (*.fsp);;All Files (*)")
        if file_path:
            try:
                self.set_current_file_path(file_path)
                with open(self.current_file_path(), 'r', encoding="utf-8") as file:
                    json_obj = json.load(file)
                project = Project.from_dict(json_obj['project'])
                if project is None:
                    raise RuntimeError(f"Project from file {file_path} produced a null project.")
                self.set_project(project)
                self.mark_as_modified(False)
                self.refresh_ui(0, -1)
                if self.job_list_count() > 0:
                    self.set_current_job(0)
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                QMessageBox.critical(
                    self.parent, "Error", f"Cannot open file {file_path}:\n{str(e)}")
            if self.num_project_jobs() > 0:
                self.set_current_job(0)
                self.activate_window_requested.emit()
                self.save_actions_set_enabled(True)
            for job in self.project_jobs():
                if 'working_path' in job.params.keys():
                    working_path = job.params['working_path']
                    if not os.path.isdir(working_path):
                        QMessageBox.warning(
                            self.parent, "Working path not found",
                            f'''The working path specified in the project file for the job:
                                "{job.params['name']}"
                                was not found.\n
                                Please, select a valid working path.''')
                        self.edit_action(job)
                for action in job.sub_actions:
                    if 'working_path' in job.params.keys():
                        working_path = job.params['working_path']
                        if working_path != '' and not os.path.isdir(working_path):
                            QMessageBox.warning(
                                self.parent, "Working path not found",
                                f'''The working path specified in the project file for the job:
                                "{job.params['name']}"
                                was not found.\n
                                Please, select a valid working path.''')
                            self.edit_action(action)

    def save_project(self):
        path = self.current_file_path()
        if path:
            self.do_save(path)
        else:
            self.save_project_as()

    def save_project_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent, "Save Project As", "", "Project Files (*.fsp);;All Files (*)")
        if file_path:
            if not file_path.endswith('.fsp'):
                file_path += '.fsp'
            self.do_save(file_path)
            self.set_current_file_path(file_path)
            os.chdir(os.path.dirname(file_path))

    def do_save(self, file_path):
        try:
            json_obj = jsonpickle.encode({
                'project': self.project().to_dict(), 'version': 1
            })
            with open(file_path, 'w', encoding="utf-8") as f:
                f.write(json_obj)
            self.mark_as_modified(False)
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"Cannot save file:\n{str(e)}")

    def check_unsaved_changes(self) -> bool:
        if self.modified():
            reply = QMessageBox.question(
                self.parent, "Unsaved Changes",
                "The project has unsaved changes. Do you want to continue?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self.save_project()
                return True
            return reply == QMessageBox.Discard
        return True

    def on_job_edit(self, item):
        index = self.job_list().row(item)
        if 0 <= index < self.num_project_jobs():
            job = self.project_job(index)
            dialog = self.action_config_dialog(job)
            if dialog.exec() == QDialog.Accepted:
                current_row = self.current_job_index()
                if current_row >= 0:
                    self.job_list_item(current_row).setText(job.params['name'])
                self.refresh_ui()

    def on_action_edit(self, item):
        job_index = self.current_job_index()
        if 0 <= job_index < self.num_project_jobs():
            job = self.project_job(job_index)
            action_index = self.action_list().row(item)
            current_action, is_sub_action = self.get_current_action_at(job, action_index)
            if current_action:
                if not is_sub_action:
                    self.set_enabled_sub_actions_gui(
                        current_action.type_name == constants.ACTION_COMBO)
                dialog = self.action_config_dialog(current_action)
                if dialog.exec() == QDialog.Accepted:
                    self.on_job_selected(job_index)
                    self.refresh_ui()
                    self.set_current_job(job_index)
                    self.set_current_action(action_index)

    def edit_current_action(self):
        current_action = None
        job_row = self.current_job_index()
        if 0 <= job_row < self.num_project_jobs():
            job = self.project_job(job_row)
            if self.job_list_has_focus():
                current_action = job
            elif self.action_list_has_focus():
                job_row, _action_row, pos = self.get_current_action()
                if pos.actions is not None:
                    current_action = pos.action if not pos.is_sub_action else pos.sub_action
        if current_action is not None:
            self.edit_action(current_action)

    def edit_action(self, action):
        dialog = self.action_config_dialog(action)
        if dialog.exec() == QDialog.Accepted:
            self.on_job_selected(self.current_job_index())
            self.mark_as_modified()
