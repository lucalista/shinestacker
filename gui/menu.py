from PySide6.QtWidgets import (QMessageBox, QFileDialog, QMainWindow)
from PySide6.QtGui import QAction
from gui.project_model import Project
import os.path
import os
import json
import jsonpickle

CLONE_POSTFIX = " (clone)"


class WindowMenu(QMainWindow):
    def add_file_menu(self, menubar):
        menu = menubar.addMenu("&File")
        new_action = QAction("&New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_project)
        menu.addAction(new_action)
        open_action = QAction("&Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_project)
        menu.addAction(open_action)
        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_project)
        menu.addAction(save_action)
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self._save_project_as)
        menu.addAction(save_as_action)
        menu.addSeparator()
        exit_action = QAction("Shut down ", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)

    def add_edit_menu(self, menubar):
        menu = menubar.addMenu("Editt")
        up_action = QAction("Move &Up", self)
        up_action.setShortcut("Ctrl+U")
        up_action.triggered.connect(self._move_element_up)
        menu.addAction(up_action)
        down_action = QAction("Move &Down", self)
        down_action.setShortcut("Ctrl+D")
        down_action.triggered.connect(self._move_element_down)
        menu.addAction(down_action)
        clone_action = QAction("Clone", self)
        clone_action.setShortcut("Alt+C")
        clone_action.triggered.connect(self._clone_element)
        menu.addAction(clone_action)
        delete_action = QAction("Delete", self)
        delete_action.setShortcut("Alt+D")
        delete_action.triggered.connect(self._delete_element)
        menu.addAction(delete_action)

    def __init__(self):
        super().__init__()
        self._current_file = None
        menubar = self.menuBar()
        self.add_file_menu(menubar)
        self.add_edit_menu(menubar)

    def _new_project(self):
        if self._check_unsaved_changes():
            self.project = Project()
            self._current_file = None
            self._update_title()
            self.job_list.clear()
            self.action_list.clear()

    def _open_project(self):
        if not self._check_unsaved_changes():
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "",
            "Project Files (*.fsp);;All Files (*)")
        if file_path:
            try:
                file = open(file_path, 'r')
                json_obj = json.load(file)
                self.project = Project.from_dict(json_obj['project'])
                self._current_file = file_path
                self._update_title()
                self._refresh_ui()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot open file {file_path}:\n{str(e)}")

    def _save_project(self):
        if self._current_file:
            self._do_save(self._current_file)
        else:
            self._save_project_as()

    def _save_project_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Project As", "",
                                                   "Project Files (*.fsp);;All Files (*)")
        if file_path:
            if not file_path.endswith('.fsp'):
                file_path += '.fsp'
            self._do_save(file_path)
            self._current_file = file_path
            self._update_title()

    def _do_save(self, file_path):
        try:
            json_obj = jsonpickle.encode({
                'project': self.project.to_dict(),
                'version': 1
            })
            f = open(file_path, 'w')
            f.write(json_obj)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot save file:\n{str(e)}")

    def _check_unsaved_changes(self) -> bool:
        return True
        # ignore the following code
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

    def _update_title(self):
        title = "Focus Stacking GUI"
        if self._current_file:
            title += f" - {os.path.basename(self._current_file)}"
        self.setWindowTitle(title)

    def _shift_job(self, delta):
        job_index = self.job_list.currentRow()
        if job_index < 0:
            return
        new_index = job_index + delta
        if 0 <= new_index < len(self.project.jobs):
            jobs = self.project.jobs
            jobs.insert(new_index, jobs.pop(job_index))
            self._refresh_ui()
            self.job_list.setCurrentRow(new_index)

    def _shift_action(self, delta):
        action_row = self.action_list.currentRow()
        if action_row < 0:
            return
        job_row = self.job_list.currentRow()
        if (0 <= job_row < len(self.project.jobs)) and (0 <= action_row < self.action_list.count()):
            job = self.project.jobs[job_row]
            action_counter = -1
            sub_action_index = -1
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
            new_row = action_row
            if sub_action_index == -1:
                new_index = action_index + delta
                if 0 <= new_index < len(actions):
                    actions.insert(new_index, actions.pop(action_index))
                    new_row = 0
                    for action in actions[:new_index]:
                        new_row += 1 + len(action.sub_actions)
            else:
                new_index = sub_action_index + delta
                if 0 <= new_index < len(sub_actions):
                    sub_actions.insert(new_index, sub_actions.pop(sub_action_index))
                    new_row = 1 + new_index
                    for action in actions[:action_index]:
                        new_row += 1 + len(action.sub_actions)
        self._refresh_ui()
        self.job_list.setCurrentRow(job_row)
        self.action_list.setCurrentRow(new_row)

    def _move_element_up(self):
        if self.job_list.hasFocus():
            self._shift_job(-1)
        elif self.action_list.hasFocus():
            self._shift_action(-1)

    def _move_element_down(self):
        if self.job_list.hasFocus():
            self._shift_job(+1)
        elif self.action_list.hasFocus():
            self._shift_action(+1)

    def _clone_element(self):
        job_index = self.job_list.currentRow()
        if self.job_list.hasFocus():
            if 0 <= job_index < len(self.project.jobs):
                job_clone = self.project.jobs[job_index].clone(CLONE_POSTFIX)
                new_job_index = job_index + 1
                self.project.jobs.insert(new_job_index, job_clone)
                self.job_list.setCurrentRow(new_job_index)
                self.action_list.setCurrentRow(new_job_index)
                self._refresh_ui()
                self.job_list.setCurrentRow(new_job_index)
        elif self.action_list.hasFocus():
            action_row = self.action_list.currentRow()
            if action_row < 0:
                return
            job_row = self.job_list.currentRow()
            if (0 <= job_row < len(self.project.jobs)) and (0 <= action_row < self.action_list.count()):
                job = self.project.jobs[job_row]
                action_counter = -1
                sub_action_index = -1
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
                if sub_action_index == -1:
                    action_clone = action.clone(CLONE_POSTFIX)
                    actions.insert(action_index + 1, action_clone)
                else:
                    sub_action = sub_actions[sub_action_index]
                    sub_action_clone = sub_action.clone(CLONE_POSTFIX)
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
                self._refresh_ui()
                self.job_list.setCurrentRow(job_index)
                self.action_list.setCurrentRow(new_row)

    def _refresh_ui(self):
        self.job_list.clear()
        for job in self.project.jobs:
            self.job_list.addItem(job.params['name'])
        if self.project.jobs:
            self.job_list.setCurrentRow(0)

    def _delete_element(self):
        if self.job_list.hasFocus():
            self.delete_job()
        elif self.action_list.hasFocus():
            self.delete_action()        
            
    def delete_job(self):
        current_index = self.job_list.currentRow()
        if 0 <= current_index < len(self.project.jobs):
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete job '{self.project.jobs[current_index].params.get('name', '')}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.job_list.takeItem(current_index)
                self.project.jobs.pop(current_index)
                self.action_list.clear()
                self._refresh_ui()

    def delete_action(self):
        job_index = self.job_list.currentRow()
        action_row = self.action_list.currentRow()
        if action_row < 0:
            return
        job_row = self.job_list.currentRow()
        if (0 <= job_row < len(self.project.jobs)) and (0 <= action_row < self.action_list.count()):
            job = self.project.jobs[job_row]
            action_counter = -1
            sub_action_index = -1
            actions = job.sub_actions
            sub_actions = None
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
            current_action = action if sub_action_index == -1 else sub_action
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to delete action '{self.action_text(current_action, sub_action_index != -1, indent=False)}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                if sub_action_index != -1:
                    action.pop_sub_action(sub_action_index)
                    new_row = action_row if sub_action_index < len(sub_actions) else action_row - 1
                else:
                    job.pop_sub_action(action_index)
                    if action_index == 0:
                        new_row = 0 if len(actions) > 0 else -1
                    elif action_index < len(actions):
                        new_row = action_row
                    elif action_index == len(actions):
                        new_row = action_row - len(actions[action_index - 1].sub_actions) - 1
                self._refresh_ui()
                self.job_list.setCurrentRow(job_index)
                if new_row >= 0:
                    self.action_list.setCurrentRow(new_row)
                    
            
