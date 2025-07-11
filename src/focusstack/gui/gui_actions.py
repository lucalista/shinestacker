from PySide6.QtWidgets import QMainWindow, QListWidget, QMessageBox, QDialog
from focusstack.config.constants import constants
from focusstack.gui.action_config import ActionConfig, ActionConfigDialog
from focusstack.gui.project_converter import ProjectConverter
from focusstack.gui.gui_run import RunWorker

DISABLED_TAG = ""  # " <disabled>"
INDENT_SPACE = "     "
CLONE_POSTFIX = " (clone)"


class JobLogWorker(RunWorker):
    def __init__(self, job, id_str):
        super().__init__(id_str)
        self.job = job
        self.tag = "Job"

    def do_run(self):
        converter = ProjectConverter()
        return converter.run_job(self.job, self.id_str, self.callbacks)


class ProjectLogWorker(RunWorker):
    def __init__(self, project, id_str):
        super().__init__(id_str)
        self.project = project
        self.tag = "Project"

    def do_run(self):
        converter = ProjectConverter()
        return converter.run_project(self.project, self.id_str, self.callbacks)


class GuiActions(QMainWindow):
    def __init__(self):
        super().__init__()
        self._copy_buffer = None
        self._modified_project = False
        self._project_buffer = []
        self.job_list = QListWidget()
        self.action_list = QListWidget()

    def job_text(self, job):
        txt = job.params.get('name', '(job)')
        if not job.enabled():
            txt += DISABLED_TAG
        return txt

    def action_text(self, action, is_sub_action=False, indent=True):
        txt = INDENT_SPACE if is_sub_action and indent else ""
        if action.params.get('name', '') != '':
            txt += action.params["name"]
        txt += f" [{action.type_name}]"
        if not action.enabled():
            txt += DISABLED_TAG
        return txt

    def shift_job(self, delta):
        job_index = self.job_list.currentRow()
        if job_index < 0:
            return
        new_index = job_index + delta
        if 0 <= new_index < len(self.project.jobs):
            jobs = self.project.jobs
            self.mark_as_modified()
            jobs.insert(new_index, jobs.pop(job_index))
            self.refresh_ui(new_index, -1)

    def get_job_at(self, index):
        return None if index < 0 else self.project.jobs[index]

    def get_current_job(self):
        return self.get_job_at(self.job_list.currentRow())

    def get_current_action(self):
        return self.get_action_at(self.action_list.currentRow())

    def get_action_at(self, action_row):
        job_row = self.job_list.currentRow()
        if (0 <= job_row < len(self.project.jobs)) and (0 <= action_row < self.action_list.count()):
            job = self.project.jobs[job_row]
            action_counter = -1
            sub_action_index = -1
            sub_actions = None
            actions = job.sub_actions
            for action_index, action in enumerate(actions):
                action_counter += 1
                if action_counter == action_row:
                    break
                if len(action.sub_actions) > 0:
                    sub_actions = action.sub_actions
                    for i, sub_action in enumerate(sub_actions):
                        action_counter += 1
                        if action_counter == action_row:
                            sub_action_index = i
                            break
                    if sub_action_index != -1:
                        break
            return job_row, action_row, actions, sub_actions, action_index, sub_action_index
        return job_row, action_row, None, None, -1, -1

    def shift_action(self, delta):
        job_row, action_row, actions, sub_actions, action_index, sub_action_index = self.get_current_action()
        if actions is not None:
            new_row = action_row
            if sub_action_index == -1:
                new_index = action_index + delta
                if 0 <= new_index < len(actions):
                    self.mark_as_modified()
                    actions.insert(new_index, actions.pop(action_index))
                    new_row = 0
                    for action in actions[:new_index]:
                        new_row += 1 + len(action.sub_actions)
            else:
                new_index = sub_action_index + delta
                if 0 <= new_index < len(sub_actions):
                    self.mark_as_modified()
                    sub_actions.insert(new_index, sub_actions.pop(sub_action_index))
                    new_row = 1 + new_index
                    for action in actions[:action_index]:
                        new_row += 1 + len(action.sub_actions)
            self.refresh_ui(job_row, new_row)

    def move_element_up(self):
        if self.job_list.hasFocus():
            self.shift_job(-1)
        elif self.action_list.hasFocus():
            self.shift_action(-1)

    def move_element_down(self):
        if self.job_list.hasFocus():
            self.shift_job(+1)
        elif self.action_list.hasFocus():
            self.shift_action(+1)

    def clone_job(self):
        job_index = self.job_list.currentRow()
        if 0 <= job_index < len(self.project.jobs):
            job_clone = self.project.jobs[job_index].clone(CLONE_POSTFIX)
            new_job_index = job_index + 1
            self.mark_as_modified()
            self.project.jobs.insert(new_job_index, job_clone)
            self.job_list.setCurrentRow(new_job_index)
            self.action_list.setCurrentRow(new_job_index)
            self.refresh_ui(new_job_index, -1)

    def clone_action(self):
        job_row, action_row, actions, sub_actions, action_index, sub_action_index = self.get_current_action()
        action = actions[action_index]
        if actions is not None:
            if sub_action_index == -1:
                action_clone = action.clone(CLONE_POSTFIX)
                self.mark_as_modified()
                actions.insert(action_index + 1, action_clone)
            else:
                sub_action = sub_actions[sub_action_index]
                sub_action_clone = sub_action.clone(CLONE_POSTFIX)
                self.mark_as_modified()
                sub_actions.insert(sub_action_index + 1, sub_action_clone)
            new_row = action_row
            if sub_action_index == -1:
                new_index = action_index + 1
                if 0 <= new_index < len(actions):
                    new_row = 0
                    for action in actions[:new_index]:
                        new_row += 1 + len(action.sub_actions)
            else:
                new_index = sub_action_index + 1
                if 0 <= new_index < len(sub_actions):
                    new_row = 1 + new_index
                    for action in actions[:action_index]:
                        new_row += 1 + len(action.sub_actions)
            self.refresh_ui(job_row, new_row)

    def clone_element(self):
        if self.job_list.hasFocus():
            self.clone_job()
        elif self.action_list.hasFocus():
            self.clone_action()

    def delete_job(self, confirm=True):
        current_index = self.job_list.currentRow()
        if 0 <= current_index < len(self.project.jobs):
            if confirm:
                reply = QMessageBox.question(
                    self, "Confirm Delete",
                    f"Are you sure you want to delete job '{self.project.jobs[current_index].params.get('name', '')}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
            if not confirm or reply == QMessageBox.Yes:
                self.job_list.takeItem(current_index)
                self.mark_as_modified()
                current_job = self.project.jobs.pop(current_index)
                self.action_list.clear()
                self.refresh_ui()
                return current_job
        return None

    def delete_action(self, confirm=True):
        job_row, action_row, actions, sub_actions, action_index, sub_action_index = self.get_current_action()
        if actions is not None:
            action = actions[action_index]
            current_action = action if sub_action_index == -1 else sub_actions[sub_action_index]
            if confirm:
                reply = QMessageBox.question(
                    self,
                    "Confirm Delete",
                    f"Are you sure you want to delete action '{self.action_text(current_action, sub_action_index != -1, indent=False)}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
            if not confirm or reply == QMessageBox.Yes:
                if sub_action_index != -1:
                    self.mark_as_modified()
                    action.pop_sub_action(sub_action_index)
                    new_row = action_row if sub_action_index < len(sub_actions) else action_row - 1
                else:
                    self.mark_as_modified()
                    self.project.jobs[job_row].pop_sub_action(action_index)
                    if action_index == 0:
                        new_row = 0 if len(actions) > 0 else -1
                    elif action_index < len(actions):
                        new_row = action_row
                    elif action_index == len(actions):
                        new_row = action_row - len(actions[action_index - 1].sub_actions) - 1
                self.refresh_ui(job_row, new_row)
            return current_action
        return None

    def delete_element(self, confirm=True):
        if self.job_list.hasFocus():
            element = self.delete_job(confirm)
        elif self.action_list.hasFocus():
            element = self.delete_action(confirm)
        if self.job_list.count() > 0:
            self.delete_element_action.setEnabled(True)
        return element

    def add_job(self):
        job_action = ActionConfig("Job")
        dialog = ActionConfigDialog(job_action, self)
        if dialog.exec() == QDialog.Accepted:
            self.mark_as_modified()
            self.project.jobs.append(job_action)
            self.job_list.addItem(self.list_item(self.job_text(job_action), job_action.enabled()))
            self.job_list.setCurrentRow(self.job_list.count() - 1)
            self.job_list.item(self.job_list.count() - 1).setSelected(True)
            self.refresh_ui()

    def add_action(self, type_name=False):
        current_index = self.job_list.currentRow()
        if current_index < 0:
            if len(self.project.jobs) > 0:
                QMessageBox.warning(self, "No Job Selected", "Please select a job first.")
            else:
                QMessageBox.warning(self, "No Job Added", "Please add a job first.")
            return
        if type_name is False:
            type_name = self.action_selector.currentText()
        action = ActionConfig(type_name)
        action.parent = self.get_current_job()
        dialog = ActionConfigDialog(action, self)
        if dialog.exec() == QDialog.Accepted:
            self.mark_as_modified()
            self.project.jobs[current_index].add_sub_action(action)
            self.action_list.addItem(self.list_item(self.action_text(action), action.enabled()))
            self.delete_element_action.setEnabled(False)

    def add_action_CombinedActions(self):
        self.add_action(constants.ACTION_COMBO)

    def add_action_NoiseDetection(self):
        self.add_action(constants.ACTION_NOISEDETECTION)

    def add_action_FocusStack(self):
        self.add_action(constants.ACTION_FOCUSSTACK)

    def add_action_FocusStackBunch(self):
        self.add_action(constants.ACTION_FOCUSSTACKBUNCH)

    def add_action_MultiLayer(self):
        self.add_action(constants.ACTION_MULTILAYER)

    def add_sub_action(self, type_name=False):
        current_job_index = self.job_list.currentRow()
        current_action_index = self.action_list.currentRow()
        if (current_job_index < 0 or current_action_index < 0 or current_job_index >= len(self.project.jobs)):
            return
        job = self.project.jobs[current_job_index]
        action = None
        action_counter = -1
        for i, act in enumerate(job.sub_actions):
            action_counter += 1
            if action_counter == current_action_index:
                action = act
                break
            action_counter += len(act.sub_actions)
        if not action or action.type_name != constants.ACTION_COMBO:
            return
        if type_name is False:
            type_name = self.sub_action_selector.currentText()
        sub_action = ActionConfig(type_name)
        dialog = ActionConfigDialog(sub_action, self)
        if dialog.exec() == QDialog.Accepted:
            self.mark_as_modified()
            action.add_sub_action(sub_action)
            self.on_job_selected(current_job_index)
            self.action_list.setCurrentRow(current_action_index)

    def add_sub_action_MakeNoise(self):
        self.add_sub_action(constants.ACTION_MASKNOISE)

    def add_sub_action_Vignetting(self):
        self.add_sub_action(constants.ACTION_VIGNETTING)

    def add_sub_action_AlignFrames(self):
        self.add_sub_action(constants.ACTION_ALIGNFRAMES)

    def add_sub_action_BalanceFrames(self):
        self.add_sub_action(constants.ACTION_BALANCEFRAMES)

    def copy_job(self):
        current_index = self.job_list.currentRow()
        if 0 <= current_index < len(self.project.jobs):
            self._copy_buffer = self.project.jobs[current_index].clone()

    def copy_action(self):
        job_row, action_row, actions, sub_actions, action_index, sub_action_index = self.get_current_action()
        if actions is not None:
            if sub_action_index == -1:
                self._copy_buffer = actions[action_index].clone()
            else:
                self._copy_buffer = sub_actions[sub_action_index].clone()

    def copy_element(self):
        if self.job_list.hasFocus():
            self.copy_job()
        elif self.action_list.hasFocus():
            self.copy_action()

    def paste_job(self):
        if self._copy_buffer.type_name != constants.ACTION_JOB:
            return
        job_index = self.job_list.currentRow()
        if 0 <= job_index < len(self.project.jobs):
            new_job_index = job_index
            self.mark_as_modified()
            self.project.jobs.insert(new_job_index, self._copy_buffer)
            self.job_list.setCurrentRow(new_job_index)
            self.action_list.setCurrentRow(new_job_index)
            self.refresh_ui(new_job_index, -1)

    def paste_action(self):
        job_row, action_row, actions, sub_actions, action_index, sub_action_index = self.get_current_action()
        action = actions[action_index]
        if actions is not None:
            if sub_action_index == -1:
                if self._copy_buffer.type_name not in constants.ACTION_TYPES:
                    return
                self.mark_as_modified()
                actions.insert(action_index, self._copy_buffer)
            else:
                if action.type_name != constants.ACTION_COMBO or \
                   self._copy_buffer.type_name not in constants.SUB_ACTION_TYPES:
                    return
                self.mark_as_modified()
                sub_actions.insert(sub_action_index, self._copy_buffer)
            new_row = action_row
            if sub_action_index == -1:
                new_index = action_index
                if 0 <= new_index < len(actions):
                    new_row = 0
                    for action in actions[:new_index]:
                        new_row += 1 + len(action.sub_actions)
            else:
                new_index = sub_action_index
                if 0 <= new_index < len(sub_actions):
                    new_row = 1 + new_index
                    for action in actions[:action_index]:
                        new_row += 1 + len(action.sub_actions)
            self.refresh_ui(job_row, new_row)

    def paste_element(self):
        if self._copy_buffer is None:
            return
        if self.job_list.hasFocus():
            self.paste_job()
        elif self.action_list.hasFocus():
            self.paste_action()

    def cut_element(self):
        self._copy_buffer = self.delete_element(False)

    def undo(self):
        job_row = self.job_list.currentRow()
        action_row = self.action_list.currentRow()
        if len(self._project_buffer) > 0:
            self.project = self._project_buffer.pop()
            self.refresh_ui()
            len_jobs = len(self.project.jobs)
            if len_jobs > 0:
                if job_row >= len_jobs:
                    job_row = len_jobs - 1
                self.job_list.setCurrentRow(job_row)
                actions = self.project.jobs[job_row].sub_actions
                len_actions = len(actions)
                if len_actions > 0:
                    if action_row >= len_actions:
                        action_row = len_actions
                    self.action_list.setCurrentRow(action_row)

    def set_enabled(self, enabled):
        current_action = None
        if self.job_list.hasFocus():
            job_row = self.job_list.currentRow()
            if 0 <= job_row < len(self.project.jobs):
                current_action = self.project.jobs[job_row]
                action_row = -1
        elif self.action_list.hasFocus():
            job_row, action_row, actions, sub_actions, action_index, sub_action_index = self.get_current_action()
            if actions is not None:
                action = actions[action_index]
                current_action = action if sub_action_index == -1 else sub_actions[sub_action_index]
        if current_action:
            if current_action.enabled() != enabled:
                self.mark_as_modified()
                current_action.set_enabled(enabled)
                self.refresh_ui(job_row, action_row)

    def enable(self):
        self.set_enabled(True)

    def disable(self):
        self.set_enabled(False)

    def set_enabled_all(self, enable=True):
        self.mark_as_modified()
        job_row = self.job_list.currentRow()
        action_row = self.action_list.currentRow()
        for j in self.project.jobs:
            j.set_enabled_all(enable)
        self.refresh_ui(job_row, action_row)

    def enable_all(self):
        self.set_enabled_all(True)

    def disable_all(self):
        self.set_enabled_all(False)

    def run_job(self):
        current_index = self.job_list.currentRow()
        if current_index < 0:
            if len(self.project.jobs) > 0:
                QMessageBox.warning(self, "No Job Selected", "Please select a job first.")
            else:
                QMessageBox.warning(self, "No Job Added", "Please add a job first.")
            return
        if current_index >= 0:
            job = self.project.jobs[current_index]
            if job.enabled():
                labels = [[(self.action_text(a), a.enabled()) for a in job.sub_actions]]
                new_window, id_str = self.create_new_window("Job: " + job.params["name"], labels)
                worker = JobLogWorker(job, id_str)
                self.connect_signals(worker, new_window)
                self.start_thread(worker)
                self._workers.append(worker)
            else:
                QMessageBox.warning(self, "Can't run Job", "Job " + job.params["name"] + " is disabled.")
                return

    def run_all_jobs(self):
        labels = [[(self.action_text(a), a.enabled() and job.enabled()) for a in job.sub_actions] for job in self.project.jobs]
        project_name = ".".join(self.current_file_name().split(".")[:-1])
        if project_name == '':
            project_name = '[new]'
        new_window, id_str = self.create_new_window("Project: " + project_name, labels)
        worker = ProjectLogWorker(self.project, id_str)
        self.connect_signals(worker, new_window)
        self.start_thread(worker)
        self._workers.append(worker)

    def on_job_selected(self, index):
        self.action_list.clear()
        if 0 <= index < len(self.project.jobs):
            job = self.project.jobs[index]
            for action in job.sub_actions:
                self.action_list.addItem(self.list_item(self.action_text(action),
                                                        action.enabled()))
                if len(action.sub_actions) > 0:
                    for sub_action in action.sub_actions:
                        self.action_list.addItem(self.list_item(self.action_text(sub_action, is_sub_action=True),
                                                                sub_action.enabled()))
            self.update_delete_action_state()

    def update_delete_action_state(self):
        has_job_selected = len(self.job_list.selectedItems()) > 0
        has_action_selected = len(self.action_list.selectedItems()) > 0
        self.delete_element_action.setEnabled(has_job_selected or has_action_selected)
        if has_action_selected and has_job_selected:
            job_index = self.job_list.currentRow()
            if job_index >= len(self.project.jobs):
                job_index = len(self.project.jobs) - 1
            action_index = self.action_list.currentRow()
            job = self.project.jobs[job_index]
            action_counter = -1
            current_action = None
            is_sub_action = False
            for action in job.sub_actions:
                action_counter += 1
                if action_counter == action_index:
                    current_action = action
                    break
                if len(action.sub_actions) > 0:
                    for sub_action in action.sub_actions:
                        action_counter += 1
                        if action_counter == action_index:
                            current_action = sub_action
                            is_sub_action = True
                            break
                    if current_action:
                        break
            enable_sub_actions = current_action is not None and \
                not is_sub_action and current_action.type_name == constants.ACTION_COMBO
            self.set_enabled_sub_actions_gui(enable_sub_actions)
        else:
            self.set_enabled_sub_actions_gui(False)
