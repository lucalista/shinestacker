from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QSplitter
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from focusstack.gui.project_model import Project
from focusstack.gui.actions_window import ActionsWindow
from focusstack.gui.gui_logging import LogManager
from focusstack.gui.gui_run import RunWindow


class MainWindow(ActionsWindow, LogManager):
    def __init__(self):
        ActionsWindow.__init__(self)
        LogManager.__init__(self)
        self._windows = []
        self._workers = []
        self.update_title()
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
        self.job_list.currentRowChanged.connect(self.on_job_selected)
        self.job_list.itemDoubleClicked.connect(self.on_job_edit)
        self.action_list.itemDoubleClicked.connect(self.on_action_edit)
        vbox_left = QVBoxLayout()
        vbox_left.setSpacing(4)
        vbox_left.addWidget(QLabel("Jobs"))
        vbox_left.addWidget(self.job_list)
        vbox_right = QVBoxLayout()
        vbox_right.setSpacing(4)
        vbox_right.addWidget(QLabel("Actions"))
        vbox_right.addWidget(self.action_list)
        self.job_list.itemSelectionChanged.connect(self.update_delete_action_state)
        self.action_list.itemSelectionChanged.connect(self.update_delete_action_state)
        h_layout.addLayout(vbox_left)
        h_layout.addLayout(vbox_right)
        layout.addWidget(h_splitter)
        self.central_widget.setLayout(layout)

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
        new_window = RunWindow(labels,
                               lambda id_str: self.stop_worker(self.get_tab_position(id_str)),
                               lambda id_str: self.close_window(self.get_tab_position(id_str)),
                               self)
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
        worker.open_app_signal.connect(window.handle_open_app)

    def set_enabled_sub_actions_gui(self, enabled):
        self.add_sub_action_entry_action.setEnabled(enabled)
        self.sub_action_selector.setEnabled(enabled)
        for a in self.sub_action_menu_entries:
            a.setEnabled(enabled)
