from config.config import config
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QProgressBar
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal, Slot
from gui.project_converter import ProjectConverter
from gui.gui_logging import LogWorker, QTextEditLogger, LOG_FONTS_STR

DISABLED_TAG = "" # " <disabled>"


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
    LIGHT_RED = ColorEntry(240, 210, 210)
    DARK_BLUE = ColorEntry(0, 0, 160)
    DARK_RED = ColorEntry(160, 0, 0)
    MEDIUM_BLUE = ColorEntry(160, 160, 200)
    MEDIUM_GREEN = ColorEntry(160, 200, 160)
    MEDIUM_RED = ColorEntry(200, 160, 160)


class ColorButton(QPushButton):
    def __init__(self, text, enabled, parent=None):
        super().__init__(text.replace(DISABLED_TAG, ''), parent)
        self.setMinimumHeight(1)
        self.setMaximumHeight(70)
        color = ColorPalette.LIGHT_BLUE if enabled else ColorPalette.LIGHT_RED
        self.set_color(*color.tuple())

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
        self.row_widget_id = 0
        self.resize(1200, 600)
        layout = QVBoxLayout()
        self.color_widgets = []
        if len(labels) > 0:
            for label_row in labels:
                self.color_widgets.append([])
                row = QWidget(self)
                h_layout = QHBoxLayout(row)
                h_layout.setContentsMargins(0, 0, 0, 0)
                h_layout.setSpacing(2)
                for label, enabled in label_row:
                    widget = ColorButton(label, enabled)
                    h_layout.addWidget(widget, stretch=1)
                    self.color_widgets[-1].append(widget)
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
          border-radius: 10px;
          text-align: center;
          font-weight: bold;
          font-size: 14px;
          background-color: #{self.light_background_color.hex()};
          color: #{self.text_color.hex()};
          min-height: 1px;
        }}
        QProgressBar::chunk {{
          border-radius: 8px;
          background-color: #{bar_color.hex()};
        }}
        """)

    @Slot(int)
    def handle_before_action(self, id, name):
        if 0 <= id < len(self.color_widgets[self.row_widget_id]):
            self.color_widgets[self.row_widget_id][id].set_color(*self.action_running_color.tuple())
            self.progress_bar.setValue(0)
        if id == -1:
            self.set_progress_bar_style(self.action_running_color)

    @Slot(int)
    def handle_after_action(self, id, name):
        if 0 <= id < len(self.color_widgets[self.row_widget_id]):
            self.color_widgets[self.row_widget_id][id].set_color(*self.action_done_color.tuple())
            self.progress_bar.setValue(self.progress_bar.maximum())
        if id == -1:
            self.set_progress_bar_style(self.action_done_color)
            self.row_widget_id += 1

    @Slot(int, int)
    def handle_step_count(self, id, name, steps):
        self.progress_bar.setMaximum(steps)

    @Slot(int, int)
    def handle_begin_steps(self, id, name):
        self.progress_bar.setValue(0)

    @Slot(int, int)
    def handle_end_steps(self, id, name):
        self.progress_bar.setValue(self.progress_bar.maximum())

    @Slot(int, int)
    def handle_after_step(self, id, name, step):
        self.progress_bar.setValue(step)


class RunWorker(LogWorker):
    before_action_signal = Signal(int, str)
    after_action_signal = Signal(int, str)
    step_count_signal = Signal(int, str, int)
    begin_steps_signal = Signal(int, str)
    end_steps_signal = Signal(int, str)
    after_step_signal = Signal(int, str, int)

    def __init__(self, id_str):
        LogWorker.__init__(self)
        self.id_str = id_str
        self.callbacks = {
            'before_action': self.before_action,
            'after_action': self.after_action,
            'step_count': self.step_count,
            'begin_steps': self.begin_steps,
            'end_steps': self.end_steps,
            'after_step': self.after_step
        }
        self.tag = ""

    def before_action(self, id, name):
        self.before_action_signal.emit(id, name)

    def after_action(self, id, name):
        self.after_action_signal.emit(id, name)

    def step_count(self, id, name, steps):
        self.step_count_signal.emit(id, name, steps)

    def begin_steps(self, id, name):
        self.begin_steps_signal.emit(id, name)

    def end_steps(self, id, name):
        self.end_steps_signal.emit(id, name)

    def after_step(self, id, name, step):
        self.after_step_signal.emit(id, name, step)

    def run(self):
        run_error = False
        self.status_signal.emit(f"{self.tag} running...", 0)
        self.html_signal.emit(f'''
        <div style="margin: 2px 0; font-family: {LOG_FONTS_STR};">
        <span style="color: #{ColorPalette.DARK_BLUE.hex()}; font-weight: bold;">{self.tag} begins</span>
        </div>
        ''')
        if config.TRAP_RUN_EXCEPTIONS:
            try:
                self._do_run()
            except Exception as e:
                run_error = True
                self.exception_signal.emit(f'{self.tag} failed:\n{str(e)}')
                self.exception_signal.emit(f'{self.tag} failed:\n{str(e)}')
        else:
            self._do_run()
        if run_error:
            message = f"{self.tag} failed"
            status = 1
            color = "#" + ColorPalette.DARK_RED.hex()
        else:
            message = f"{self.tag} ended successfully"
            status = 0
            color = "#" + ColorPalette.DARK_BLUE.hex()
            self.html_signal.emit(f'''
        <div style="margin: 2px 0; font-family: {LOG_FONTS_STR};">
        <span style="color: {color}; font-weight: bold;">{message}</span>
        </div>
        ''')
        self.end_signal.emit(status, message)
        self.status_signal.emit(f"{self.tag} completed", 0)


class JobLogWorker(RunWorker):
    def __init__(self, job, id_str):
        super().__init__(id_str)
        self.job = job
        self.tag = "Job"

    def _do_run(self):
        converter = ProjectConverter()
        converter.run_job(self.job, self.id_str, self.callbacks)


class ProjectLogWorker(RunWorker):
    def __init__(self, project, id_str):
        super().__init__(id_str)
        self.project = project
        self.tag = "Project"

    def _do_run(self):
        converter = ProjectConverter()
        converter.run_project(self.project, self.id_str, self.callbacks)
