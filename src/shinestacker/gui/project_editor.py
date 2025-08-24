# pylint: disable=C0114, C0115, C0116, R0904, R1702, R0917, R0913, R0902, E0611, E1131, E1121
import os
from dataclasses import dataclass
from PySide6.QtWidgets import (QListWidget, QMessageBox,
                               QDialog, QListWidgetItem, QLabel)
from PySide6.QtCore import Qt, QObject, Signal
from .. config.constants import constants
from .colors import ColorPalette
from .action_config_dialog import ActionConfigDialog
from .project_model import ActionConfig, get_action_input_path, get_action_output_path


@dataclass
class ActionPosition:
    actions: list
    sub_actions: list
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


class ProjectUndoManager:
    def __init__(self):
        self._undo_buffer = []

    def add(self, item):
        self._undo_buffer.append(item)

    def pop(self):
        return self._undo_buffer.pop()

    def filled(self):
        return len(self._undo_buffer) != 0


class ProjectEditor(QObject):
    INDENT_SPACE = "&nbsp;&nbsp;&nbsp;↪&nbsp;&nbsp;&nbsp;"
    CLONE_POSTFIX = " (clone)"

    modified_signal = Signal(int)
    select_signal = Signal()
    refresh_ui_signal = Signal(int, int)
    enable_delete_action_signal = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._undo_manager = ProjectUndoManager()
        self._modified = False
        self._project = None
        self._copy_buffer = None
        self._current_file_path = ''
        self._job_list = QListWidget()
        self._action_list = QListWidget()
        self.dialog = None

    def add_undo(self, item):
        self._undo_manager.add(item)

    def pop_undo(self):
        return self._undo_manager.pop()

    def filled_undo(self):
        return self._undo_manager.filled()

    def mark_as_modified(self, modified=True):
        self._modified = modified
        if modified:
            self.add_undo(self._project.clone())
        self.modified_signal.emit(modified)

    def modified(self):
        return self._modified

    def set_project(self, project):
        self._project = project

    def project(self):
        return self._project

    def project_jobs(self):
        return self._project.jobs

    def add_job_to_project(self, job):
        self._project.jobs.append(job)

    def num_project_jobs(self):
        return len(self.project().jobs)

    def copy_buffer(self):
        return self._copy_buffer

    def set_copy_buffer(self, item):
        self._copy_buffer = item

    def has_copy_buffer(self):
        return self._copy_buffer is not None

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

    def project_job(self, index):
        return self._project.jobs[index]

    def job_list(self):
        return self._job_list

    def action_list(self):
        return self._action_list

    def current_job_index(self):
        return self._job_list.currentRow()

    def current_action_index(self):
        return self._action_list.currentRow()

    def set_current_job(self, index):
        self._job_list.setCurrentRow(index)

    def set_current_action(self, index):
        self._action_list.setCurrentRow(index)

    def job_list_count(self):
        return self._job_list.count()

    def action_list_count(self):
        return self._action_list.count()

    def job_list_item(self, index):
        return self._job_list.item(index)

    def action_list_item(self, index):
        return self._action_list.item(index)

    def job_list_has_focus(self):
        return self._job_list.hasFocus()

    def action_list_has_focus(self):
        return self._action_list.hasFocus()

    def take_job(self, index):
        return self._job_list.takeItem(index)

    def clear_job_list(self):
        self._job_list.clear()

    def clear_action_list(self):
        self._action_list.clear()

    def num_selected_jobs(self):
        return len(self._job_list.selectedItems())

    def num_selected_actions(self):
        return len(self._action_list.selectedItems())

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
            txt = self.INDENT_SPACE
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
        return None if index < 0 else self.project_job(index)

    def get_current_job(self):
        return self.get_job_at(self.current_job_index())

    def get_current_action(self):
        return self.get_action_at(self.current_action_index())

    def get_action_at(self, action_row):
        job_row = self.current_job_index()
        if job_row < 0 or action_row < 0:
            return (job_row, action_row, None)
        action, sub_action, sub_action_index = self.find_action_position(job_row, action_row)
        if not action:
            return (job_row, action_row, None)
        job = self.project_job(job_row)
        if sub_action:
            return (job_row, action_row,
                    ActionPosition(job.sub_actions, action.sub_actions,
                                   job.sub_actions.index(action), sub_action_index))
        return (job_row, action_row,
                ActionPosition(job.sub_actions, None, job.sub_actions.index(action)))

    def find_action_position(self, job_index, ui_index):
        if not 0 <= job_index < self.num_project_jobs():
            return (None, None, -1)
        actions = self.project_job(job_index).sub_actions
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

    def shift_job(self, delta):
        job_index = self.current_job_index()
        if job_index < 0:
            return
        new_index = job_index + delta
        if 0 <= new_index < self.num_project_jobs():
            jobs = self.project_jobs()
            self.mark_as_modified()
            jobs.insert(new_index, jobs.pop(job_index))
            self.refresh_ui_signal.emit(new_index, -1)

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
            self.refresh_ui_signal.emit(job_row, new_row)

    def move_element_up(self):
        if self.job_list_has_focus():
            self.shift_job(-1)
        elif self.action_list_has_focus():
            self.shift_action(-1)

    def move_element_down(self):
        if self.job_list_has_focus():
            self.shift_job(+1)
        elif self.action_list_has_focus():
            self.shift_action(+1)

    def clone_job(self):
        job_index = self.current_job_index()
        if 0 <= job_index < self.num_project_jobs():
            job_clone = self.project_job(job_index).clone(self.CLONE_POSTFIX)
            new_job_index = job_index + 1
            self.mark_as_modified()
            self.project_jobs().insert(new_job_index, job_clone)
            self.set_current_job(new_job_index)
            self.set_current_action(new_job_index)
            self.refresh_ui_signal.emit(new_job_index, -1)

    def clone_action(self):
        job_row, action_row, pos = self.get_current_action()
        if not pos.actions:
            return
        self.mark_as_modified()
        job = self.project_job(job_row)
        if pos.is_sub_action:
            cloned = pos.sub_action.clone(self.CLONE_POSTFIX)
            pos.sub_actions.insert(pos.sub_action_index + 1, cloned)
        else:
            cloned = pos.action.clone(self.CLONE_POSTFIX)
            job.sub_actions.insert(pos.action_index + 1, cloned)
        new_row = new_row_after_clone(job, action_row, pos.is_sub_action, cloned)
        self.refresh_ui_signal.emit(job_row, new_row)

    def clone_element(self):
        if self.job_list_has_focus():
            self.clone_job()
        elif self.action_list_has_focus():
            self.clone_action()

    def delete_job(self, confirm=True):
        current_index = self.current_job_index()
        if 0 <= current_index < self.num_project_jobs():
            if confirm:
                reply = QMessageBox.question(
                    self.parent(), "Confirm Delete",
                    "Are you sure you want to delete job "
                    f"'{self.project_job(current_index).params.get('name', '')}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
            else:
                reply = None
            if not confirm or reply == QMessageBox.Yes:
                self.take_job(current_index)
                self.mark_as_modified()
                current_job = self.project_jobs().pop(current_index)
                self.clear_action_list()
                self.refresh_ui_signal.emit(-1, -1)
                return current_job
        return None

    def delete_action(self, confirm=True):
        job_row, action_row, pos = self.get_current_action()
        if pos is not None:
            current_action = pos.action if not pos.is_sub_action else pos.sub_action
            if confirm:
                reply = QMessageBox.question(
                    self.parent(),
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
                    self.project_job(job_row).pop_sub_action(pos.action_index)
                new_row = new_row_after_delete(action_row, pos)
                self.refresh_ui_signal.emit(job_row, new_row)
            return current_action
        return None

    def delete_element(self, confirm=True):
        if self.job_list_has_focus():
            element = self.delete_job(confirm)
        elif self.action_list_has_focus():
            element = self.delete_action(confirm)
        else:
            element = None
        return element

    def action_config_dialog(self, action):
        return ActionConfigDialog(action, self.current_file_directory(), self.parent())

    def add_job(self):
        job_action = ActionConfig("Job")
        self.dialog = self.action_config_dialog(job_action)
        if self.dialog.exec() == QDialog.Accepted:
            self.mark_as_modified()
            self.project_jobs().append(job_action)
            self.add_list_item(self.job_list(), job_action, False)
            self.set_current_job(self.job_list_count() - 1)
            self.job_list_item(self.job_list_count() - 1).setSelected(True)
            self.refresh_ui_signal.emit(-1, -1)

    def add_action(self, type_name):
        current_index = self.current_job_index()
        if current_index < 0:
            if self.num_project_jobs() > 0:
                QMessageBox.warning(self.parent(),
                                    "No Job Selected", "Please select a job first.")
            else:
                QMessageBox.warning(self.parent(),
                                    "No Job Added", "Please add a job first.")
            return
        action = ActionConfig(type_name)
        action.parent = self.get_current_job()
        self.dialog = self.action_config_dialog(action)
        if self.dialog.exec() == QDialog.Accepted:
            self.mark_as_modified()
            self.project_job(current_index).add_sub_action(action)
            self.add_list_item(self.action_list(), action, False)
            self.enable_delete_action_signal.emit(False)

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

    def add_sub_action(self, type_name):
        current_job_index = self.current_job_index()
        current_action_index = self.current_action_index()
        if current_job_index < 0 or current_action_index < 0 or \
           current_job_index >= self.num_project_jobs():
            return
        job = self.project_job(current_job_index)
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
        sub_action = ActionConfig(type_name)
        self.dialog = self.action_config_dialog(sub_action)
        if self.dialog.exec() == QDialog.Accepted:
            self.mark_as_modified()
            action.add_sub_action(sub_action)
            self.on_job_selected(current_job_index)
            self.set_current_action(current_action_index)

    def copy_job(self):
        current_index = self.current_job_index()
        if 0 <= current_index < self.num_project_jobs():
            self.set_copy_buffer(self.project_job(current_index).clone())

    def copy_action(self):
        _job_row, _action_row, pos = self.get_current_action()
        if pos.actions is not None:
            self.set_copy_buffer(pos.sub_action.clone()
                                 if pos.is_sub_action else pos.action.clone())

    def copy_element(self):
        if self.job_list_has_focus():
            self.copy_job()
        elif self.action_list_has_focus():
            self.copy_action()

    def paste_job(self):
        if self.copy_buffer().type_name != constants.ACTION_JOB:
            return
        job_index = self.current_job_index()
        if 0 <= job_index < self.num_project_jobs():
            new_job_index = job_index
            self.mark_as_modified()
            self.project_jobs().insert(new_job_index, self.copy_buffer())
            self.set_current_job(new_job_index)
            self.set_current_action(new_job_index)
            self.refresh_ui_signal.emit(new_job_index, -1)

    def paste_action(self):
        job_row, action_row, pos = self.get_current_action()
        if pos.actions is not None:
            if not pos.is_sub_action:
                if self.copy_buffer().type_name not in constants.ACTION_TYPES:
                    return
                self.mark_as_modified()
                pos.actions.insert(pos.action_index, self.copy_buffer())
            else:
                if pos.action.type_name != constants.ACTION_COMBO or \
                   self.copy_buffer().type_name not in constants.SUB_ACTION_TYPES:
                    return
                self.mark_as_modified()
                pos.sub_actions.insert(pos.sub_action_index, self.copy_buffer())
            new_row = new_row_after_paste(action_row, pos)
            self.refresh_ui_signal.emit(job_row, new_row)

    def paste_element(self):
        if self.has_copy_buffer():
            if self.job_list_has_focus():
                self.paste_job()
            elif self.action_list_has_focus():
                self.paste_action()

    def cut_element(self):
        self.set_copy_buffer(self.delete_element(False))

    def undo(self):
        job_row = self.current_job_index()
        action_row = self.current_action_index()
        if self.filled_undo():
            self.set_project(self.pop_undo())
            self.refresh_ui_signal.emit(-1, -1)
            len_jobs = self.num_project_jobs()
            if len_jobs > 0:
                job_row = min(job_row, len_jobs - 1)
                self.set_current_job(job_row)
                len_actions = self.action_list_count()
                if len_actions > 0:
                    action_row = min(action_row, len_actions)
                    self.set_current_action(action_row)

    def set_enabled(self, enabled):
        current_action = None
        if self.job_list_has_focus():
            job_row = self.current_job_index()
            if 0 <= job_row < self.num_project_jobs():
                current_action = self.project_job(job_row)
            action_row = -1
        elif self.action_list_has_focus():
            job_row, action_row, pos = self.get_current_action()
            current_action = pos.sub_action if pos.is_sub_action else pos.action
        else:
            action_row = -1
        if current_action:
            if current_action.enabled() != enabled:
                self.mark_as_modified()
                current_action.set_enabled(enabled)
                self.refresh_ui_signal.emit(job_row, action_row)

    def enable(self):
        self.set_enabled(True)

    def disable(self):
        self.set_enabled(False)

    def set_enabled_all(self, enable=True):
        self.mark_as_modified()
        job_row = self.current_job_index()
        action_row = self.current_action_index()
        for j in self.project_jobs():
            j.set_enabled_all(enable)
        self.refresh_ui_signal.emit(job_row, action_row)

    def enable_all(self):
        self.set_enabled_all(True)

    def disable_all(self):
        self.set_enabled_all(False)

    def on_job_selected(self, index):
        self.clear_action_list()
        if 0 <= index < self.num_project_jobs():
            job = self.project_job(index)
            for action in job.sub_actions:
                self.add_list_item(self.action_list(), action, False)
                if len(action.sub_actions) > 0:
                    for sub_action in action.sub_actions:
                        self.add_list_item(self.action_list(), sub_action, True)
            self.select_signal.emit()

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
