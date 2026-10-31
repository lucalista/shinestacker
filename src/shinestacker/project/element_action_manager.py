# pylint: disable=W0246, E0611, R0917, R0913, W0613, R0911, R0912, R0904, E1121
import os
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QMessageBox, QDialog
from ..config.constants import constants
from ..gui.action_config_dialog import ActionConfigDialog
from ..gui.project_model import ActionConfig
from ..common_project.selection_state import SelectionState
from ..common_project.project_handler import ProjectHandler
from .rename_dialog import RenameDialog


def get_position_stack(position):
    if position[2] >= 0:
        return [position[0], position[1]], position[2]
    if position[1] >= 0:
        return [position[0]], position[1]
    if position[0] >= 0:
        return [-1], position[0]
    return [], -1


class ElementActionManager(ProjectHandler, QObject):
    project_modified_signal = Signal(bool)

    def __init__(self, project, undo_manager, selection_state, parent=None):
        ProjectHandler.__init__(self, project)
        self._undo_manager = undo_manager
        self.selection_state = selection_state
        self.action_dialog = None
        self.rename_dialog = None
        QObject.__init__(self, parent)
        self.current_file_path = ''
        self.modified = False
        self._copy_buffer = None

    def copy_buffer(self):
        return self._copy_buffer

    def set_copy_buffer(self, item):
        self._copy_buffer = item.clone()

    def has_copy_buffer(self):
        return self._copy_buffer is not None

    def mark_as_modified(self, modified=True):
        self.modified = modified

    def mark_as_not_modified(self):
        self.modified = False

    def current_file_directory(self):
        if os.path.isdir(self.current_file_path):
            return self.current_file_path
        return os.path.dirname(self.current_file_path)

    def current_file_name(self):
        if os.path.isfile(self.current_file_path):
            return os.path.basename(self.current_file_path)
        return ''

    def set_current_file_path(self, path):
        if path and not os.path.exists(path):
            raise RuntimeError(f"Path: {path} does not exist.")
        self.current_file_path = os.path.abspath(path)
        os.chdir(self.current_file_directory())

    def add_undo(self, item, description='', action_type=None,
                 old_position=None, new_position=None):
        self._undo_manager.add(item, description, action_type, old_position, new_position)

    def pop_undo(self):
        return self._undo_manager.pop()

    def filled_undo(self):
        return self._undo_manager.filled()

    @staticmethod
    def _swap_positions(entry):
        swapped = {
            'item': entry['item'],
            'description': entry['description'],
            'action_type': entry.get('action_type', ''),
            'old_position': entry.get('new_position', (-1, -1, -1)),
            'new_position': entry.get('old_position', (-1, -1, -1))
        }
        if 'modern_widget_state' in entry:
            swapped['modern_widget_state'] = entry['modern_widget_state']
        return swapped

    def undo(self):
        if self.filled_undo():
            current_state = self.project().clone()
            entry = self.pop_undo()
            counter_entry = self._swap_positions({**entry, 'item': current_state})
            self._undo_manager.add_to_redo(counter_entry)
            self.set_project(entry['item'])
            return entry
        return None

    def pop_redo(self):
        return self._undo_manager.pop_redo()

    def filled_redo(self):
        return self._undo_manager.filled_redo()

    def redo(self):
        if self.filled_redo():
            current_state = self.project().clone()
            entry = self.pop_redo()
            counter_entry = self._swap_positions({**entry, 'item': current_state})
            self._undo_manager.add_to_undo(counter_entry)
            self.set_project(entry['item'])
            return self._swap_positions(entry)
        return None

    def save_undo_state(self, description='', action_type='',
                        old_position=None, new_position=None):
        self.save_prev_undo_state(self.project().clone(), description, action_type,
                                  old_position, new_position)

    def save_prev_undo_state(self, pre_state, description='', action_type='',
                             old_position=None, new_position=None):
        self.mark_as_modified()
        self.add_undo(pre_state, description, action_type, old_position, new_position)
        self.project_modified_signal.emit(True)

    def new_state_after_op(self, state, delta):
        job_idx, act_idx, sub_idx = state.to_tuple()
        job = self.project_job(job_idx)
        if job is None:
            return SelectionState()
        if act_idx > len(job.sub_actions):
            return SelectionState(job_idx)
        if sub_idx >= 0:
            num_sub = len(job.sub_actions[act_idx].sub_actions)
            return SelectionState(job_idx, act_idx, min(sub_idx + delta, num_sub - 1))
        if act_idx >= 0:
            num_act = len(job.sub_actions)
            return SelectionState(job_idx, min(act_idx + delta, num_act - 1))
        num_job = self.num_project_jobs()
        return SelectionState(min(job_idx + delta, num_job - 1))

    def show_warning(self, title, message):
        QMessageBox.warning(self.parent() if self.parent() else self, title, message)

    def new_state_after_delete(self, state):
        return self.new_state_after_op(state, 0)

    def new_state_after_insert(self, state):
        return self.new_state_after_op(state, 1)

    def is_job_selected(self):
        return self.selection_state.is_job_selected()

    def is_action_selected(self):
        return self.selection_state.is_action_selected()

    def is_subaction_selected(self):
        return self.selection_state.is_subaction_selected()

    def confirm_delete_message(self, type_name, element_name):
        return QMessageBox.question(
            self.parent(), "Confirm Delete",
            f"Are you sure you want to delete {type_name} '{element_name}'?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes

    def copy_element(self):
        if self.selection_state and self.selection_state.is_valid():
            element = self.project_element(*self.selection_state.to_tuple())
            if element:
                self.set_copy_buffer(element.clone())

    def paste_element(self):
        if not self.has_copy_buffer():
            return False
        old_position = self.selection_state.to_tuple()
        if not self.valid_indices(*old_position):
            return False
        copy_buffer = self.copy_buffer().clone(name_postfix=constants.COPY_POSTFIX)
        if copy_buffer.type_name == constants.ACTION_JOB:
            level = 0
            idx = (-1, -1)
        elif copy_buffer.type_name in constants.ACTION_TYPES:
            level = 1
            idx = (old_position[0], -1)
        elif copy_buffer.type_name in constants.SUB_ACTION_TYPES:
            level = 2
            idx = (old_position[0], old_position[1])
            action = self.project_action(*idx)
            if not action or action.type_name != constants.ACTION_COMBO:
                return False
        else:
            return False
        container = self.project_container(*idx)
        if container is None:
            return False
        pos = old_position[level] if len(old_position) > level else -1
        insert_index = min(max(pos + 1 if pos >= 0 else len(container), 0), len(container))
        element_type = ["Job", "Action", "Subaction"][level]
        new_position = tuple(list(old_position[:level]) + [insert_index] + [-1] * (2 - level))
        self.save_undo_state(f"Paste {element_type}", "paste", old_position, tuple(new_position))
        container.insert(insert_index, copy_buffer)
        self.selection_state.from_tuple(new_position)
        return True

    def clone_element(self):
        old_position = self.selection_state.to_tuple()
        if not self.valid_indices(*old_position):
            return False
        element = self.project_element(*old_position)
        idx, s = get_position_stack(old_position)
        if len(idx) == 0:
            return False
        clone_position = list(old_position)
        if old_position[2] >= 0:
            clone_position[2] = old_position[2] + 1
        elif old_position[1] >= 0:
            clone_position[1] = old_position[1] + 1
        else:
            clone_position[0] = old_position[0] + 1
        new_position = tuple(clone_position)
        self.save_undo_state(
            f"Duplicate {self.selection_state.type().title()}",
            "clone", old_position, new_position)
        container = self.project_container(*idx)
        container.insert(s + 1, element.clone(name_postfix=constants.CLONE_POSTFIX))
        self.selection_state.from_tuple(new_position)
        return True

    def delete_element(self, confirm=True, save_copy=False):
        if not self.selection_state.is_valid():
            return False
        old_position = self.selection_state.to_tuple()
        element = self.project_element(*old_position)
        if not element:
            return False
        element_type = self.selection_state.type()
        if confirm and not self.confirm_delete_message(
                element_type, element.params.get('name', '')):
            return False
        new_selection = self.new_state_after_delete(self.selection_state)
        new_position = new_selection.to_tuple()
        self.save_undo_state(
            f"Delete {element_type.title()}", "delete", old_position, new_position)
        deleted_element = None
        idx, s = get_position_stack(old_position)
        if len(idx) == 0:
            return False
        container = self.project_container(*idx)
        if container and 0 <= s < len(container):
            deleted_element = container.pop(s)
        self.selection_state.from_tuple(new_position)
        success = deleted_element is not None
        if save_copy and success:
            self.set_copy_buffer(deleted_element)
        return success

    def cut_element(self):
        return self.delete_element(False, True)

    def shift_element(self, delta, direction):
        if not self.selection_state.is_valid():
            return False
        old_position = self.selection_state.to_tuple()
        idx, current_index = get_position_stack(old_position)
        if len(idx) == 0:
            return False
        container = self.project_container(*idx)
        if not container:
            return False
        new_index = current_index + delta
        if 0 <= new_index < len(container):
            new_position = list(old_position)
            if old_position[2] >= 0:
                new_position[2] = new_index
            elif old_position[1] >= 0:
                new_position[1] = new_index
            else:
                new_position[0] = new_index
            self.save_undo_state(f"Move {self.selection_state.type().title()} {direction}",
                                 "move", old_position, tuple(new_position))
            container.insert(new_index, container.pop(current_index))
            self.selection_state.from_tuple(new_position)
            return True
        return False

    def set_enabled_all(self, enabled):
        action = "Enable" if enabled else "Disable"
        old_position = self.selection_state.to_tuple()
        self.save_undo_state(f"{action} All", "edit_all", old_position, old_position)
        for job in self.project().jobs:
            job.set_enabled_all(enabled)

    def set_enabled(self, selection, enabled):
        if selection is None:
            return False
        position = selection.to_tuple()
        element = self.project_element(*position)
        if not element or element.enabled() == enabled:
            return False
        txt = "Enable" if enabled else "Disable"
        self.save_undo_state(f"{txt} {selection.type().title()}", "edit", position, position)
        element.set_enabled(enabled)
        return True

    def action_config_dialog(self, action):
        return ActionConfigDialog(action, self.current_file_directory(), self.parent())

    def edit_element(self, selection):
        element = self.project_element(*selection.to_tuple())
        pre_edit_project = self.project().clone()
        dialog = self.action_config_dialog(element)
        if dialog.exec() == QDialog.Accepted:
            position = selection.to_tuple()
            self.save_prev_undo_state(
                pre_edit_project, f"Edit {selection.type().title()}", "edit", position, position)
            return True
        return False

    def open_job_browse_folder_dialog(self):
        if not self.is_job_selected():
            self.show_warning("No Job Selected", "Please select a job first.")
            return ''
        job = self.project_element(*self.selection_state.to_tuple())
        if not job:
            return ''
        dialog = self.action_config_dialog(job)

        def trigger_browse():
            input_widget = dialog.configurator.input_widget
            if hasattr(input_widget, 'browse_button'):
                input_widget.browse_button.click()

        QTimer.singleShot(0, trigger_browse)
        if dialog.exec() == QDialog.Accepted:
            return os.path.basename(dialog.configurator.input_widget.path_edit.text())
        return ''

    def _rename_element(self, element, options):
        element.params['name'] = options['name']
        sub_element = element.sub_actions
        sub_options = options.get('sub')
        if len(sub_element) > 0 and sub_options:
            for e, o in zip(sub_element, sub_options):
                self._rename_element(e, o)

    def rename(self, selection):
        element = self.project_element(*selection.to_tuple())
        self.rename_dialog = RenameDialog(element, self.parent())
        if self.rename_dialog.exec() == QDialog.Accepted:
            position = selection.to_tuple()
            self.save_undo_state(f"Rename {selection.type().title()}", "rename", position, position)
            self._rename_element(element, self.rename_dialog.options)
            return True
        return False

    def add_job(self):
        job_action = ActionConfig("Job")
        self.action_dialog = self.action_config_dialog(job_action)
        if self.action_dialog.exec() != QDialog.Accepted:
            return False
        new_job_index = 0 if self.num_project_jobs() == 0 \
            else self.selection_state.job_index + 1
        old_position = self.selection_state.to_tuple()
        new_position = (new_job_index, -1, -1)
        self.save_undo_state("Add Job", "add", old_position, new_position)
        self.project_jobs().insert(new_job_index, job_action)
        self.selection_state.from_tuple(new_position)
        return True

    def add_action(self, type_name):
        job_index = self.selection_state.job_index
        if job_index < 0:
            return False
        is_valid, error_title, error_msg = self.validate_add_action(job_index)
        if not is_valid:
            self.show_warning(error_title, error_msg)
            return False
        job = self.project_job(job_index)
        action = ActionConfig(type_name)
        action.parent = job
        self.action_dialog = self.action_config_dialog(action)
        if self.action_dialog.exec() != QDialog.Accepted:
            return False
        new_selection = self.new_state_after_insert(self.selection_state)
        old_position = self.selection_state.to_tuple()
        new_position = new_selection.to_tuple()
        self.save_undo_state("Add Action", "add", old_position, new_position)
        job.sub_actions.insert(new_selection.action_index, action)
        self.selection_state.from_tuple(new_position)
        return True

    def validate_add_action(self, job_index):
        if job_index < 0:
            if self.num_project_jobs() > 0:
                return False, "No Job Selected", "Please select a job first."
            return False, "No Job Added", "Please add a job first."
        return True, "", ""

    def add_subaction(self, type_name):
        job_index = self.selection_state.job_index
        action_index = self.selection_state.action_index
        if job_index < 0 or action_index < 0:
            return False
        is_valid, error_title, error_msg = self.validate_add_subaction(job_index, action_index)
        if not is_valid:
            self.show_warning(error_title, error_msg)
            return False
        job = self.project_job(job_index)
        action = job.sub_actions[action_index]
        sub_action = ActionConfig(type_name)
        self.action_dialog = self.action_config_dialog(sub_action)
        if self.action_dialog.exec() != QDialog.Accepted:
            return False
        new_selection = self.new_state_after_insert(self.selection_state)
        old_position = self.selection_state.to_tuple()
        new_position = new_selection.to_tuple()
        self.save_undo_state(
            "Add Sub-action", "add", old_position, new_position)
        action.sub_actions.insert(new_selection.subaction_index, sub_action)
        self.selection_state.from_tuple(new_position)
        return True

    def validate_add_subaction(self, job_index, action_index):
        if job_index < 0 or action_index < 0:
            return False, "Invalid Selection", "Please select an action first."
        if job_index >= self.num_project_jobs():
            return False, "Invalid Job", "Selected job does not exist."
        job = self.project_job(job_index)
        if action_index >= len(job.sub_actions):
            return False, "Invalid Action", "Selected action does not exist."
        action = job.sub_actions[action_index]
        if action.type_name != constants.ACTION_COMBO:
            return False, "Invalid Action Type", "Sub-actions can only be added to Combo actions."
        return True, "", ""

    def perform_undo(self):
        entry = self.undo()
        if entry:
            old_position = entry.get('old_position', (-1, -1, -1))
            self.selection_state.from_tuple(old_position)
        return entry

    def perform_redo(self):
        entry = self.redo()
        if entry:
            new_position = entry.get('new_position', (-1, -1, -1))
            self.selection_state.from_tuple(new_position)
        return entry

    def clear_run_metadata(self):
        self.save_undo_state("Clear Run Information", "clear_run_info")
