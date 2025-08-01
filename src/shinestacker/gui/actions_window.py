import os.path
import os
import json
import jsonpickle
import traceback
from PySide6.QtWidgets import QMessageBox, QFileDialog, QDialog
from .. core.core_utils import get_app_base_path
from .. config.constants import constants
from .project_model import ActionConfig
from .action_config import ActionConfigDialog
from .project_editor import ProjectEditor
from .new_project import NewProjectDialog
from .project_model import Project


class ActionsWindow(ProjectEditor):
    def __init__(self):
        super().__init__()
        self._current_file = None
        self._current_file_wd = ''
        self._modified_project = False
        self.update_title()

    def update_title(self):
        title = constants.APP_TITLE
        if self._current_file:
            title += f" - {os.path.basename(self._current_file)}"
            if self._modified_project:
                title += " *"
        self.window().setWindowTitle(title)

    def mark_as_modified(self):
        self._modified_project = True
        self._project_buffer.append(self.project.clone())
        self.update_title()

    def close_project(self):
        if self._check_unsaved_changes():
            self.set_project(Project())
            self._current_file = None
            self.update_title()
            self.job_list.clear()
            self.action_list.clear()
            self._modified_project = False

    def new_project(self):
        if not self._check_unsaved_changes():
            return
        os.chdir(get_app_base_path())
        self._current_file = None
        self._modified_project = False
        self.update_title()
        self.job_list.clear()
        self.action_list.clear()
        dialog = NewProjectDialog(self)
        if dialog.exec() == QDialog.Accepted:
            input_folder = dialog.get_input_folder().split('/')
            working_path = '/'.join(input_folder[:-1])
            input_path = input_folder[-1]
            project = Project()
            if dialog.get_noise_detection():
                job_noise = ActionConfig(constants.ACTION_JOB,
                                         {'name': 'detect-noise', 'working_path': working_path,
                                          'input_path': input_path})
                noise_detection = ActionConfig(constants.ACTION_NOISEDETECTION,
                                               {'name': 'detect-noise'})
                job_noise.add_sub_action(noise_detection)
                project.jobs.append(job_noise)
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
            project.jobs.append(job)
            self.set_project(project)
            self._modified_project = True
            self.refresh_ui(0, -1)

    def open_project(self, file_path=False):
        if not self._check_unsaved_changes():
            return
        if file_path is False:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "Project Files (*.fsp);;All Files (*)")
        if file_path:
            try:
                self._current_file_wd = '' if os.path.isabs(file_path) else os.getcwd()
                file = open(file_path, 'r')
                pp = file_path.split('/')
                if len(pp) > 1:
                    os.chdir('/'.join(pp[:-1]))
                json_obj = json.load(file)
                project = Project.from_dict(json_obj['project'])
                if project is None:
                    raise RuntimeError(f"Project from file {file_path} produced a null project.")
                self.set_project(project)
                self._modified_project = False
                self._current_file = file_path
                self.update_title()
                self.refresh_ui(0, -1)
                if self.job_list.count() > 0:
                    self.job_list.setCurrentRow(0)
            except Exception as e:
                traceback.print_tb(e.__traceback__)
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
            self._current_file_wd = ''
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
            path = f"{self._current_file_wd}/{file_path}" if self._current_file_wd != '' else file_path
            f = open(path, 'w')
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
                self.save_project()
                return True
            elif reply == QMessageBox.Discard:
                return True
            else:
                return False
        else:
            return True

    def on_job_edit(self, item):
        index = self.job_list.row(item)
        if 0 <= index < len(self.project.jobs):
            job = self.project.jobs[index]
            dialog = ActionConfigDialog(job, self)
            if dialog.exec() == QDialog.Accepted:
                current_row = self.job_list.currentRow()
                if current_row >= 0:
                    self.job_list.item(current_row).setText(job.params['name'])
                self.refresh_ui()

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
                if dialog.exec() == QDialog.Accepted:
                    self.on_job_selected(job_index)
                    self.refresh_ui()
                    self.job_list.setCurrentRow(job_index)
                    self.action_list.setCurrentRow(action_index)

    def edit_current_action(self):
        current_action = None
        job_row = self.job_list.currentRow()
        if 0 <= job_row < len(self.project.jobs):
            job = self.project.jobs[job_row]
            if self.job_list.hasFocus():
                current_action = job
            elif self.action_list.hasFocus():
                job_row, action_row, pos = self.get_current_action()
                if pos.actions is not None:
                    current_action = pos.action if not pos.is_sub_action else pos.sub_action
        if current_action is not None:
            self.edit_action(current_action)

    def edit_action(self, action):
        dialog = ActionConfigDialog(action, self)
        if dialog.exec() == QDialog.Accepted:
            self.on_job_selected(self.job_list.currentRow())
            self.mark_as_modified()
