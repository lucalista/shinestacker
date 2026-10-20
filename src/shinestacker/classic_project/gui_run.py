# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0915, R0914, R0917, R0913, R0902, R0904
import os
import traceback
from PySide6.QtWidgets import (QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QSplitter,
                               QMessageBox, QScrollArea, QSizePolicy, QFrame, QLabel, QComboBox)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, QTimer
from PySide6.QtCore import Slot
from .. config.gui_constants import gui_constants
from .. algorithms.utils import extension_supported_output, extension_pdf
from .. algorithms.plot_manager import DirectPlotManager
from .. gui.gui_logging import QTextEditLogger
from .. gui.gui_images import GuiPdfView, GuiImageView, GuiOpenApp
from .. gui.colors import (
    ColorPalette,
    RED_BUTTON_STYLE, BLUE_BUTTON_STYLE, BLUE_COMBO_STYLE,
    ACTION_RUNNING_COLOR, ACTION_COMPLETED_COLOR,
    ACTION_STOPPED_COLOR, ACTION_FAILED_COLOR)
from .. gui.time_progress_bar import TimerProgressBar
from .. gui.flow_layout import FlowLayout
from .. common_project.processing_widget import MultiModuleStatusContainer


class ColorButton(QPushButton):
    def __init__(self, text, enabled, parent=None):
        super().__init__(text.replace(gui_constants.DISABLED_TAG, ''), parent)
        self.setMinimumHeight(1)
        self.setMaximumHeight(70)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
                min-width: 60px;
            }}
        """)


class RunWindow(QTextEditLogger):
    def __init__(self, labels, close_window_callback, retouch_paths, parent):
        QTextEditLogger.__init__(self, parent)
        self.retouch_paths = retouch_paths
        self.close_window_callback = close_window_callback
        self.row_widget_id = 0
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.color_widgets = []
        self.image_views = []
        if len(labels) > 0:
            for label_row in labels:
                self.color_widgets.append([])
                row = QWidget(self)
                if len(label_row) > 1:
                    h_layout = FlowLayout(row)
                else:
                    h_layout = QHBoxLayout(row)
                h_layout.setContentsMargins(0, 0, 0, 0)
                h_layout.setSpacing(2)
                for label, enabled in label_row:
                    widget = ColorButton(label, enabled)
                    h_layout.addWidget(widget)
                    self.color_widgets[-1].append(widget)
                layout.addWidget(row)
        self.progress_bar = TimerProgressBar()
        layout.addWidget(self.progress_bar)
        output_layout = QHBoxLayout()
        left_layout, right_layout = QVBoxLayout(), QVBoxLayout()
        left_layout.setSpacing(10)
        left_layout.setContentsMargins(5, 5, 5, 5)
        output_layout.addLayout(left_layout, stretch=1)
        output_layout.addLayout(right_layout, stretch=0)
        self.frames_status_box = MultiModuleStatusContainer()
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.frames_status_box)
        self.splitter.addWidget(self.text_edit)
        self.splitter.setSizes([0, 1])
        self.frames_status_box.content_size_changed.connect(self.adjust_splitter)
        left_layout.addWidget(self.splitter)
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

        self.close_button = QPushButton("Close")
        self.close_button.setEnabled(False)
        self.close_button.setStyleSheet(RED_BUTTON_STYLE)
        self.close_button.clicked.connect(self.close_window)
        self.status_bar.addPermanentWidget(self.close_button)
        layout.addWidget(self.status_bar)
        self.setLayout(layout)
        self.user_manually_adjusted_splitter = False
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        self.plot_manager = DirectPlotManager()

    def _on_splitter_moved(self):
        self.user_manually_adjusted_splitter = True

    def adjust_splitter(self):
        if self.user_manually_adjusted_splitter:
            return
        QTimer.singleShot(50, self._delayed_adjust_splitter)

    def _delayed_adjust_splitter(self):
        content_height = self.frames_status_box.get_content_height()
        if content_height > 0:
            current_sizes = self.splitter.sizes()
            if current_sizes[0] < MultiModuleStatusContainer.MAX_HEIGHT:
                new_top_size = min(content_height, MultiModuleStatusContainer.MAX_HEIGHT)
                available_height = self.splitter.height()
                if available_height > 0:
                    new_bottom_size = available_height - new_top_size
                    if new_bottom_size > 100:
                        self.splitter.setSizes([new_top_size, new_bottom_size])

    def retouch(self, path):

        def find_parent(widget, class_name):
            current = widget
            while current is not None:
                if current.objectName() == class_name:
                    return current
                current = current.parent()
            return None

        parent = find_parent(self, "mainWindow")
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
        if self.row_widget_id < len(self.color_widgets):
            widgets = self.color_widgets[self.row_widget_id]
            if 0 <= run_id < len(widgets):
                widget = widgets[run_id]
                widget.set_color(*ACTION_RUNNING_COLOR.tuple())
                widget.setText(widget.text() + " - running")
                self.progress_bar.start(1)
        if run_id == -1:
            self.progress_bar.run()

    @Slot(int, str)
    def handle_after_action(self, run_id, _name):
        if self.row_widget_id < len(self.color_widgets):
            widgets = self.color_widgets[self.row_widget_id]
            if 0 <= run_id < len(widgets):
                widget = widgets[run_id]
                widget.set_color(*ACTION_COMPLETED_COLOR.tuple())
                postfix = f" - completed in {self.progress_bar.elapsed_str}"
                widget.setText(widget.text().replace(" - running", "") + postfix)
                self.progress_bar.stop()
        if run_id == -1:
            self.row_widget_id += 1
            self.progress_bar.done()

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

    @Slot(int, str, str, str, str)
    def handle_save_plot(self, _run_id, _module_name, caption, path, _tag="_dfault"):
        label = QLabel(caption, self)
        label.setStyleSheet("QLabel {margin-top: 5px; font-weight: bold;}")
        self.image_layout.addWidget(label)
        try:
            if extension_pdf(path):
                image_view = GuiPdfView(path, self)
            elif extension_supported_output(path):
                image_view = GuiImageView(path, self)
            else:
                traceback.print_exc()
                raise RuntimeError(f"Can't visualize file type {os.path.splitext(path)[1]}.")
            self.image_views.append(image_view)
            self.image_layout.addWidget(image_view)
            needed_width = gui_constants.GUI_IMG_WIDTH + 20
            self.right_area.setFixedWidth(needed_width)
            self.image_area_widget.setFixedWidth(needed_width)
            self.right_area.updateGeometry()
            self.image_area_widget.updateGeometry()
            QTimer.singleShot(
                0, lambda: self.right_area.verticalScrollBar().setValue(
                    self.right_area.verticalScrollBar().maximum()))
        except RuntimeError:
            traceback.print_exc()

    @Slot(int, str, str, str)
    def handle_open_app(self, _run_id, name, path):
        label = QLabel(name, self)
        label.setStyleSheet("QLabel {margin-top: 5px; font-weight: bold;}")
        self.image_layout.addWidget(label)
        image_view = GuiOpenApp(path, self)
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

    @Slot(int)
    def handle_run_completed(self, _run_id):
        self.progress_bar.setFormat(self.progress_bar.format() + " - completed")

    def handle_run_interrupt(self, run_id, color, postfix):
        if self.row_widget_id < len(self.color_widgets):
            widgets = self.color_widgets[self.row_widget_id]
            if 0 <= run_id < len(widgets):
                widget = widgets[run_id]
                widget.set_color(*color)
                widget.setText(widget.text().replace(" - running", "") + postfix)

    @Slot(int)
    def handle_run_stopped(self, run_id, _name):
        postfix = f" - stopped after {self.progress_bar.elapsed_str}"
        self.progress_bar.stop()
        self.handle_run_interrupt(run_id, ACTION_STOPPED_COLOR.tuple(), postfix)

    @Slot(int)
    def handle_run_failed(self, run_id, _name):
        postfix = f" - failed after {self.progress_bar.elapsed_str}"
        self.progress_bar.fail()
        self.handle_run_interrupt(run_id, ACTION_FAILED_COLOR.tuple(), postfix)

    @Slot(str)
    def handle_add_status_box(self, module_name):
        self.frames_status_box.add_module(module_name)

    @Slot(str, str, int)
    def handle_add_frame(self, module_name, filename, total_actions):
        self.frames_status_box.add_frame(module_name, filename, total_actions)

    @Slot(str, str, int)
    def handle_update_frame_status(self, module_name, filename, status_id):
        self.frames_status_box.update_frame_status(module_name, filename, status_id)

    @Slot(str, str, int)
    def handle_set_total_actions(self, module_name, filename, status_id):
        self.frames_status_box.set_frame_total_actions(module_name, filename, status_id)

    @Slot(str, object, str)
    def handle_save_plot_via_manager(self, filename, fig, tag="_default"):
        self.plot_manager.save_plot(filename, fig, tag)
