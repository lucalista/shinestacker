from PySide6.QtWidgets import (QMessageBox, QFileDialog, QMainWindow, QListWidgetItem, QDialog, QMenu)
from PySide6.QtGui import QAction, QColor, QIcon
from gui.project_model import Project, ActionConfig
from gui.project_model import (ACTION_JOB, ACTION_COMBO, ACTION_TYPES, SUB_ACTION_TYPES,
                               ACTION_COMBO, ACTION_NOISEDETECTION, ACTION_FOCUSSTACK, ACTION_FOCUSSTACKBUNCH, ACTION_MULTILAYER,
                               ACTION_MASKNOISE, ACTION_VIGNETTING, ACTION_ALIGNFRAMES, ACTION_BALANCEFRAMES)

from gui.gui_run import ColorPalette
from gui.action_config import ActionConfigDialog
import os.path
import os
import json
import jsonpickle
import webbrowser

CLONE_POSTFIX = " (clone)"
DONT_USE_NATIVE_MENU = True
ENABLED_LIST_ITEM_COLOR = ColorPalette.DARK_BLUE.tuple()
DISABLED_LIST_ITEM_COLOR = ColorPalette.DARK_RED.tuple()



class WindowMenu(QMainWindow):
    _copy_buffer = None
    _modified_project = False
    _project_buffer = []

    def list_item(self, text, enabled):
        script_dir = os.path.dirname(__file__)
        if enabled:
            color = QColor(*ENABLED_LIST_ITEM_COLOR)
            icon = QIcon(os.path.join(script_dir, "img/on.png"))
        else:
            color = QColor(*DISABLED_LIST_ITEM_COLOR)
            icon = QIcon(os.path.join(script_dir, "img/off.png"))
        item = QListWidgetItem(icon, text)
        item.setForeground(color)
        return item

    def touch_project(self):
        self._modified_project = True
        self._project_buffer.append(self.project.clone())

    def add_file_menu(self, menubar):
        menu = menubar.addMenu("&File")
        new_action = QAction("&New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        menu.addAction(new_action)
        open_action = QAction("&Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_project)
        menu.addAction(open_action)
        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        menu.addAction(save_action)
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)
        menu.addAction(save_as_action)
        menu.addSeparator()
        if DONT_USE_NATIVE_MENU:
            quit_txt, quit_short = "&Quit", "Ctrl+Q"
        else:
            quit_txt. quit_short = "Shut dw&wn", "Ctrl+W"
        exit_action = QAction(quit_txt, self)
        exit_action.setShortcut(quit_short)
        exit_action.triggered.connect(self.quit)
        menu.addAction(exit_action)

    def add_edit_menu(self, menubar):
        menu = menubar.addMenu("&Edit")
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        menu.addAction(undo_action)
        menu.addSeparator()
        cut_action = QAction("&Cut", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self.cut_element)
        menu.addAction(cut_action)
        copy_action = QAction("Cop&y", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy_element)
        menu.addAction(copy_action)
        paste_action = QAction("&Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.paste_element)
        menu.addAction(paste_action)
        clone_action = QAction("Duplicate", self)
        clone_action.setShortcut("Ctrl+D")
        clone_action.triggered.connect(self.clone_element)
        menu.addAction(clone_action)
        delete_action = QAction("Delete", self)
        delete_action.setShortcut("Del")  # Qt.Key_Backspace
        delete_action.triggered.connect(self.delete_element)
        menu.addAction(delete_action)
        menu.addSeparator()
        up_action = QAction("Move &Up", self)
        up_action.setShortcut("Ctrl+Up")
        up_action.triggered.connect(self.move_element_up)
        menu.addAction(up_action)
        down_action = QAction("Move &Down", self)
        down_action.setShortcut("Ctrl+Down")
        down_action.triggered.connect(self.move_element_down)
        menu.addAction(down_action)
        menu.addSeparator()
        enable_action = QAction("E&nable", self)
        enable_action.setShortcut("Ctrl+E")
        enable_action.triggered.connect(self.enable)
        menu.addAction(enable_action)
        disable_action = QAction("Di&sable", self)
        disable_action.setShortcut("Ctrl+B")
        disable_action.triggered.connect(self.disable)
        menu.addAction(disable_action)
        enable_all_action = QAction("Enable All", self)
        enable_all_action.setShortcut("Ctrl+Shift+E")
        enable_all_action.triggered.connect(self.enable_all)
        menu.addAction(enable_all_action)
        disable_all_action = QAction("Disable All", self)
        disable_all_action.setShortcut("Ctrl+Shift+B")
        disable_all_action.triggered.connect(self.disable_all)
        menu.addAction(disable_all_action)

    def add_job_menu(self, menubar):
        menu = menubar.addMenu("&Jobs")
        add_job_action = QAction("Add Job", self)
        add_job_action.setShortcut("Ctrl+P")
        add_job_action.triggered.connect(self.add_job)
        menu.addAction(add_job_action)
        menu.addSeparator()        
        self.run_job_action = QAction("Run Job", self)
        self.run_job_action.setShortcut("Ctrl+J")
        self.run_job_action.triggered.connect(self.run_job)
        menu.addAction(self.run_job_action)
        self.run_all_jobs_action = QAction("Run All Jobs", self)
        self.run_all_jobs_action.setShortcut("Ctrl+J")
        self.run_all_jobs_action.triggered.connect(self.run_all_jobs)
        self.run_all_jobs_action.setShortcut("Ctrl+Shift+J")
        menu.addAction(self.run_all_jobs_action)

    def add_actions_menu(self, menubar):
        menu = menubar.addMenu("&Actions")
        add_action_menu = QMenu("Add Action", self)
        for action in ACTION_TYPES:
            entry_action = QAction(action, self)
            entry_action.triggered.connect({
                ACTION_COMBO: self.add_action_CombinedActions,
                ACTION_NOISEDETECTION: self.add_action_NoiseDetection,
                ACTION_FOCUSSTACK: self.add_action_FocusStack,
                ACTION_FOCUSSTACKBUNCH: self.add_action_FocusStackBunch,
                ACTION_MULTILAYER: self.add_action_MultiLayer
            }[action])
            add_action_menu.addAction(entry_action)
        menu.addMenu(add_action_menu)
        add_sub_action_menu = QMenu("Add Sub Action", self)
        self.sub_action_menu_entries = []
        for action in SUB_ACTION_TYPES:
            entry_action = QAction(action, self)
            entry_action.triggered.connect({
                ACTION_MASKNOISE: self.add_sub_action_MakeNoise,
                ACTION_VIGNETTING: self.add_sub_action_Vignetting,
                ACTION_ALIGNFRAMES: self.add_sub_action_AlignFrames,
                ACTION_BALANCEFRAMES: self.add_sub_action_BalanceFrames
            }[action])
            entry_action.setEnabled(False)
            self.sub_action_menu_entries.append(entry_action)
            add_sub_action_menu.addAction(entry_action)
        menu.addMenu(add_sub_action_menu)

    def add_help_menu(self, menubar):
        menu = menubar.addMenu("&Help")
        help_action = QAction("Online Help", self)
        help_action.triggered.connect(self.website)
        menu.addAction(help_action)
        
    def __init__(self):
        super().__init__()
        self._current_file = None
        menubar = self.menuBar()
        self.add_file_menu(menubar)
        self.add_edit_menu(menubar)
        self.add_job_menu(menubar)
        self.add_actions_menu(menubar)
        self.add_help_menu(menubar)

    def website(self):
        webbrowser.open("https://github.com/lucalista/focusstack/blob/main/docs/main.md")

    def _refresh_ui(self, job_row=-1, action_row=-1):
        self.job_list.clear()
        for job in self.project.jobs:
            self.job_list.addItem(self.list_item(self.job_text(job), job.enabled()))
        if self.project.jobs:
            self.job_list.setCurrentRow(0)
        if job_row >= 0:
            self.job_list.setCurrentRow(job_row)
        if action_row >= 0:
            self.action_list.setCurrentRow(action_row)

    def _update_title(self):
        title = "Focus Stacking GUI"
        if self._current_file:
            title += f" - {os.path.basename(self._current_file)}"
        self.setWindowTitle(title)

    def quit(self):
        if self._check_unsaved_changes():
            self.close()

    def new_project(self):
        if self._check_unsaved_changes():
            self.project = Project()
            self._current_file = None
            self._update_title()
            self.job_list.clear()
            self.action_list.clear()
            self._modified_project = False

    def open_project(self):
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
                self._refresh_ui(0, -1)
                if self.job_list.count() > 0:
                    self.job_list.setCurrentRow(0)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot open file {file_path}:\n{str(e)}")
        self._modified_project = False

    def save_project(self):
        if self._current_file:
            self.do_save(self._current_file)
        else:
            self.save_project_as()

    def save_project_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Project As", "",
                                                   "Project Files (*.fsp);;All Files (*)")
        if file_path:
            if not file_path.endswith('.fsp'):
                file_path += '.fsp'
            self.do_save(file_path)
            self._current_file = file_path
            self._update_title()

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

    def _shift_job(self, delta):
        job_index = self.job_list.currentRow()
        if job_index < 0:
            return
        new_index = job_index + delta
        if 0 <= new_index < len(self.project.jobs):
            jobs = self.project.jobs
            self.touch_project()
            jobs.insert(new_index, jobs.pop(job_index))
            self._refresh_ui(new_index, -1)

    def _get_current_action(self):
        action_row = self.action_list.currentRow()
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

    def _shift_action(self, delta):
        job_row, action_row, actions, sub_actions, action_index, sub_action_index = self._get_current_action()
        if actions is not None:
            new_row = action_row
            if sub_action_index == -1:
                new_index = action_index + delta
                if 0 <= new_index < len(actions):
                    self.touch_project()
                    actions.insert(new_index, actions.pop(action_index))
                    new_row = 0
                    for action in actions[:new_index]:
                        new_row += 1 + len(action.sub_actions)
            else:
                new_index = sub_action_index + delta
                if 0 <= new_index < len(sub_actions):
                    self.touch_project()
                    sub_actions.insert(new_index, sub_actions.pop(sub_action_index))
                    new_row = 1 + new_index
                    for action in actions[:action_index]:
                        new_row += 1 + len(action.sub_actions)
            self._refresh_ui(job_row, new_row)

    def move_element_up(self):
        if self.job_list.hasFocus():
            self._shift_job(-1)
        elif self.action_list.hasFocus():
            self._shift_action(-1)

    def move_element_down(self):
        if self.job_list.hasFocus():
            self._shift_job(+1)
        elif self.action_list.hasFocus():
            self._shift_action(+1)

    def clone_job(self):
        job_index = self.job_list.currentRow()
        if 0 <= job_index < len(self.project.jobs):
            job_clone = self.project.jobs[job_index].clone(CLONE_POSTFIX)
            new_job_index = job_index + 1
            self.touch_project()
            self.project.jobs.insert(new_job_index, job_clone)
            self.job_list.setCurrentRow(new_job_index)
            self.action_list.setCurrentRow(new_job_index)
            self._refresh_ui(new_job_index, -1)

    def clone_action(self):
        job_row, action_row, actions, sub_actions, action_index, sub_action_index = self._get_current_action()
        action = actions[action_index]
        if actions is not None:
            if sub_action_index == -1:
                action_clone = action.clone(CLONE_POSTFIX)
                self.touch_project()
                actions.insert(action_index + 1, action_clone)
            else:
                sub_action = sub_actions[sub_action_index]
                sub_action_clone = sub_action.clone(CLONE_POSTFIX)
                self.touch_project()
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
            self._refresh_ui(job_row, new_row)

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
                self.touch_project()
                current_job = self.project.jobs.pop(current_index)
                self.action_list.clear()
                self._refresh_ui()
                return current_job
        return None

    def delete_action(self, confirm=True):
        job_row, action_row, actions, sub_actions, action_index, sub_action_index = self._get_current_action()
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
                    self.touch_project()
                    action.pop_sub_action(sub_action_index)
                    new_row = action_row if sub_action_index < len(sub_actions) else action_row - 1
                else:
                    self.touch_project()
                    self.project.jobs[job_row].pop_sub_action(action_index)
                    if action_index == 0:
                        new_row = 0 if len(actions) > 0 else -1
                    elif action_index < len(actions):
                        new_row = action_row
                    elif action_index == len(actions):
                        new_row = action_row - len(actions[action_index - 1].sub_actions) - 1
                self._refresh_ui(job_row, new_row)
            return current_action
        return None

    def delete_element(self, confirm=True):
        if self.job_list.hasFocus():
            element = self.delete_job(confirm)
        elif self.action_list.hasFocus():
            element = self.delete_action(confirm)
        return element

    def add_job(self):
        job_action = ActionConfig("Job")
        dialog = ActionConfigDialog(job_action, self)
        if dialog.exec() == QDialog.Accepted:
            self.touch_project()
            self.project.jobs.append(job_action)
            self.job_list.addItem(self.list_item(self.job_text(job_action), job_action.enabled()))
            self.job_list.setCurrentRow(self.job_list.count() - 1)
            self.job_list.item(self.job_list.count() - 1).setSelected(True)
    
    def add_action(self, type_name=''):
        current_index = self.job_list.currentRow()
        if current_index < 0:
            QMessageBox.warning(self, "No Job Selected", "Please select a job first.")
            return
        if type_name == '':
            type_name = self.action_selector.currentText()
        action = ActionConfig(type_name)
        action.parent = self.get_current_job()
        dialog = ActionConfigDialog(action, self)
        if dialog.exec() == QDialog.Accepted:
            self.touch_project()
            self.project.jobs[current_index].add_sub_action(action)
            self.action_list.addItem(self.list_item(self.action_text(action), action.enabled()))

    def add_action_CombinedActions(self):
        self.add_action(ACTION_COMBO)

    def add_action_NoiseDetection(self):
        self.add_action(ACTION_NOISEDETECTION)

    def add_action_FocusStack(self):
        self.add_action(ACTION_FOCUSSTACK)

    def add_action_FocusStackBunch(self):
        self.add_action(ACTION_FOCUSSTACKBUNCH)

    def add_action_MultiLayer(self):
        self.add_action(ACTION_MULTILAYER)
    
    def add_sub_action(self, type_name=''):
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
        if not action or action.type_name != ACTION_COMBO:
            return
        if type_name == '':
            type_name = self.sub_action_selector.currentText()
        sub_action = ActionConfig(type_name)
        dialog = ActionConfigDialog(sub_action, self)
        if dialog.exec() == QDialog.Accepted:
            self.touch_project()
            action.add_sub_action(sub_action)
            self.on_job_selected(current_job_index)
            self.action_list.setCurrentRow(current_action_index)

    def add_sub_action_MakeNoise(self):
        self.add_sub_action(ACTION_MASKNOISE)

    def add_sub_action_Vignetting(self):
        self.add_sub_action(ACTION_VIGNETTING)

    def add_sub_action_AlignFrames(self):
        self.add_sub_action(ACTION_ALIGNFRAMES)

    def add_sub_action_BalanceFrames(self):
        self.add_sub_action(ACTION_BALANCEFRAMES)
    
    def copy_job(self):
        current_index = self.job_list.currentRow()
        if 0 <= current_index < len(self.project.jobs):
            self._copy_buffer = self.project.jobs[current_index].clone()

    def copy_action(self):
        job_row, action_row, actions, sub_actions, action_index, sub_action_index = self._get_current_action()
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
        if self._copy_buffer.type_name != ACTION_JOB:
            return
        job_index = self.job_list.currentRow()
        if 0 <= job_index < len(self.project.jobs):
            new_job_index = job_index
            self.touch_project()
            self.project.jobs.insert(new_job_index, self._copy_buffer)
            self.job_list.setCurrentRow(new_job_index)
            self.action_list.setCurrentRow(new_job_index)
            self._refresh_ui(new_job_index, -1)

    def paste_action(self):
        job_row, action_row, actions, sub_actions, action_index, sub_action_index = self._get_current_action()
        action = actions[action_index]
        if actions is not None:
            if sub_action_index == -1:
                if self._copy_buffer.type_name not in ACTION_TYPES:
                    return
                self.touch_project()
                actions.insert(action_index, self._copy_buffer)
            else:
                if action.type_name != ACTION_COMBO or self._copy_buffer.type_name not in SUB_ACTION_TYPES:
                    return
                self.touch_project()
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
            self._refresh_ui(job_row, new_row)

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
            self._refresh_ui()
            len_jobs = len(self.project.jobs)
            if len_jobs > 0:
                if job_row >= len_jobs:
                    job_row = len_jobs - 1
                self.job_list.setCurrentRow(job_row)
                actions = self.project.jobs[job_row].sub_actions
                len_actions = len(actions)
                if len_actions > 0:
                    if action_row  >= len_actions:
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
            job_row, action_row, actions, sub_actions, action_index, sub_action_index = self._get_current_action()
            if actions is not None:
                action = actions[action_index]
                current_action = action if sub_action_index == -1 else sub_actions[sub_action_index]
        if current_action:
            if current_action.enabled() != enabled:
                self.touch_project()
                current_action.set_enabled(enabled)
                self._refresh_ui(job_row, action_row)

    def enable(self):
        self.set_enabled(True)

    def disable(self):
        self.set_enabled(False)

    def set_enabled_all(self, enable=True):
        self.touch_project()
        job_row = self.job_list.currentRow()
        action_row = self.action_list.currentRow()
        for j in self.project.jobs:
            j.set_enabled_all(enable)
        self._refresh_ui(job_row, action_row)

    def enable_all(self):
        self.set_enabled_all(True)

    def disable_all(self):
        self.set_enabled_all(False)
