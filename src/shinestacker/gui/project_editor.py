# pylint: disable=C0114, C0115, C0116, R0904, R1702, R0917, R0913, R0902, E0611, E1131
import os
from dataclasses import dataclass
from PySide6.QtWidgets import (QMainWindow, QListWidget, QMessageBox,
                               QDialog, QListWidgetItem, QLabel)
from PySide6.QtCore import Qt
from .. config.constants import constants
from .colors import ColorPalette
from .action_config import ActionConfig, ActionConfigDialog
from .project_model import get_action_input_path, get_action_output_path

INDENT_SPACE = "&nbsp;&nbsp;&nbsp;↪&nbsp;&nbsp;&nbsp;"
CLONE_POSTFIX = " (clone)"


@dataclass
class ActionPosition:
    actions: list
    sub_actions: list | None
    action_index: int
    sub_action_index: int = -1

    @property
    def is_sub_action(self) -> bool:
        return self.sub_action_index != -1

    @property
    def action(self):
        return None if self.actions is None else self.actions[self.action_index]

    @property
    def sub_action(self):
        return None if self.sub_actions is None or \
                       self.sub_action_index == -1 \
                       else self.sub_actions[self.sub_action_index]


def new_row_after_delete(action_row, pos: ActionPosition):
    if pos.is_sub_action:
        new_row = action_row if pos.sub_action_index < len(pos.sub_actions) else action_row - 1
    else:
        if pos.action_index == 0:
            new_row = 0 if len(pos.actions) > 0 else -1
        elif pos.action_index < len(pos.actions):
            new_row = action_row
        elif pos.action_index == len(pos.actions):
            new_row = action_row - len(pos.actions[pos.action_index - 1].sub_actions) - 1
        else:
            new_row = None
    return new_row


def new_row_after_insert(action_row, pos: ActionPosition, delta):
    new_row = action_row
    if not pos.is_sub_action:
        new_index = pos.action_index + delta
        if 0 <= new_index < len(pos.actions):
            new_row = 0
            for action in pos.actions[:new_index]:
                new_row += 1 + len(action.sub_actions)
    else:
        new_index = pos.sub_action_index + delta
        if 0 <= new_index < len(pos.sub_actions):
            new_row = 1 + new_index
            for action in pos.actions[:pos.action_index]:
                new_row += 1 + len(action.sub_actions)
    return new_row


def new_row_after_paste(action_row, pos: ActionPosition):
    return new_row_after_insert(action_row, pos, 0)


def new_row_after_clone(job, action_row, is_sub_action, cloned):
    return action_row + 1 if is_sub_action else \
        sum(1 + len(action.sub_actions)
            for action in job.sub_actions[:job.sub_actions.index(cloned)])


class ProjectEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self._copy_buffer = None
        self.project_buffer = []
        self.job_list = QListWidget()
        self.action_list = QListWidget()
        self.project = None
        self.job_list_model = None
        self.expert_options = False
        self.script_dir = os.path.dirname(__file__)
        self.dialog = None
        self._current_file_path = ''
        self._modified_project = False

    def current_file_path(self):
        return self._current_file_path

    def current_file_directory(self):
        if os.path.isdir(self._current_file_path):
            return self._current_file_path
        return os.path.dirname(self._current_file_path)

    def current_file_name(self):
        if os.path.isfile(self._current_file_path):
            return os.path.basename(self._current_file_path)
        return ''

    def set_current_file_path(self, path):
        if path and not os.path.exists(path):
            raise RuntimeError(f"Path: {path} does not exist.")
        self._current_file_path = os.path.abspath(path)
        os.chdir(self.current_file_directory())

    def set_project(self, project):
        self.project = project

    def job_text(self, job, long_name=False, html=False):
        txt = f"{job.params.get('name', '(job)')}"
        if html:
            txt = f"<b>{txt}</b>"
        in_path = get_action_input_path(job)
        return txt + (f" [⚙️ Job: 📁 {in_path[0]} → 📂 ...]" if long_name else "")

    def action_text(self, action, is_sub_action=False, indent=True, long_name=False, html=False):
        icon_map = {
            constants.ACTION_COMBO: '⚡',
            constants.ACTION_NOISEDETECTION: '🌫',
            constants.ACTION_FOCUSSTACK: '🎯',
            constants.ACTION_FOCUSSTACKBUNCH: '🖇',
            constants.ACTION_MULTILAYER: '🎞️',
            constants.ACTION_MASKNOISE: '🎭',
            constants.ACTION_VIGNETTING: '⭕️',
            constants.ACTION_ALIGNFRAMES: '📐',
            constants.ACTION_BALANCEFRAMES: '🌈'
        }
        ico = icon_map.get(action.type_name, '')
        if is_sub_action and indent:
            txt = INDENT_SPACE
            if ico == '':
                ico = '🟣'
        else:
            txt = ''
            if ico == '':
                ico = '🔵'
        if action.params.get('name', '') != '':
            txt += f"{action.params['name']}"
            if html:
                txt = f"<b>{txt}</b>"
        in_path, out_path = get_action_input_path(action), get_action_output_path(action)
        return f"{txt} [{ico} {action.type_name}" + \
               (f": 📁 <i>{in_path[0]}</i> → 📂 <i>{out_path[0]}</i>]"
                if long_name and not is_sub_action else "]")

    def get_job_at(self, index):
        return None if index < 0 else self.project.jobs[index]

    def get_current_job(self):
        return self.get_job_at(self.job_list.currentRow())

    def get_current_action(self):
        return self.get_action_at(self.action_list.currentRow())

    def get_action_at(self, action_row):
        job_row = self.job_list.currentRow()
        if job_row < 0 or action_row < 0:
            return (job_row, action_row, None)
        action, sub_action, sub_action_index = self.find_action_position(job_row, action_row)
        if not action:
            return (job_row, action_row, None)
        job = self.project.jobs[job_row]
        if sub_action:
            return (job_row, action_row,
                    ActionPosition(job.sub_actions, action.sub_actions,
                                   job.sub_actions.index(action), sub_action_index))
        return (job_row, action_row,
                ActionPosition(job.sub_actions, None, job.sub_actions.index(action)))

    def find_action_position(self, job_index, ui_index):
        if not 0 <= job_index < len(self.project.jobs):
            return (None, None, -1)
        actions = self.project.jobs[job_index].sub_actions
        counter = -1
        for action in actions:
            counter += 1
            if counter == ui_index:
                return (action, None, -1)
            for sub_action_index, sub_action in enumerate(action.sub_actions):
                counter += 1
                if counter == ui_index:
                    return (action, sub_action, sub_action_index)
        return (None, None, -1)

    def refresh_ui(self, job_row=-1, action_row=-1):
        pass

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

    def shift_action(self, delta):
        job_row, action_row, pos = self.get_current_action()
        if pos is not None:
            if not pos.is_sub_action:
                new_index = pos.action_index + delta
                if 0 <= new_index < len(pos.actions):
                    self.mark_as_modified()
                    pos.actions.insert(new_index, pos.actions.pop(pos.action_index))
            else:
                new_index = pos.sub_action_index + delta
                if 0 <= new_index < len(pos.sub_actions):
                    self.mark_as_modified()
                    pos.sub_actions.insert(new_index, pos.sub_actions.pop(pos.sub_action_index))
            new_row = new_row_after_insert(action_row, pos, delta)
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
        job_row, action_row, pos = self.get_current_action()
        if not pos.actions:
            return
        self.mark_as_modified()
        job = self.project.jobs[job_row]
        if pos.is_sub_action:
            cloned = pos.sub_action.clone(CLONE_POSTFIX)
            pos.sub_actions.insert(pos.sub_action_index + 1, cloned)
        else:
            cloned = pos.action.clone(CLONE_POSTFIX)
            job.sub_actions.insert(pos.action_index + 1, cloned)
        new_row = new_row_after_clone(job, action_row, pos.is_sub_action, cloned)
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
                    "Are you sure you want to delete job "
                    f"'{self.project.jobs[current_index].params.get('name', '')}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
            else:
                reply = None
            if not confirm or reply == QMessageBox.Yes:
                self.job_list.takeItem(current_index)
                self.mark_as_modified()
                current_job = self.project.jobs.pop(current_index)
                self.action_list.clear()
                self.refresh_ui()
                return current_job
        return None

    def delete_action(self, confirm=True):
        job_row, action_row, pos = self.get_current_action()
        if pos is not None:
            current_action = pos.action if not pos.is_sub_action else pos.sub_action
            if confirm:
                reply = QMessageBox.question(
                    self,
                    "Confirm Delete",
                    "Are you sure you want to delete action "
                    f"'{self.action_text(current_action, pos.is_sub_action, indent=False)}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
            else:
                reply = None
            if not confirm or reply == QMessageBox.Yes:
                self.mark_as_modified()
                if pos.is_sub_action:
                    pos.action.pop_sub_action(pos.sub_action_index)
                else:
                    self.project.jobs[job_row].pop_sub_action(pos.action_index)
                new_row = new_row_after_delete(action_row, pos)
                self.refresh_ui(job_row, new_row)
            return current_action
        return None

    def delete_element(self, confirm=True):
        if self.job_list.hasFocus():
            element = self.delete_job(confirm)
        elif self.action_list.hasFocus():
            element = self.delete_action(confirm)
        else:
            element = None
        if self.job_list.count() > 0:
            self.delete_element_action.setEnabled(True)
        return element

    def action_config_dialog(self, action):
        return ActionConfigDialog(action, self.current_file_directory(), self)

    def add_job(self):
        job_action = ActionConfig("Job")
        self.dialog = self.action_config_dialog(job_action)
        if self.dialog.exec() == QDialog.Accepted:
            self.mark_as_modified()
            self.project.jobs.append(job_action)
            self.add_list_item(self.job_list, job_action, False)
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
        self.dialog = self.action_config_dialog(action)
        if self.dialog.exec() == QDialog.Accepted:
            self.mark_as_modified()
            self.project.jobs[current_index].add_sub_action(action)
            self.add_list_item(self.action_list, action, False)
            self.delete_element_action.setEnabled(False)

    def add_list_item(self, widget_list, action, is_sub_action):
        if action.type_name == constants.ACTION_JOB:
            text = self.job_text(action, long_name=True, html=True)
        else:
            text = self.action_text(action, long_name=True, html=True, is_sub_action=is_sub_action)
        item = QListWidgetItem()
        item.setText('')
        item.setData(Qt.ItemDataRole.UserRole, True)
        widget_list.addItem(item)
        html_text = f"✅ <span style='color:#{ColorPalette.DARK_BLUE.hex()};'>{text}</span>" \
                    if action.enabled() \
                    else f"🚫 <span style='color:#{ColorPalette.DARK_RED.hex()};'>{text}</span>"
        label = QLabel(html_text)
        widget_list.setItemWidget(item, label)

    def add_sub_action(self, type_name=False):
        current_job_index = self.job_list.currentRow()
        current_action_index = self.action_list.currentRow()
        if current_job_index < 0 or current_action_index < 0 or \
           current_job_index >= len(self.project.jobs):
            return
        job = self.project.jobs[current_job_index]
        action = None
        action_counter = -1
        for act in job.sub_actions:
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
        self.dialog = self.action_config_dialog(sub_action)
        if self.dialog.exec() == QDialog.Accepted:
            self.mark_as_modified()
            action.add_sub_action(sub_action)
            self.on_job_selected(current_job_index)
            self.action_list.setCurrentRow(current_action_index)

    def copy_job(self):
        current_index = self.job_list.currentRow()
        if 0 <= current_index < len(self.project.jobs):
            self._copy_buffer = self.project.jobs[current_index].clone()

    def copy_action(self):
        _job_row, _action_row, pos = self.get_current_action()
        if pos.actions is not None:
            self._copy_buffer = pos.sub_action.clone() if pos.is_sub_action else pos.action.clone()

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
        job_row, action_row, pos = self.get_current_action()
        if pos.actions is not None:
            if not pos.is_sub_action:
                if self._copy_buffer.type_name not in constants.ACTION_TYPES:
                    return
                self.mark_as_modified()
                pos.actions.insert(pos.action_index, self._copy_buffer)
            else:
                if pos.action.type_name != constants.ACTION_COMBO or \
                   self._copy_buffer.type_name not in constants.SUB_ACTION_TYPES:
                    return
                self.mark_as_modified()
                pos.sub_actions.insert(pos.sub_action_index, self._copy_buffer)
            new_row = new_row_after_paste(action_row, pos)
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
        if len(self.project_buffer) > 0:
            self.set_project(self.project_buffer.pop())
            self.refresh_ui()
            len_jobs = len(self.project.jobs)
            if len_jobs > 0:
                if job_row >= len_jobs:
                    job_row = len_jobs - 1
                self.job_list.setCurrentRow(job_row)
                len_actions = self.action_list.count()
                if len_actions > 0:
                    action_row = min(action_row, len_actions)
                    self.action_list.setCurrentRow(action_row)

    def set_enabled(self, enabled):
        current_action = None
        if self.job_list.hasFocus():
            job_row = self.job_list.currentRow()
            if 0 <= job_row < len(self.project.jobs):
                current_action = self.project.jobs[job_row]
            action_row = -1
        elif self.action_list.hasFocus():
            job_row, action_row, pos = self.get_current_action()
            current_action = pos.sub_action if pos.is_sub_action else pos.action
        else:
            action_row = -1
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

    def on_job_selected(self, index):
        self.action_list.clear()
        if 0 <= index < len(self.project.jobs):
            job = self.project.jobs[index]
            for action in job.sub_actions:
                self.add_list_item(self.action_list, action, False)
                if len(action.sub_actions) > 0:
                    for sub_action in action.sub_actions:
                        self.add_list_item(self.action_list, sub_action, True)
            self.update_delete_action_state()

    def get_current_action_at(self, job, action_index):
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

        return current_action, is_sub_action

    def update_delete_action_state(self):
        has_job_selected = len(self.job_list.selectedItems()) > 0
        has_action_selected = len(self.action_list.selectedItems()) > 0
        self.delete_element_action.setEnabled(has_job_selected or has_action_selected)
        if has_action_selected and has_job_selected:
            job_index = self.job_list.currentRow()
            if job_index >= len(self.project.jobs):
                job_index = len(self.project.jobs) - 1
            action_index = self.action_list.currentRow()
            if job_index >= 0:
                job = self.project.jobs[job_index]
                current_action, is_sub_action = self.get_current_action_at(job, action_index)
                enable_sub_actions = current_action is not None and \
                    not is_sub_action and current_action.type_name == constants.ACTION_COMBO
                self.set_enabled_sub_actions_gui(enable_sub_actions)
        else:
            self.set_enabled_sub_actions_gui(False)
