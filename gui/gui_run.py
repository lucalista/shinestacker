from config.config import config
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal, Slot
from gui.project_converter import ProjectConverter
from gui.gui_logging import LogWorker, QTextEditLogger


class ColorButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(1)
        self.setMaximumHeight(70)
        self.set_color(210, 210, 240)

    def set_color(self, r, g, b):
        self.color = QColor(r, g, b)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color.name()};
                color: black;
                font-weight: bold;
                border: none;
                min-height: 1px;
                padding: 5px;
                margin: 0px;
            }}
        """)        


class RunWindow(QTextEditLogger):    
    def __init__(self, labels):
        QTextEditLogger.__init__(self)
        self.resize(1200, 600)
        layout = QVBoxLayout()
        self.color_widgets = []
        if len(labels) > 0:
            row = QWidget(self)
            h_layout = QHBoxLayout(row)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(2)
            for label in labels:
                widget = ColorButton(label)
                widget.setMinimumHeight(80)
                h_layout.addWidget(widget, stretch=1)
                self.color_widgets.append(widget)
            layout.addWidget(row)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.status_bar)
        self.setLayout(layout)

    @Slot(int)
    def handle_before_action(self, id):
        if 0 <= id < len(self.color_widgets):
            self.color_widgets[id].set_color(160, 160, 200)
    
    @Slot(int)
    def handle_after_action(self, id):
        if 0 <= id < len(self.color_widgets):
            self.color_widgets[id].set_color(160, 200, 160)
    
class JobLogWorker(LogWorker):
    before_action_signal = Signal(int)
    after_action_signal = Signal(int)

    def __init__(self, job, id_str):
        LogWorker.__init__(self)
        self.job = job
        self.id_str = id_str

    def before_run(self, id):
        self.before_action_signal.emit(id)

    def after_run(self, id):
        self.after_action_signal.emit(id)

    def _do_run_job(self):
        converter = ProjectConverter()
        callbacks = {'before_run': self.before_run, 'after_run': self.after_run}
        converter.run_job(self.job, self.id_str, callbacks)

    def run(self):
        job_error = False
        self.status_signal.emit("Job running...", 0)
        if config.TRAP_RUN_EXCEPTIONS:
            try:
                self._do_run_job()
            except Exception as e:
                job_error = True
                self.exception_signal.emit(f'Job {self.job.params["name"]} failed:\n{str(e)}')
        else:
            self._do_run_job()
        if job_error:
            message = "Job failed."
            status = 1
            color = "#ff0000"
        else:
            message = "Job ended successfully."
            status = 0
            color = "#000089"
        self.html_signal.emit(f'''
        <hr><div style="margin: 2px 0; font-family: monospace;">
        <span style="color: {color}; font-weight: bold;">{message}</span>
        </div>
        ''')
        self.end_signal.emit(status, message)
        self.status_signal.emit("Job completed", 0)


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
        self.status_signal.emit("Project running...", 0)
        if config.TRAP_RUN_EXCEPTIONS:
            try:
                self._do_run_project()
            except Exception as e:
                job_error = True
                self.exception_signal.emit(f'Project failed:\n{str(e)}')
        else:
            self._do_run_project()

        if job_error:
            message = "Run failed."
            status = 1
            color = "#ff0000"
        else:
            message = "Project ended successfully."
            status = 0
            color = "#000089"
        self.html_signal.emit(f'''
        <hr><div style="margin: 2px 0; font-family: monospace;">
        <span style="color: {color}; font-weight: bold;">{message}</span>
        </div>
        ''')
        self.end_signal.emit(status, message)
        self.status_signal.emit("Project completed", 0)
