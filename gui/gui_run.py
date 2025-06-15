from config.config import config
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QProgressBar
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal, Slot
from gui.project_converter import ProjectConverter
from gui.gui_logging import LogWorker, QTextEditLogger


class ColorEntry:
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def tuple(self):
        return self.r, self.g, self.b

    def hex(self):
        return f"{self.r:02x}{self.g:02x}{self.b:02x}"

    def q_color(self):
        return QColor(self.r, self.g, self.b)


class ColorPalette:
    BLACK = ColorEntry(0, 0, 0)
    WHITE = ColorEntry(255, 255, 255)
    LIGHT_BLUE = ColorEntry(210, 210, 240)
    DARK_BLUE = ColorEntry(0, 0, 160)
    MEDIUM_BLUE = ColorEntry(160, 160, 200)
    MEDIUM_GREEN = ColorEntry(160, 200, 160)

class ColorButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(1)
        self.setMaximumHeight(70)
        self.set_color(*ColorPalette.LIGHT_BLUE.tuple())

    def set_color(self, r, g, b):
        self.color = QColor(r, g, b)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color.name()};
                color: #{ColorPalette.DARK_BLUE.hex()};
                font-weight: bold;
                border: none;
                min-height: 1px;
                padding: 5px;
                margin: 0px;
            }}
        """)


class RunWindow(QTextEditLogger):
    light_background_color = ColorPalette.LIGHT_BLUE
    border_color = ColorPalette.DARK_BLUE
    text_color = ColorPalette.DARK_BLUE
    bar_color = ColorPalette.MEDIUM_BLUE
    action_running_color = ColorPalette.MEDIUM_BLUE
    action_done_color = ColorPalette.MEDIUM_GREEN
    
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
                h_layout.addWidget(widget, stretch=1)
                self.color_widgets.append(widget)
            layout.addWidget(row)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.set_progress_bar_style()
        self.progress_bar.setRange(0, 10)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.status_bar)
        self.setLayout(layout)

    def set_progress_bar_style(self, bar_color=None):
        if bar_color is None:
            bar_color = self.bar_color
        self.progress_bar.setStyleSheet(f"""
        QProgressBar {{
          border: 2px solid #{self.border_color.hex()};
          border-radius: 5px;
          text-align: center;
          font-weight: bold;
          font-size: 14px;
          background-color: #{self.light_background_color.hex()};
          color: #{self.text_color.hex()};
          min-height: 1px;
        }}
        QProgressBar::chunk {{
          background-color: #{bar_color.hex()};
        }}
        """)

    @Slot(int)
    def handle_before_action(self, id):
        if 0 <= id < len(self.color_widgets):
            self.color_widgets[id].set_color(*self.action_running_color.tuple())
            self.progress_bar.setValue(0)
        if id == -1:
            self.set_progress_bar_style(self.action_running_color)
    
    @Slot(int)
    def handle_after_action(self, id):
        if 0 <= id < len(self.color_widgets):
            self.color_widgets[id].set_color(*self.action_done_color.tuple())
            self.progress_bar.setValue(self.progress_bar.maximum())
        if id == -1:
            self.set_progress_bar_style(self.action_done_color)

    @Slot(int, int)
    def handle_step_count(self, id, steps):
        self.progress_bar.setMaximum(steps)

    @Slot(int, int)
    def handle_begin_steps(self, id):
        self.progress_bar.setValue(0)

    @Slot(int, int)
    def handle_end_steps(self, id):
        self.progress_bar.setValue(self.progress_bar.maximum())

    @Slot(int, int)
    def handle_after_step(self, id, step):
        self.progress_bar.setValue(step)
    
class JobLogWorker(LogWorker):
    before_action_signal = Signal(int)
    after_action_signal = Signal(int)
    step_count_signal = Signal(int, int)
    begin_steps_signal = Signal(int)
    end_steps_signal = Signal(int)
    after_step_signal = Signal(int, int)

    def __init__(self, job, id_str):
        LogWorker.__init__(self)
        self.job = job
        self.id_str = id_str

    def before_run(self, id):
        self.before_action_signal.emit(id)

    def after_run(self, id):
        self.after_action_signal.emit(id)

    def step_count(self, id, steps):
        self.step_count_signal.emit(id, steps)

    def begin_steps(self, id):
        self.begin_steps_signal.emit(id)

    def end_steps(self, id):
        self.end_steps_signal.emit(id)

    def after_step(self, id, step):
        self.after_step_signal.emit(id, step)
        
    def _do_run_job(self):
        converter = ProjectConverter()
        callbacks = {
            'before_run': self.before_run,
            'after_run': self.after_run,
            'step_count': self.step_count,
            'begin_steps': self.begin_steps,
            'end_steps': self.end_steps,
            'after_step': self.after_step
        }
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
