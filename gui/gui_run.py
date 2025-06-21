from config.config import config
from PySide6.QtWidgets import (QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QProgressBar,
                               QMessageBox, QScrollArea, QSizePolicy, QFrame)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from PySide6.QtCore import Signal, Slot
from gui.project_converter import ProjectConverter
from gui.gui_logging import LogWorker, QTextEditLogger, LOG_FONTS_STR
from gui.gui_images import MyPdfView

DISABLED_TAG = ""  # " <disabled>"
INDENT_SPACE = "     "


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
                padding: 4px;
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

    def __init__(self, labels, main_window, tab_position, parent=None):
        QTextEditLogger.__init__(self, parent)
        self.main_window = main_window
        self.tab_position = tab_position
        self.row_widget_id = 0
        layout = QVBoxLayout()
        self.color_widgets = []
        self.pdf_views = []
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
        output_layout = QHBoxLayout()
        left_layout, right_layout = QVBoxLayout(), QVBoxLayout()
        output_layout.addLayout(left_layout, stretch=1)
        output_layout.addLayout(right_layout, stretch=0)
        left_layout.addWidget(self.text_edit)
        self.right_area = QScrollArea()
        self.right_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.right_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.right_area.setWidgetResizable(True)
        self.right_area.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.right_area.setContentsMargins(0, 0, 0, 0)
        self.right_area.setFrameShape(QFrame.NoFrame)
        self.right_area.setViewportMargins(0, 0, 0, 0)
        self.right_area.viewport().setStyleSheet("background: transparent; border: 0px;")        
        self.image_area_widget = QWidget()
        self.image_area_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.image_area_widget.setContentsMargins(0, 0, 0, 0)
        self.right_area.setWidget(self.image_area_widget)
        self.image_layout = QVBoxLayout()
        self.image_layout.setSpacing(5)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.setAlignment(Qt.AlignTop)        
        self.image_area_widget.setLayout(self.image_layout)
        right_layout.addWidget(self.right_area)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_area.setMinimumWidth(0)
        self.right_area.setMaximumWidth(0)
        self.image_area_widget.setFixedWidth(0)
        layout.addLayout(output_layout)        
        self.close_button = QPushButton("Close")
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #{ColorPalette.MEDIUM_RED.hex()};
                color: #{ColorPalette.DARK_RED.hex()};
                font-weight: bold;
                border-radius: 5px;
                padding: 4px;
            }}
        """)
        self.close_button.clicked.connect(self.close_window)
        self.status_bar.addPermanentWidget(self.close_button)
        layout.addWidget(self.status_bar)
        self.setLayout(layout)

    def close_window(self):
        confirm = QMessageBox()
        confirm.setIcon(QMessageBox.Question)
        confirm.setWindowTitle('Close Tab')
        confirm.setInformativeText("Really close tab?")
        confirm.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        confirm.setDefaultButton(QMessageBox.Cancel)
        if confirm.exec() == QMessageBox.Ok:
            self.main_window.close_window(self.tab_position)

    def set_progress_bar_style(self, bar_color=None):
        if bar_color is None:
            bar_color = self.bar_color
        self.progress_bar.setStyleSheet(f"""
        QProgressBar {{
          border: 2px solid #{self.border_color.hex()};
          border-radius: 8px;
          text-align: center;
          font-weight: bold;
          font-size: 12px;
          background-color: #{self.light_background_color.hex()};
          color: #{self.text_color.hex()};
          min-height: 1px;
        }}
        QProgressBar::chunk {{
          border-radius: 6px;
          background-color: #{bar_color.hex()};
        }}
        """)

    @Slot(int, str)
    def handle_before_action(self, id, name):
        if 0 <= id < len(self.color_widgets[self.row_widget_id]):
            self.color_widgets[self.row_widget_id][id].set_color(*self.action_running_color.tuple())
            self.progress_bar.setValue(0)
        if id == -1:
            self.set_progress_bar_style(self.action_running_color)

    @Slot(int, str)
    def handle_after_action(self, id, name):
        if 0 <= id < len(self.color_widgets[self.row_widget_id]):
            self.color_widgets[self.row_widget_id][id].set_color(*self.action_done_color.tuple())
            self.progress_bar.setValue(self.progress_bar.maximum())
        if id == -1:
            self.set_progress_bar_style(self.action_done_color)
            self.row_widget_id += 1

    @Slot(int, str, str)
    def handle_step_count(self, id, name, steps):
        self.progress_bar.setMaximum(steps)

    @Slot(int, str)
    def handle_begin_steps(self, id, name):
        self.progress_bar.setValue(0)

    @Slot(int, str)
    def handle_end_steps(self, id, name):
        self.progress_bar.setValue(self.progress_bar.maximum())

    @Slot(int, str, str)
    def handle_after_step(self, id, name, step):
        self.progress_bar.setValue(step)

    @Slot(int, str, str)
    def handle_save_plot(self, id, name, path):
        pdf_view = MyPdfView(path, self)
        pdf_view.setWindowTitle(name)
        self.pdf_views.append(pdf_view)
        self.image_layout.addWidget(pdf_view)
        max_width = max(pv.size().width() for pv in self.pdf_views) if self.pdf_views else 0        
        scrollbar_needed = any(pv.size().height() > self.right_area.viewport().height() for pv in self.pdf_views)
        scrollbar_width = self.right_area.verticalScrollBar().sizeHint().width() if scrollbar_needed else 0
        needed_width = max_width + scrollbar_width + 2
        self.right_area.setFixedWidth(needed_width)
        self.image_area_widget.setFixedWidth(needed_width)
        self.right_area.updateGeometry()
        self.image_area_widget.updateGeometry()    

class RunWorker(LogWorker):
    before_action_signal = Signal(int, str)
    after_action_signal = Signal(int, str)
    step_count_signal = Signal(int, str, int)
    begin_steps_signal = Signal(int, str)
    end_steps_signal = Signal(int, str)
    after_step_signal = Signal(int, str, int)
    save_plot_signal = Signal(int, str, str)

    def __init__(self, id_str):
        LogWorker.__init__(self)
        self.id_str = id_str
        self.callbacks = {
            'before_action': self.before_action,
            'after_action': self.after_action,
            'step_count': self.step_count,
            'begin_steps': self.begin_steps,
            'end_steps': self.end_steps,
            'after_step': self.after_step,
            'save_plot': self.save_plot
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

    def save_plot(self, id, name, path):
        self.save_plot_signal.emit(id, name, path)

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
