from PySide6.QtWidgets import QMessageBox, QFileDialog, QListWidgetItem, QMenu, QToolBar, QComboBox, QDialog
from PySide6.QtGui import QAction, QColor, QIcon
from PySide6.QtCore import Qt
from gui.project_model import Project
from config.constants import constants
from gui.gui_run import ColorPalette
from gui.action_config import ActionConfigDialog
from gui.gui_actions import GuiActions
import os.path
import os
import json
import jsonpickle
import webbrowser
import platform
import subprocess


DONT_USE_NATIVE_MENU = True
ENABLED_LIST_ITEM_COLOR = ColorPalette.DARK_BLUE.tuple()
DISABLED_LIST_ITEM_COLOR = ColorPalette.DARK_RED.tuple()


def running_under_windows() -> bool:
    return os.name in ['nt', 'ce']


def running_under_macos() -> bool:
    return "darwin" in platform.system().casefold()


class WindowMenu(GuiActions):
    def __init__(self):
        super().__init__()
        self.script_dir = os.path.dirname(__file__)
        self._current_file = None
        self._workers = []
        menubar = self.menuBar()
        self.add_file_menu(menubar)
        self.add_edit_menu(menubar)
        self.add_job_menu(menubar)
        self.add_actions_menu(menubar)
        self.add_help_menu(menubar)
        toolbar = QToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        self.fill_toolbar(toolbar)

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
        self.delete_element_action = QAction("Delete", self)
        self.delete_element_action.setShortcut("Del")  # Qt.Key_Backspace
        self.delete_element_action.setIcon(self.get_icon("close-round-line-icon"))
        self.delete_element_action.setToolTip("delete")
        self.delete_element_action.triggered.connect(self.delete_element)
        self.delete_element_action.setEnabled(False)
        menu.addAction(self.delete_element_action)
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
        self.enable_action = QAction("E&nable", self)
        self.enable_action.setShortcut("Ctrl+E")
        self.enable_action.triggered.connect(self.enable)
        menu.addAction(self.enable_action)
        self.disable_action = QAction("Di&sable", self)
        self.disable_action.setShortcut("Ctrl+B")
        self.disable_action.triggered.connect(self.disable)
        menu.addAction(self.disable_action)
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
        self.add_job_action = QAction("Add Job", self)
        self.add_job_action.setShortcut("Ctrl+P")
        self.add_job_action.setIcon(self.get_icon("plus-round-line-icon"))
        self.add_job_action.setToolTip("Add job")
        self.add_job_action.triggered.connect(self.add_job)
        menu.addAction(self.add_job_action)
        menu.addSeparator()
        self.run_job_action = QAction("Run Job", self)
        self.run_job_action.setShortcut("Ctrl+J")
        self.run_job_action.setIcon(self.get_icon("play-button-round-icon"))
        self.run_job_action.setToolTip("Run job")
        self.run_job_action.setEnabled(False)
        self.run_job_action.triggered.connect(self.run_job)
        menu.addAction(self.run_job_action)
        self.run_all_jobs_action = QAction("Run All Jobs", self)
        self.run_all_jobs_action.setShortcut("Ctrl+Shift+J")
        self.run_all_jobs_action.setIcon(self.get_icon("forward-button-icon"))
        self.run_all_jobs_action.setToolTip("Run all jobs")
        self.run_all_jobs_action.setEnabled(False)
        self.run_all_jobs_action.triggered.connect(self.run_all_jobs)
        menu.addAction(self.run_all_jobs_action)

    def add_actions_menu(self, menubar):
        menu = menubar.addMenu("&Actions")
        add_action_menu = QMenu("Add Action", self)
        for action in constants.ACTION_TYPES:
            entry_action = QAction(action, self)
            entry_action.triggered.connect({
                constants.ACTION_COMBO: self.add_action_CombinedActions,
                constants.ACTION_NOISEDETECTION: self.add_action_NoiseDetection,
                constants.ACTION_FOCUSSTACK: self.add_action_FocusStack,
                constants.ACTION_FOCUSSTACKBUNCH: self.add_action_FocusStackBunch,
                constants.ACTION_MULTILAYER: self.add_action_MultiLayer
            }[action])
            add_action_menu.addAction(entry_action)
        menu.addMenu(add_action_menu)
        add_sub_action_menu = QMenu("Add Sub Action", self)
        self.sub_action_menu_entries = []
        for action in constants.SUB_ACTION_TYPES:
            entry_action = QAction(action, self)
            entry_action.triggered.connect({
                constants.ACTION_MASKNOISE: self.add_sub_action_MakeNoise,
                constants.ACTION_VIGNETTING: self.add_sub_action_Vignetting,
                constants.ACTION_ALIGNFRAMES: self.add_sub_action_AlignFrames,
                constants.ACTION_BALANCEFRAMES: self.add_sub_action_BalanceFrames
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

    def fill_toolbar(self, toolbar):
        toolbar.addAction(self.add_job_action)
        toolbar.addSeparator()
        self.action_selector = QComboBox()
        self.action_selector.addItems(constants.ACTION_TYPES)
        self.action_selector.setEnabled(False)
        toolbar.addWidget(self.action_selector)
        self.add_action_entry_action = QAction("Add Action", self)
        self.add_action_entry_action.setIcon(QIcon(os.path.join(self.script_dir, "img/plus-round-line-icon.png")))
        self.add_action_entry_action.setToolTip("Add action")
        self.add_action_entry_action.triggered.connect(self.add_action)
        self.add_action_entry_action.setEnabled(False)
        toolbar.addAction(self.add_action_entry_action)
        self.sub_action_selector = QComboBox()
        self.sub_action_selector.addItems(constants.SUB_ACTION_TYPES)
        self.sub_action_selector.setEnabled(False)
        toolbar.addWidget(self.sub_action_selector)
        self.add_sub_action_entry_action = QAction("Add Sub Action", self)
        self.add_sub_action_entry_action.setIcon(QIcon(os.path.join(self.script_dir, "img/plus-round-line-icon.png")))
        self.add_sub_action_entry_action.setToolTip("Add sub action")
        self.add_sub_action_entry_action.triggered.connect(self.add_sub_action)
        self.add_sub_action_entry_action.setEnabled(False)
        toolbar.addAction(self.add_sub_action_entry_action)
        toolbar.addSeparator()
        toolbar.addAction(self.delete_element_action)
        toolbar.addSeparator()
        toolbar.addAction(self.run_job_action)
        toolbar.addAction(self.run_all_jobs_action)

    def website(self):
        webbrowser.open("https://github.com/lucalista/focusstack/blob/main/docs/main.md")

    def refresh_ui(self, job_row=-1, action_row=-1):
        self.job_list.clear()
        for job in self.project.jobs:
            self.job_list.addItem(self.list_item(self.job_text(job), job.enabled()))
        if self.project.jobs:
            self.job_list.setCurrentRow(0)
        if job_row >= 0:
            self.job_list.setCurrentRow(job_row)
        if action_row >= 0:
            self.action_list.setCurrentRow(action_row)
        if self.job_list.count() == 0:
            self.add_action_entry_action.setEnabled(False)
            self.action_selector.setEnabled(False)
            self.run_job_action.setEnabled(False)
            self.run_all_jobs_action.setEnabled(False)
        else:
            self.add_action_entry_action.setEnabled(True)
            self.action_selector.setEnabled(True)
            self.delete_element_action.setEnabled(True)
            self.run_job_action.setEnabled(True)
            self.run_all_jobs_action.setEnabled(True)

    def update_title(self):
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
            self.update_title()
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
                self.update_title()
                self.refresh_ui(0, -1)
                if self.job_list.count() > 0:
                    self.job_list.setCurrentRow(0)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot open file {file_path}:\n{str(e)}")
        if len(self.project.jobs) > 0:
            self.job_list.setCurrentRow(0)
            self.activateWindow()
        self._modified_project = False

    def current_file_name(self):
        return os.path.basename(self._current_file) if self._current_file else ''

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

    def stop_worker(self, tab_position):
        worker = self._workers[tab_position]
        worker.stop()

    def contextMenuEvent(self, event):
        item = self.job_list.itemAt(self.job_list.viewport().mapFrom(self, event.pos()))
        current_action = None
        if item:
            index = self.job_list.row(item)
            current_action = self.get_job_at(index)
            self.job_list.setCurrentRow(index)
        item = self.action_list.itemAt(self.action_list.viewport().mapFrom(self, event.pos()))
        if item:
            index = self.action_list.row(item)
            self.action_list.setCurrentRow(index)
            job_row, action_row, actions, sub_actions, action_index, sub_action_index = self.get_action_at(index)
            if actions is not None:
                action = actions[action_index]
                current_action = action if sub_action_index == -1 else sub_actions[sub_action_index]
        if current_action:
            menu = QMenu(self)
            if current_action.enabled():
                menu.addAction(self.disable_action)
            else:
                menu.addAction(self.enable_action)
            edit_config_action = QAction("Edit configuration")
            edit_config_action.triggered.connect(self.edit_current_action)
            menu.addAction(edit_config_action)
            menu.addSeparator()
            self.current_action_working_path, name = self.get_action_working_path(current_action)
            if self.current_action_working_path != '' and os.path.exists(self.current_action_working_path):
                action_name = "Browse Working Path" + (f" > {name}" if name != '' else '')
                self.browse_working_path_action = QAction(action_name)
                self.browse_working_path_action.triggered.connect(self.browse_working_path_path)
                menu.addAction(self.browse_working_path_action)
            ip, name = self.get_action_input_path(current_action)
            if ip != '':
                ips = ip.split(constants.PATH_SEPARATOR)
                self.current_action_input_path = constants.PATH_SEPARATOR.join([f"{self.current_action_working_path}/{ip}" for ip in ips])
                p_exists = False
                for p in self.current_action_input_path.split(constants.PATH_SEPARATOR):
                    if os.path.exists(p):
                        p_exists = True
                        break
                if p_exists:
                    action_name = "Browse Input Path" + (f" > {name}" if name != '' else '')
                    self.browse_input_path_action = QAction(action_name)
                    self.browse_input_path_action.triggered.connect(self.browse_input_path_path)
                    menu.addAction(self.browse_input_path_action)
            op, name = self.get_action_output_path(current_action)
            if op != '':
                self.current_action_output_path = f"{self.current_action_working_path}/{op}"
                if os.path.exists(self.current_action_output_path):
                    action_name = "Browse Output Path" + (f" > {name}" if name != '' else '')
                    self.browse_output_path_action = QAction(action_name)
                    self.browse_output_path_action.triggered.connect(self.browse_output_path_path)
                    menu.addAction(self.browse_output_path_action)
            menu.addSeparator()
            menu.addAction(self.run_job_action)
            menu.addAction(self.run_all_jobs_action)
            menu.exec(event.globalPos())

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
                self.show_action_config_dialog(current_action)
