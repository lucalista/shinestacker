# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0915, R0904, R0914, R0912, E1101, W0201, E1121
import os
import subprocess
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QMessageBox,
                               QSplitter, QToolBar, QMenu, QComboBox, QStackedWidget)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QAction, QIcon, QPixmap
from .. config.constants import constants
from .. core.core_utils import running_under_windows, running_under_macos, get_app_base_path
from .colors import ColorPalette
from .project_model import Project
from .actions_window import ActionsWindow
from .gui_logging import LogManager
from .gui_run import RunWindow, RunWorker
from .project_converter import ProjectConverter
from .project_model import get_action_working_path, get_action_input_path, get_action_output_path
from .menu_manager import MenuManager


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


class TabWidgetWithPlaceholder(QWidget):
    currentChanged = Signal(int)
    tabCloseRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.stacked_widget = QStackedWidget()
        self.layout.addWidget(self.stacked_widget)
        self.tab_widget = QTabWidget()
        self.stacked_widget.addWidget(self.tab_widget)
        self.placeholder = QLabel()
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rel_path = 'ico/focus_stack_bkg.png'
        icon_path = f'{get_app_base_path()}/{rel_path}'
        if not os.path.exists(icon_path):
            icon_path = f'{get_app_base_path()}/../{rel_path}'
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            pixmap = pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            self.placeholder.setPixmap(pixmap)
        else:
            self.placeholder.setText("Run logs will appear here.")
        self.stacked_widget.addWidget(self.placeholder)
        self.tab_widget.currentChanged.connect(self._on_current_changed)
        self.tab_widget.tabCloseRequested.connect(self._on_tab_close_requested)
        self.update_placeholder_visibility()

    def _on_current_changed(self, index):
        self.currentChanged.emit(index)
        self.update_placeholder_visibility()

    def _on_tab_close_requested(self, index):
        self.tabCloseRequested.emit(index)
        self.update_placeholder_visibility()

    def update_placeholder_visibility(self):
        if self.tab_widget.count() == 0:
            self.stacked_widget.setCurrentIndex(1)
        else:
            self.stacked_widget.setCurrentIndex(0)

    # pylint: disable=C0103
    def addTab(self, widget, label):
        result = self.tab_widget.addTab(widget, label)
        self.update_placeholder_visibility()
        return result

    def removeTab(self, index):
        result = self.tab_widget.removeTab(index)
        self.update_placeholder_visibility()
        return result

    def count(self):
        return self.tab_widget.count()

    def setCurrentIndex(self, index):
        return self.tab_widget.setCurrentIndex(index)

    def currentIndex(self):
        return self.tab_widget.currentIndex()

    def currentWidget(self):
        return self.tab_widget.currentWidget()

    def widget(self, index):
        return self.tab_widget.widget(index)

    def indexOf(self, widget):
        return self.tab_widget.indexOf(widget)
    # pylint: enable=C0103


LIST_STYLE_SHEET = f"""
    QListWidget::item:selected {{
        background-color: #{ColorPalette.LIGHT_BLUE.hex()};;
    }}
"""


class MainWindow(ActionsWindow, LogManager):
    def __init__(self):
        ActionsWindow.__init__(self)
        LogManager.__init__(self)
        actions = {
            "&New...": self.new_project,
            "&Open...": self.open_project,
            "&Close": self.close_project,
            "&Save": self.save_project,
            "Save &As...": self.save_project_as,
            "&Undo": self.project_editor.undo,
            "&Cut": self.project_editor.cut_element,
            "Cop&y": self.project_editor.copy_element,
            "&Paste": self.project_editor.paste_element,
            "Duplicate": self.project_editor.clone_element,
            "Delete": self.delete_element,
            "Move &Up": self.project_editor.move_element_up,
            "Move &Down": self.project_editor.move_element_down,
            "E&nable": self.project_editor.enable,
            "Di&sable": self.project_editor.disable,
            "Enable All": self.project_editor.enable_all,
            "Disable All": self.project_editor.disable_all,
            "Expert Options": self.toggle_expert_options,
            "Add Job": self.project_editor.add_job,
            "Run Job": self.run_job,
            "Run All Jobs": self.run_all_jobs,
        }
        self.menu_manager = MenuManager(self.menuBar(), actions, self.project_editor, self)
        self.script_dir = os.path.dirname(__file__)
        self._windows = []
        self._workers = []
        self.retouch_callback = None
        self.expert_options = False
        self.job_list().setStyleSheet(LIST_STYLE_SHEET)
        self.action_list().setStyleSheet(LIST_STYLE_SHEET)
        self.menu_manager.add_menus()
        toolbar = QToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        self.fill_toolbar(toolbar)
        self.resize(1200, 800)
        self.move(QGuiApplication.primaryScreen().geometry().center() -
                  self.rect().center())
        self.set_project(Project())
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        h_splitter = QSplitter(Qt.Orientation.Vertical)
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(10, 0, 10, 10)
        top_widget = QWidget()
        top_widget.setLayout(h_layout)
        h_splitter.addWidget(top_widget)
        self.tab_widget = TabWidgetWithPlaceholder()
        self.tab_widget.resize(1000, 500)
        h_splitter.addWidget(self.tab_widget)
        self.job_list().currentRowChanged.connect(self.project_editor.on_job_selected)
        self.job_list().itemDoubleClicked.connect(self.on_job_edit)
        self.action_list().itemDoubleClicked.connect(self.on_action_edit)
        vbox_left = QVBoxLayout()
        vbox_left.setSpacing(4)
        vbox_left.addWidget(QLabel("Job"))
        vbox_left.addWidget(self.job_list())
        vbox_right = QVBoxLayout()
        vbox_right.setSpacing(4)
        vbox_right.addWidget(QLabel("Action"))
        vbox_right.addWidget(self.action_list())
        self.job_list().itemSelectionChanged.connect(self.update_delete_action_state)
        self.action_list().itemSelectionChanged.connect(self.update_delete_action_state)
        h_layout.addLayout(vbox_left)
        h_layout.addLayout(vbox_right)
        layout.addWidget(h_splitter)
        self.central_widget.setLayout(layout)

        def handle_modified(modified):
            self.save_actions_set_enabled(modified)
            self.update_title()

        self.project_editor.modified_signal.connect(handle_modified)
        self.project_editor.select_signal.connect(self.update_delete_action_state)
        self.project_editor.refresh_ui_signal.connect(self.refresh_ui)
        self.project_editor.enable_delete_action_signal.connect(
            self.menu_manager.delete_element_action.setEnabled)

    def set_retouch_callback(self, callback):
        self.retouch_callback = callback

    def save_actions_set_enabled(self, enabled):
        self.menu_manager.save_actions_set_enabled(enabled)

    def fill_toolbar(self, toolbar):
        toolbar.addAction(self.menu_manager.add_job_action)
        toolbar.addSeparator()
        self.action_selector = QComboBox()
        self.action_selector.addItems(constants.ACTION_TYPES)
        self.action_selector.setEnabled(False)
        toolbar.addWidget(self.action_selector)
        self.add_action_entry_action = QAction("Add Action", self)
        self.add_action_entry_action.setIcon(
            QIcon(os.path.join(self.script_dir, "img/plus-round-line-icon.png")))
        self.add_action_entry_action.setToolTip("Add action")
        self.add_action_entry_action.triggered.connect(self.menu_manager.add_action)
        self.add_action_entry_action.setEnabled(False)
        toolbar.addAction(self.add_action_entry_action)
        self.sub_action_selector = QComboBox()
        self.sub_action_selector.addItems(constants.SUB_ACTION_TYPES)
        self.sub_action_selector.setEnabled(False)
        toolbar.addWidget(self.sub_action_selector)
        self.add_sub_action_entry_action = QAction("Add Sub Action", self)
        self.add_sub_action_entry_action.setIcon(
            QIcon(os.path.join(self.script_dir, "img/plus-round-line-icon.png")))
        self.add_sub_action_entry_action.setToolTip("Add sub action")
        self.add_sub_action_entry_action.triggered.connect(self.menu_manager.add_sub_action)
        self.add_sub_action_entry_action.setEnabled(False)
        self.menu_manager.set_selectors(
            self.action_selector, self.sub_action_selector)
        toolbar.addAction(self.add_sub_action_entry_action)
        toolbar.addSeparator()
        toolbar.addAction(self.menu_manager.delete_element_action)
        toolbar.addSeparator()
        toolbar.addAction(self.menu_manager.run_job_action)
        toolbar.addAction(self.menu_manager.run_all_jobs_action)

    # pylint: disable=C0103
    def contextMenuEvent(self, event):
        item = self.job_list().itemAt(self.job_list().viewport().mapFrom(self, event.pos()))
        current_action = None
        if item:
            index = self.job_list().row(item)
            current_action = self.get_job_at(index)
            self.set_current_job(index)
        item = self.action_list().itemAt(self.action_list().viewport().mapFrom(self, event.pos()))
        if item:
            index = self.action_list().row(item)
            self.set_current_action(index)
            _job_row, _action_row, pos = self.get_action_at(index)
            current_action = pos.action if not pos.is_sub_action else pos.sub_action
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
            self.current_action_working_path, name = get_action_working_path(current_action)
            if self.current_action_working_path != '' and \
                    os.path.exists(self.current_action_working_path):
                action_name = "Browse Working Path" + (f" > {name}" if name != '' else '')
                self.browse_working_path_action = QAction(action_name)
                self.browse_working_path_action.triggered.connect(self.browse_working_path)
                menu.addAction(self.browse_working_path_action)
            ip, name = get_action_input_path(current_action)
            if ip != '':
                ips = ip.split(constants.PATH_SEPARATOR)
                self.current_action_input_path = constants.PATH_SEPARATOR.join(
                    [f"{self.current_action_working_path}/{ip}" for ip in ips])
                p_exists = False
                for p in self.current_action_input_path.split(constants.PATH_SEPARATOR):
                    if os.path.exists(p):
                        p_exists = True
                        break
                if p_exists:
                    action_name = "Browse Input Path" + (f" > {name}" if name != '' else '')
                    n_files = [f"{len(next(os.walk(p))[2])}"
                               for p in
                               self.current_action_input_path.split(constants.PATH_SEPARATOR)]
                    s = "" if len(n_files) == 1 and n_files[0] == 1 else "s"
                    action_name += " (" + ", ".join(n_files) + f" file{s})"
                    self.browse_input_path_action = QAction(action_name)
                    self.browse_input_path_action.triggered.connect(self.browse_input_path)
                    menu.addAction(self.browse_input_path_action)
            op, name = get_action_output_path(current_action)
            if op != '':
                self.current_action_output_path = f"{self.current_action_working_path}/{op}"
                if os.path.exists(self.current_action_output_path):
                    action_name = "Browse Output Path" + (f" > {name}" if name != '' else '')
                    n_files = len(next(os.walk(op))[2])
                    s = "" if n_files == 1 else "s"
                    action_name += f" ({n_files} file{s})"
                    self.browse_output_path_action = QAction(action_name)
                    self.browse_output_path_action.triggered.connect(self.browse_output_path)
                    menu.addAction(self.browse_output_path_action)
            menu.addSeparator()
            menu.addAction(self.run_job_action)
            menu.addAction(self.run_all_jobs_action)
            if current_action.type_name == constants.ACTION_JOB:
                retouch_path = self.get_retouch_path(current_action)
                if len(retouch_path) > 0:
                    menu.addSeparator()
                    self.job_retouch_path_action = QAction("Retouch path")
                    self.job_retouch_path_action.triggered.connect(
                        lambda job: self.run_retouch_path(current_action, retouch_path))
                    menu.addAction(self.job_retouch_path_action)
            menu.exec(event.globalPos())
    # pylint: enable=C0103

    def get_icon(self, icon):
        return QIcon(os.path.join(self.script_dir, f"img/{icon}.png"))

    def get_retouch_path(self, job):
        frames_path = [get_action_output_path(action)[0]
                       for action in job.sub_actions
                       if action.type_name == constants.ACTION_COMBO]
        bunches_path = [get_action_output_path(action)[0]
                        for action in job.sub_actions
                        if action.type_name == constants.ACTION_FOCUSSTACKBUNCH]
        stack_path = [get_action_output_path(action)[0]
                      for action in job.sub_actions
                      if action.type_name == constants.ACTION_FOCUSSTACK]
        if len(bunches_path) > 0:
            stack_path += [bunches_path[0]]
        elif len(frames_path) > 0:
            stack_path += [frames_path[0]]
        wp = get_action_working_path(job)[0]
        if wp == '':
            raise ValueError("Job has no working path specified.")
        stack_path = [f"{wp}/{s}" for s in stack_path]
        return stack_path

    def run_retouch_path(self, _job, retouch_path):
        self.retouch_callback(retouch_path)

    def browse_path(self, path):
        ps = path.split(constants.PATH_SEPARATOR)
        for p in ps:
            if os.path.exists(p):
                if running_under_windows():
                    os.startfile(os.path.normpath(p))
                else:
                    cmd = 'open' if running_under_macos() else 'xdg-open'
                    subprocess.run([cmd, p], check=True)

    def browse_working_path(self):
        self.browse_path(self.current_action_working_path)

    def browse_input_path(self):
        self.browse_path(self.current_action_input_path)

    def browse_output_path(self):
        self.browse_path(self.current_action_output_path)

    def refresh_ui(self, job_row=-1, action_row=-1):
        self.clear_job_list()
        for job in self.project_jobs():
            self.project_editor.add_list_item(self.job_list(), job, False)
        if self.project_jobs():
            self.set_current_job(0)
        if job_row >= 0:
            self.set_current_job(job_row)
        if action_row >= 0:
            self.set_current_action(action_row)
        if self.job_list_count() == 0:
            self.add_action_entry_action.setEnabled(False)
            self.action_selector.setEnabled(False)
            self.run_job_action.setEnabled(False)
            self.run_all_jobs_action.setEnabled(False)
        else:
            self.add_action_entry_action.setEnabled(True)
            self.action_selector.setEnabled(True)
            self.menu_manager.delete_element_action.setEnabled(True)
            self.menu_manager.run_job_action.setEnabled(True)
            self.menu_manager.run_all_jobs_action.setEnabled(True)

    def quit(self):
        if self._check_unsaved_changes():
            for worker in self._workers:
                worker.stop()
            self.close()

    def toggle_expert_options(self):
        self.expert_options = self.menu_manager.expert_options_action.isChecked()

    def set_expert_options(self):
        self.expert_options_action.setChecked(True)
        self.expert_options = True

    def before_thread_begins(self):
        self.menu_manager.run_job_action.setEnabled(False)
        self.menu_manager.run_all_jobs_action.setEnabled(False)

    def get_tab_and_position(self, id_str):
        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            if w.id_str() == id_str:
                return i, w
        return None, None

    def get_tab_at_position(self, id_str):
        _i, w = self.get_tab_and_position(id_str)
        return w

    def get_tab_position(self, id_str):
        i, _w = self.get_tab_and_position(id_str)
        return i

    def do_handle_end_message(self, status, id_str, message):
        self.menu_manager.run_job_action.setEnabled(True)
        self.menu_manager.run_all_jobs_action.setEnabled(True)
        tab = self.get_tab_at_position(id_str)
        tab.close_button.setEnabled(True)
        tab.stop_button.setEnabled(False)
        if hasattr(tab, 'retouch_widget') and tab.retouch_widget is not None:
            tab.retouch_widget.setEnabled(True)

    def create_new_window(self, title, labels, retouch_paths):
        new_window = RunWindow(labels,
                               lambda id_str: self.stop_worker(self.get_tab_position(id_str)),
                               lambda id_str: self.close_window(self.get_tab_position(id_str)),
                               retouch_paths, self)
        self.tab_widget.addTab(new_window, title)
        self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
        if title is not None:
            new_window.setWindowTitle(title)
        new_window.show()
        self.add_gui_logger(new_window)
        self._windows.append(new_window)
        return new_window, self.last_id_str()

    def close_window(self, tab_position):
        self._windows.pop(tab_position)
        self._workers.pop(tab_position)
        self.tab_widget.removeTab(tab_position)

    def stop_worker(self, tab_position):
        worker = self._workers[tab_position]
        worker.stop()

    def connect_worker_signals(self, worker, window):
        worker.before_action_signal.connect(window.handle_before_action)
        worker.after_action_signal.connect(window.handle_after_action)
        worker.step_counts_signal.connect(window.handle_step_counts)
        worker.begin_steps_signal.connect(window.handle_begin_steps)
        worker.end_steps_signal.connect(window.handle_end_steps)
        worker.after_step_signal.connect(window.handle_after_step)
        worker.save_plot_signal.connect(window.handle_save_plot)
        worker.open_app_signal.connect(window.handle_open_app)

    def set_enabled_sub_actions_gui(self, enabled):
        self.add_sub_action_entry_action.setEnabled(enabled)
        self.sub_action_selector.setEnabled(enabled)
        for a in self.menu_manager.sub_action_menu_entries:
            a.setEnabled(enabled)

    def run_job(self):
        current_index = self.current_job_index()
        if current_index < 0:
            msg = "No Job Selected" if self.num_project_jobs() > 0 else "No Job Added"
            QMessageBox.warning(self, msg, "Please select a job first.")
            return
        if current_index >= 0:
            job = self.project_job(current_index)
            if job.enabled():
                job_name = job.params["name"]
                labels = [[(self.action_text(a), a.enabled()) for a in job.sub_actions]]
                r = self.get_retouch_path(job)
                retouch_paths = [] if len(r) == 0 else [(job_name, r)]
                new_window, id_str = self.create_new_window(f"{job_name} [⚙️ Job]",
                                                            labels, retouch_paths)
                worker = JobLogWorker(job, id_str)
                self.connect_worker_signals(worker, new_window)
                self.start_thread(worker)
                self._workers.append(worker)
            else:
                QMessageBox.warning(self, "Can't run Job",
                                    "Job " + job.params["name"] + " is disabled.")
                return

    def run_all_jobs(self):
        labels = [[(self.action_text(a), a.enabled() and
                    job.enabled()) for a in job.sub_actions] for job in self.project_jobs()]
        project_name = ".".join(self.current_file_name().split(".")[:-1])
        if project_name == '':
            project_name = '[new]'
        retouch_paths = []
        for job in self.project_jobs():
            r = self.get_retouch_path(job)
            if len(r) > 0:
                retouch_paths.append((job.params["name"], r))
        new_window, id_str = self.create_new_window(f"{project_name} [Project 📚]",
                                                    labels, retouch_paths)
        worker = ProjectLogWorker(self.project(), id_str)
        self.connect_worker_signals(worker, new_window)
        self.start_thread(worker)
        self._workers.append(worker)

    def delete_element(self):
        self.project_editor.delete_element()
        if self.job_list_count() > 0:
            self.delete_element_action.setEnabled(True)

    def update_delete_action_state(self):
        has_job_selected = self.num_selected_jobs() > 0
        has_action_selected = self.num_selected_actions() > 0
        self.menu_manager.delete_element_action.setEnabled(
            has_job_selected or has_action_selected)
        if has_action_selected and has_job_selected:
            job_index = min(self.current_job_index(), self.num_project_jobs() - 1)
            action_index = self.current_action_index()
            if job_index >= 0:
                job = self.project_job(job_index)
                current_action, is_sub_action = \
                    self.get_current_action_at(job, action_index)
                enable_sub_actions = current_action is not None and \
                    not is_sub_action and current_action.type_name == constants.ACTION_COMBO
                self.set_enabled_sub_actions_gui(enable_sub_actions)
        else:
            self.set_enabled_sub_actions_gui(False)
