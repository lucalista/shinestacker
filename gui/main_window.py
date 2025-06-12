from PySide6.QtWidgets import (QWidget, QPushButton, QVBoxLayout, QListWidget, QHBoxLayout,
                               QLabel, QComboBox, QMessageBox, QDialog)
from gui.project_model import Project, ActionConfig
from gui.project_converter import ProjectConverter
from gui.action_config import ActionConfigDialog
from gui.project_model import SUB_ACTION_TYPES, ACTION_TYPES, ACTION_COMBO
from gui.menu import WindowMenu
from gui.gui_logging import LogManager, LogWorker, QTextEditLogger
import matplotlib
matplotlib.use('agg')

TRAP_RUN_EXCEPTIONS = False


class JobLogWorker(LogWorker):
    def __init__(self, job, id_str):
        LogWorker.__init__(self)
        self.job = job
        self.id_str = id_str

    def _do_run_job(self):
        converter = ProjectConverter()
        converter.run_job(self.job, self.id_str)

    def run(self):
        job_error = False
        if TRAP_RUN_EXCEPTIONS:
            try:
                self._do_run_job()
            except Exception as e:
                job_error = True
                self.exception_signal.emit(f'Job {self.job.params["name"]} failed:\n{str(e)}')
        else:
            self._do_run_job()
        if job_error:
            self.html_signal.emit('''
            <hr><div style="margin: 2px 0; font-family: monospace;">
            <span style="color: #ff0000; font-weight: bold;">Job failed.</span>
            </div>
            ''')
        else:
            self.html_signal.emit('''
            <hr><div style="margin: 2px 0; font-family: monospace;">
            <span style="color: #000080; font-weight: bold;">Job completed.</span>
            </div>
            ''')
        self.end_signal.emit(1)


class ProjectLogWorker(LogWorker):
    def __init__(self, project, id_str):
        LogWorker.__init__(self)
        self.project = project
        self.id_str = id_str

    def _do_run_project(self):
        converter = ProjectConverter()
        converter.run_project(self.project, self.id_str)

    def run(self):
        job_error = False
        if TRAP_RUN_EXCEPTIONS:
            try:
                self._do_run_project()
            except Exception as e:
                job_error = True
                self.exception_signal.emit(f'Project failed:\n{str(e)}')
        else:
            self._do_run_project()
        if job_error:
            self.html_signal.emit('''
                <hr><div style="margin: 2px 0; font-family: monospace;">
                <span style="color: #ff0000; font-weight: bold;">Run failed.</span>
                </div>
                ''')
        else:
            self.html_signal.emit('''
                <hr><div style="margin: 2px 0; font-family: monospace;">
                <span style="color: #000080; font-weight: bold;">Run completed.</span>
                </div>
                ''')
        self.end_signal.emit(1)


class MainWindow(WindowMenu, LogManager):
    def __init__(self):
        WindowMenu.__init__(self)
        LogManager.__init__(self)
        self.setWindowTitle("Focus Stacking GUI")
        self.resize(800, 600)
        self.project = Project()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.job_list = QListWidget()
        self.job_list.currentRowChanged.connect(self.on_job_selected)
        self.job_list.itemDoubleClicked.connect(self.on_job_double_clicked)
        self.action_list = QListWidget()
        self.action_list.itemDoubleClicked.connect(self.on_action_double_clicked)
        self.add_job_button = QPushButton("Add Job")
        self.add_job_button.clicked.connect(self.add_job)
        self.run_job_button = QPushButton("Run Job")
        self.run_job_button.clicked.connect(self.run_job)
        self.run_all_jobs_button = QPushButton("Run All Jobs")
        self.run_all_jobs_button.clicked.connect(self.run_all_jobs)
        self.add_action_button = QPushButton("Add Action")
        self.add_action_button.clicked.connect(self.add_action)
        self.action_selector = QComboBox()
        self.action_selector.addItems(ACTION_TYPES)
        layout = QVBoxLayout()
        hlayout = QHBoxLayout()
        vbox_left = QVBoxLayout()
        vbox_left.addWidget(QLabel("Jobs"))
        vbox_left.addWidget(self.job_list)
        vbox_left.addWidget(self.add_job_button)
        hbox_run = QHBoxLayout()
        hbox_run.addWidget(self.run_job_button)
        hbox_run.addWidget(self.run_all_jobs_button)
        vbox_left.addLayout(hbox_run)
        vbox_right = QVBoxLayout()
        vbox_right.addWidget(QLabel("Actions"))
        vbox_right.addWidget(self.action_list)
        vbox_right.addWidget(QLabel("Select Action Type"))
        vbox_right.addWidget(self.action_selector)
        vbox_right.addWidget(self.add_action_button)
        self.delete_job_button = QPushButton("Delete Job")
        self.delete_job_button.setEnabled(False)
        self.delete_job_button.clicked.connect(self.delete_job)
        vbox_left.addWidget(self.delete_job_button)
        self.job_list.itemSelectionChanged.connect(self.update_delete_buttons_state)
        self.action_list.itemSelectionChanged.connect(self.update_delete_buttons_state)
        self.sub_action_selector = QComboBox()
        self.sub_action_selector.addItems(SUB_ACTION_TYPES)
        self.sub_action_selector.setEnabled(False)
        self.add_sub_action_button = QPushButton("Add Sub-Action")
        self.add_sub_action_button.clicked.connect(self.add_sub_action)
        self.add_sub_action_button.setEnabled(False)
        vbox_right.addWidget(QLabel("Select Sub-Action Type"))
        vbox_right.addWidget(self.sub_action_selector)
        vbox_right.addWidget(self.add_sub_action_button)
        self.delete_action_button = QPushButton("Delete Action")
        self.delete_action_button.setEnabled(False)
        self.delete_action_button.clicked.connect(self.delete_action)
        vbox_right.addWidget(self.delete_action_button)
        hlayout.addLayout(vbox_left)
        hlayout.addLayout(vbox_right)
        layout.addLayout(hlayout)
        self.central_widget.setLayout(layout)

    def add_job(self):
        job_action = ActionConfig("Job")
        dialog = ActionConfigDialog(job_action, self)
        if dialog.exec() == QDialog.Accepted:
            self.touch_project()
            self.project.jobs.append(job_action)
            self.job_list.addItem(job_action.params['name'])
            self.job_list.setCurrentRow(self.job_list.count() - 1)
            self.job_list.item(self.job_list.count() - 1).setSelected(True)

    def on_job_double_clicked(self, item):
        index = self.job_list.row(item)
        if 0 <= index < len(self.project.jobs):
            job = self.project.jobs[index]
            dialog = ActionConfigDialog(job, self)
            if dialog.exec() == QDialog.Accepted:
                current_row = self.job_list.currentRow()
                if current_row >= 0:
                    self.job_list.item(current_row).setText(job.params['name'])

    def get_current_job(self):
        current_index = self.job_list.currentRow()
        return None if current_index < 0 else self.project.jobs[current_index]

    def before_thread_begins(self):
        self.run_job_button.setEnabled(False)
        self.run_all_jobs_button.setEnabled(False)

    def _do_handle_end_message(self, int):
        self.run_job_button.setEnabled(True)
        self.run_all_jobs_button.setEnabled(True)

    def show_new_window(self, title=None):
        text_edit = QTextEditLogger()
        if title is not None:
            text_edit.setWindowTitle(title)
        text_edit.resize(1200, 600)
        text_edit.show()
        self.add_text_edit(text_edit)
        return self.last_id_str()

    def run_job(self):
        current_index = self.job_list.currentRow()
        if current_index < 0:
            QMessageBox.warning(self, "No Job Selected", "Please select a job first.")
            return
        if current_index >= 0:
            job = self.project.jobs[current_index]
            id_str = self.show_new_window("Run job: " + job.params["name"])
            worker = JobLogWorker(job, id_str)
            self.start_thread(worker)

    def run_all_jobs(self):
        id_str = self.show_new_window("Run project")
        worker = ProjectLogWorker(self.project, id_str)
        self.start_thread(worker)

    def add_action(self):
        current_index = self.job_list.currentRow()
        if current_index < 0:
            QMessageBox.warning(self, "No Job Selected", "Please select a job first.")
            return
        type_name = self.action_selector.currentText()
        action = ActionConfig(type_name)
        action.parent = self.get_current_job()
        dialog = ActionConfigDialog(action, self)
        if dialog.exec() == QDialog.Accepted:
            self.touch_project()
            self.project.jobs[current_index].add_sub_action(action)
            self.action_list.addItem(self.action_text(action))

    def show_action_config_dialog(self, action):
        dialog = ActionConfigDialog(action, self)
        if dialog.exec():
            current_job_index = self.job_list.currentRow()
            self.on_job_selected(current_job_index)

    def update_delete_buttons_state(self):
        has_job_selected = len(self.job_list.selectedItems()) > 0
        has_action_selected = len(self.action_list.selectedItems()) > 0
        self.delete_job_button.setEnabled(has_job_selected)
        self.delete_action_button.setEnabled(has_action_selected)
        if has_action_selected and has_job_selected:
            job_index = self.job_list.currentRow()
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
            enable_sub_actions = (current_action and not is_sub_action and current_action.type_name == ACTION_COMBO)
            self.sub_action_selector.setEnabled(enable_sub_actions)
            self.add_sub_action_button.setEnabled(enable_sub_actions)
            if is_sub_action:
                self.delete_action_button.setText("Delete Sub-action")
            else:
                self.delete_action_button.setText("Delete Action")
        else:
            self.sub_action_selector.setEnabled(False)
            self.add_sub_action_button.setEnabled(False)
            self.delete_action_button.setText("Delete Action")

    def action_text(self, action, is_sub_action=False, indent=True):
        txt = "    " if is_sub_action and indent else ""
        if action.params.get('name', '') != '':
            txt += action.params["name"]
        txt += f" [{action.type_name}]"
        return txt

    def on_job_selected(self, index):
        self.action_list.clear()
        if 0 <= index < len(self.project.jobs):
            job = self.project.jobs[index]
            for action in job.sub_actions:
                self.action_list.addItem(self.action_text(action))
                if len(action.sub_actions) > 0:
                    for sub_action in action.sub_actions:
                        self.action_list.addItem(self.action_text(sub_action, is_sub_action=True))

    def add_sub_action(self):
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
        type_name = self.sub_action_selector.currentText()
        sub_action = ActionConfig(type_name)
        dialog = ActionConfigDialog(sub_action, self)
        if dialog.exec() == QDialog.Accepted:
            self.touch_project()
            action.add_sub_action(sub_action)
            self.on_job_selected(current_job_index)
            self.action_list.setCurrentRow(current_action_index)

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
                    if current_action.type_name == ACTION_COMBO:
                        self.sub_action_selector.setEnabled(True)
                        self.add_sub_action_button.setEnabled(True)
                    else:
                        self.sub_action_selector.setEnabled(False)
                        self.add_sub_action_button.setEnabled(False)
                    self.show_action_config_dialog(current_action)
