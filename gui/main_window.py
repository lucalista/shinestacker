from PySide6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QHBoxLayout, QTabWidget,
                               QLabel, QDialog, QSplitter)
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from gui.project_model import Project
from gui.action_config import ActionConfigDialog
from gui.project_model import ACTION_COMBO
from gui.menu import WindowMenu
from gui.gui_logging import LogManager
from gui.gui_run import RunWindow


class MainWindow(WindowMenu, LogManager):

    def __init__(self):
        WindowMenu.__init__(self)
        LogManager.__init__(self)
        self._windows = []
        self._workers = []
        self.setWindowTitle("Focus Stacking GUI")
        self.resize(1200, 800)
        center = QGuiApplication.primaryScreen().geometry().center()
        self.move(center - self.rect().center())
        self.project = Project()
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
        self.tab_widget = QTabWidget()
        self.tab_widget.resize(1000, 500)
        h_splitter.addWidget(self.tab_widget)
        self.job_list = QListWidget()
        self.job_list.currentRowChanged.connect(self.on_job_selected)
        self.job_list.itemDoubleClicked.connect(self.on_job_double_clicked)
        self.action_list = QListWidget()
        self.action_list.itemDoubleClicked.connect(self.on_action_double_clicked)
        vbox_left = QVBoxLayout()
        vbox_left.setSpacing(4)
        vbox_left.addWidget(QLabel("Jobs"))
        vbox_left.addWidget(self.job_list)
        vbox_right = QVBoxLayout()
        vbox_right.setSpacing(4)
        vbox_right.addWidget(QLabel("Actions"))
        vbox_right.addWidget(self.action_list)
        self.job_list.itemSelectionChanged.connect(self.update_delete_buttons_state)
        self.action_list.itemSelectionChanged.connect(self.update_delete_buttons_state)
        h_layout.addLayout(vbox_left)
        h_layout.addLayout(vbox_right)
        layout.addWidget(h_splitter)
        self.central_widget.setLayout(layout)

    def on_job_double_clicked(self, item):
        index = self.job_list.row(item)
        if 0 <= index < len(self.project.jobs):
            job = self.project.jobs[index]
            dialog = ActionConfigDialog(job, self)
            if dialog.exec() == QDialog.Accepted:
                current_row = self.job_list.currentRow()
                if current_row >= 0:
                    self.job_list.item(current_row).setText(job.params['name'])

    def before_thread_begins(self):
        self.run_job_action.setEnabled(False)
        self.run_all_jobs_action.setEnabled(False)

    def get_tab_and_position(self, id_str):
        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            if w.id_str() == id_str:
                return i, w

    def get_tab_at_position(self, id_str):
        i, w = self.get_tab_and_position(id_str)
        return w

    def get_tab_position(self, id_str):
        i, w = self.get_tab_and_position(id_str)
        return i

    def do_handle_end_message(self, status, id_str, message):
        self.run_job_action.setEnabled(True)
        self.run_all_jobs_action.setEnabled(True)
        self.get_tab_at_position(id_str).close_button.setEnabled(True)
        self.get_tab_at_position(id_str).stop_button.setEnabled(False)

    def create_new_window(self, title, labels=[]):
        new_window = RunWindow(labels, self)
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

    def connect_signals(self, worker, window):
        worker.before_action_signal.connect(window.handle_before_action)
        worker.after_action_signal.connect(window.handle_after_action)
        worker.step_counts_signal.connect(window.handle_step_counts)
        worker.begin_steps_signal.connect(window.handle_begin_steps)
        worker.end_steps_signal.connect(window.handle_end_steps)
        worker.after_step_signal.connect(window.handle_after_step)
        worker.save_plot_signal.connect(window.handle_save_plot)

    def show_action_config_dialog(self, action):
        dialog = ActionConfigDialog(action, self)
        if dialog.exec():
            current_job_index = self.job_list.currentRow()
            self.on_job_selected(current_job_index)

    def set_enabled_sub_actions_gui(self, enabled):
        self.add_sub_action_entry_action.setEnabled(enabled)
        self.sub_action_selector.setEnabled(enabled)
        for a in self.sub_action_menu_entries:
            a.setEnabled(enabled)

    def update_delete_buttons_state(self):
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
                not is_sub_action and current_action.type_name == ACTION_COMBO
            self.set_enabled_sub_actions_gui(enable_sub_actions)
        else:
            self.set_enabled_sub_actions_gui(False)

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

    def on_action_double_clicked(self, item):
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
                if is_sub_action:
                    self.show_action_config_dialog(current_action)
                else:
                    self.set_enabled_sub_actions_gui(current_action.type_name == ACTION_COMBO)
                    self.show_action_config_dialog(current_action)
