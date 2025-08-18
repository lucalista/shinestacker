# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0915, R0914, R0917, R0913, R0902
import time
from PySide6.QtWidgets import (QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QProgressBar,
                               QMessageBox, QScrollArea, QSizePolicy, QFrame, QLabel, QComboBox)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, QTimer
from PySide6.QtCore import Signal, Slot
from .. config.constants import constants
from .. config.gui_constants import gui_constants
from .colors import RED_BUTTON_STYLE, BLUE_BUTTON_STYLE, BLUE_COMBO_STYLE
from .gui_logging import LogWorker, QTextEditLogger
from .gui_images import GuiPdfView, GuiImageView, GuiOpenApp
from .colors import ColorPalette


ACTION_RUNNING_COLOR = ColorPalette.MEDIUM_BLUE
ACTION_DONE_COLOR = ColorPalette.MEDIUM_GREEN


class ColorButton(QPushButton):
    def __init__(self, text, enabled, parent=None):
        super().__init__(text.replace(gui_constants.DISABLED_TAG, ''), parent)
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


class TimerProgressBar(QProgressBar):
    light_background_color = ColorPalette.LIGHT_BLUE
    border_color = ColorPalette.DARK_BLUE
    text_color = ColorPalette.DARK_BLUE

    def __init__(self):
        super().__init__()
        super().setRange(0, 10)
        super().setValue(0)
        self.set_running_style()
        self._start_time = -1
        self._current_time = -1

    def set_style(self, bar_color=None):
        if bar_color is None:
            bar_color = ColorPalette.MEDIUM_BLUE
        self.setStyleSheet(f"""
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

    def time_str(self, secs):
        ss = int(secs)
        h = ss // 3600
        m = (ss % 3600) // 60
        s = (ss % 3600) % 60
        x = secs - ss
        t_str = f"{s:02d}" + f"{x:.1f}s".lstrip('0')
        if m > 0:
            t_str = f"{m:02d}:{t_str}"
        if h > 0:
            t_str = f"{h:02d}:{t_str}"
        if m > 0 or h > 0:
            t_str = t_str.lstrip('0')
        elif 0 < s < 10:
            t_str = t_str.lstrip('0')
        elif s == 0:
            t_str = t_str[1:]
        return t_str

    def check_time(self, val):
        if self._start_time < 0:
            raise RuntimeError("TimeProgressbar: start and must be called before setValue and stop")
        self._current_time = time.time()
        elapsed_time = self._current_time - self._start_time
        elapsed_str = self.time_str(elapsed_time)
        fmt = f"Progress: %p% - %v of %m - elapsed: {elapsed_str}"
        if 0 < val < self.maximum():
            time_per_iter = elapsed_time / val
            estimated_time = time_per_iter * self.maximum()
            remaining_time = max(0, estimated_time - elapsed_time)
            remaining_str = self.time_str(remaining_time)
            fmt += f", {remaining_str} remaining"
        self.setFormat(fmt)

    def start(self, steps):
        super().setMaximum(steps)
        self._start_time = time.time()
        self.setValue(0)

    def stop(self):
        self.check_time(self.maximum())
        self.setValue(self.maximum())

    # pylint: disable=C0103
    def setValue(self, val):
        self.check_time(val)
        super().setValue(val)
    # pylint: enable=C0103

    def set_running_style(self):
        self.set_style(ACTION_RUNNING_COLOR)

    def set_done_style(self):
        self.set_style(ACTION_DONE_COLOR)


class RunWindow(QTextEditLogger):
    def __init__(self, labels, stop_worker_callback, close_window_callback, retouch_paths, parent):
        QTextEditLogger.__init__(self, parent)
        self.retouch_paths = retouch_paths
        self.stop_worker_callback = stop_worker_callback
        self.close_window_callback = close_window_callback
        self.row_widget_id = 0
        layout = QVBoxLayout()
        self.color_widgets = []
        self.image_views = []
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
        self.progress_bar = TimerProgressBar()
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

        n_paths = len(self.retouch_paths) if self.retouch_paths else 0
        if n_paths == 1:
            self.retouch_widget = QPushButton(f"Retouch {self.retouch_paths[0][0]}")
            self.retouch_widget.setStyleSheet(BLUE_BUTTON_STYLE)
            self.retouch_widget.setEnabled(False)
            self.retouch_widget.clicked.connect(lambda: self.retouch(self.retouch_paths[0]))
            self.status_bar.addPermanentWidget(self.retouch_widget)
        elif n_paths > 1:
            options = ["Retouch:"] + [f"{path[0]}" for path in self.retouch_paths]
            self.retouch_widget = QComboBox()
            self.retouch_widget.setStyleSheet(BLUE_COMBO_STYLE)
            self.retouch_widget.addItems(options)
            self.retouch_widget.setEnabled(False)
            self.retouch_widget.currentIndexChanged.connect(
                lambda: self.retouch(
                    self.retouch_paths[self.retouch_widget.currentIndex() - 1]))
            self.status_bar.addPermanentWidget(self.retouch_widget)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setStyleSheet(RED_BUTTON_STYLE)
        self.stop_button.clicked.connect(self.stop_worker)
        self.status_bar.addPermanentWidget(self.stop_button)

        self.close_button = QPushButton("Close")
        self.close_button.setEnabled(False)
        self.close_button.setStyleSheet(RED_BUTTON_STYLE)
        self.close_button.clicked.connect(self.close_window)
        self.status_bar.addPermanentWidget(self.close_button)

        layout.addWidget(self.status_bar)
        self.setLayout(layout)

    def stop_worker(self):
        self.stop_worker_callback(self.id_str())

    def retouch(self, path):

        def find_parent(widget, class_name):
            current = widget
            while current is not None:
                if current.__class__.__name__ == class_name:
                    return current
                current = current.parent()
            return None
        parent = find_parent(self, "MainWindow")
        if parent:
            parent.retouch_callback(path[1])
        else:
            raise RuntimeError("Can't find MainWindow parent.")

    def close_window(self):
        confirm = QMessageBox()
        confirm.setIcon(QMessageBox.Question)
        confirm.setWindowTitle('Close Tab')
        confirm.setInformativeText("Really close tab?")
        confirm.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        confirm.setDefaultButton(QMessageBox.Cancel)
        if confirm.exec() == QMessageBox.Ok:
            self.close_window_callback(self.id_str())

    @Slot(int, str)
    def handle_before_action(self, run_id, _name):
        if 0 <= run_id < len(self.color_widgets[self.row_widget_id]):
            self.color_widgets[self.row_widget_id][run_id].set_color(*ACTION_RUNNING_COLOR.tuple())
            self.progress_bar.start(1)
        if run_id == -1:
            self.progress_bar.set_running_style()

    @Slot(int, str)
    def handle_after_action(self, run_id, _name):
        if 0 <= run_id < len(self.color_widgets[self.row_widget_id]):
            self.color_widgets[self.row_widget_id][run_id].set_color(*ACTION_DONE_COLOR.tuple())
            self.progress_bar.stop()
        if run_id == -1:
            self.row_widget_id += 1
            self.progress_bar.set_done_style()

    @Slot(int, str, str)
    def handle_step_counts(self, _run_id, _name, steps):
        self.progress_bar.start(steps)

    @Slot(int, str)
    def handle_begin_steps(self, _run_id, _name):
        self.progress_bar.start(1)

    @Slot(int, str)
    def handle_end_steps(self, _run_id, _name):
        self.progress_bar.stop()

    @Slot(int, str, str)
    def handle_after_step(self, _run_id, _name, step):
        self.progress_bar.setValue(step)

    @Slot(int, str, str)
    def handle_save_plot(self, _run_id, name, path):
        label = QLabel(name, self)
        label.setStyleSheet("QLabel {margin-top: 5px; font-weight: bold;}")
        self.image_layout.addWidget(label)
        ext = path.split('.')[-1].lower()
        if ext == 'pdf':
            image_view = GuiPdfView(path, self)
        elif ext in ['jpg', 'jpeg', 'tif', 'tiff', 'png']:
            image_view = GuiImageView(path, self)
        else:
            raise RuntimeError("Can't visualize file type {ext}.")
        self.image_views.append(image_view)
        self.image_layout.addWidget(image_view)
        max_width = max(pv.size().width() for pv in self.image_views) if self.image_views else 0
        needed_width = max_width + 20
        self.right_area.setFixedWidth(needed_width)
        self.image_area_widget.setFixedWidth(needed_width)
        self.right_area.updateGeometry()
        self.image_area_widget.updateGeometry()
        QTimer.singleShot(
            0, lambda: self.right_area.verticalScrollBar().setValue(
                self.right_area.verticalScrollBar().maximum()))

    @Slot(int, str, str, str)
    def handle_open_app(self, _run_id, name, app, path):
        label = QLabel(name, self)
        label.setStyleSheet("QLabel {margin-top: 5px; font-weight: bold;}")
        self.image_layout.addWidget(label)
        image_view = GuiOpenApp(app, path, self)
        self.image_views.append(image_view)
        self.image_layout.addWidget(image_view)
        max_width = max(pv.size().width() for pv in self.image_views) if self.image_views else 0
        needed_width = max_width + 15
        self.right_area.setFixedWidth(needed_width)
        self.image_area_widget.setFixedWidth(needed_width)
        self.right_area.updateGeometry()
        self.image_area_widget.updateGeometry()
        QTimer.singleShot(
            0, lambda: self.right_area.verticalScrollBar().setValue(
                self.right_area.verticalScrollBar().maximum()))


class RunWorker(LogWorker):
    before_action_signal = Signal(int, str)
    after_action_signal = Signal(int, str)
    step_counts_signal = Signal(int, str, int)
    begin_steps_signal = Signal(int, str)
    end_steps_signal = Signal(int, str)
    after_step_signal = Signal(int, str, int)
    save_plot_signal = Signal(int, str, str)
    open_app_signal = Signal(int, str, str, str)

    def __init__(self, id_str):
        LogWorker.__init__(self)
        self.id_str = id_str
        self.status = constants.STATUS_RUNNING
        self.callbacks = {
            'before_action': self.before_action,
            'after_action': self.after_action,
            'step_counts': self.step_counts,
            'begin_steps': self.begin_steps,
            'end_steps': self.end_steps,
            'after_step': self.after_step,
            'save_plot': self.save_plot,
            'check_running': self.check_running,
            'open_app': self.open_app
        }
        self.tag = ""

    def before_action(self, run_id, name):
        self.before_action_signal.emit(run_id, name)

    def after_action(self, run_id, name):
        self.after_action_signal.emit(run_id, name)

    def step_counts(self, run_id, name, steps):
        self.step_counts_signal.emit(run_id, name, steps)

    def begin_steps(self, run_id, name):
        self.begin_steps_signal.emit(run_id, name)

    def end_steps(self, run_id, name):
        self.end_steps_signal.emit(run_id, name)

    def after_step(self, run_id, name, step):
        self.after_step_signal.emit(run_id, name, step)

    def save_plot(self, run_id, name, path):
        self.save_plot_signal.emit(run_id, name, path)

    def open_app(self, run_id, name, app, path):
        self.open_app_signal.emit(run_id, name, app, path)

    def check_running(self, _run_id, _name):
        return self.status == constants.STATUS_RUNNING

    def run(self):
        # pylint: disable=line-too-long
        self.status_signal.emit(f"{self.tag} running...", constants.RUN_ONGOING, "", 0)
        self.html_signal.emit(f'''
        <div style="margin: 2px 0; font-family: {constants.LOG_FONTS_STR};">
        <span style="color: #{ColorPalette.DARK_BLUE.hex()}; font-style: italic; font-weigt: bold;">{self.tag} begins</span>
        </div>
        ''') # noqa
        status, error_message = self.do_run()
        if status == constants.RUN_FAILED:
            message = f"{self.tag} failed"
            color = "#" + ColorPalette.DARK_RED.hex()
        elif status == constants.RUN_COMPLETED:
            message = f"{self.tag} ended successfully"
            color = "#" + ColorPalette.DARK_BLUE.hex()
        elif status == constants.RUN_STOPPED:
            message = f"{self.tag} stopped"
            color = "#" + ColorPalette.DARK_RED.hex()
        else:
            message = ''
            color = "#000000"
        self.html_signal.emit(f'''
        <div style="margin: 2px 0; font-family: {constants.LOG_FONTS_STR};">
        <span style="color: {color}; font-style: italic; font-weight: bold;">{message}</span>
        </div>
        ''')
        # pylint: enable=line-too-long
        self.end_signal.emit(status, self.id_str, message)
        self.status_signal.emit(message, status, error_message, 0)

    def stop(self):
        self.status = constants.STATUS_STOPPED
        self.wait()
