# pylint: disable=C0103, C0114, C0115, C0116, E0611, R0903, R0915, R0914, R0917, R0913, R0902
import os
import math
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QScrollArea, QLabel, QSizePolicy, QVBoxLayout)
from .. gui.colors import ColorPalette
from .. gui.gui_images import open_file


class MultiModuleStatusContainer(QWidget):
    MAX_HEIGHT = 400
    content_size_changed = Signal()

    def __init__(self, classic_view=True):
        super().__init__()
        self.classic_view = classic_view
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self._programmatic_scroll = False
        self._user_scrolling = False
        self._scrolling_timer = QTimer()
        self._scrolling_timer.setSingleShot(True)
        self._scrolling_timer.timeout.connect(self._reset_user_scrolling)
        self._scrolling_cooldown = 4000  # 4 seconds
        if self.classic_view:
            self.scroll_area = QScrollArea()
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.scroll_area.setFrameShape(QScrollArea.NoFrame)
            self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_user_scroll)
            self.container_widget = QWidget()
            self.layout = QVBoxLayout(self.container_widget)
            self.layout.setContentsMargins(0, 0, 0, 0)
            self.layout.setSpacing(0)
            self.layout.setAlignment(Qt.AlignTop)
            self.scroll_area.setWidget(self.container_widget)
            main_layout.addWidget(self.scroll_area)
        else:
            self.container_widget = QWidget()
            self.layout = QVBoxLayout(self.container_widget)
            self.layout.setContentsMargins(0, 0, 0, 0)
            self.layout.setSpacing(0)
            self.layout.setAlignment(Qt.AlignTop)
            main_layout.addWidget(self.container_widget)
        self.status_widgets = {}
        self.setMinimumHeight(0)
        if self.classic_view:
            self.setMaximumHeight(self.MAX_HEIGHT)
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self.content_size_changed.emit)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(500)
        try:
            QTimer.singleShot(
                500,
                lambda: [self.content_size_changed.emit(), self._scroll_to_bottom()])
        except RuntimeError:
            pass

    def _on_user_scroll(self, _value):
        if self._programmatic_scroll:
            self._programmatic_scroll = False
            return
        self._user_scrolling = True
        self._scrolling_timer.start(self._scrolling_cooldown)

    def _reset_user_scrolling(self):
        self._user_scrolling = False

    def _scroll_to_bottom(self):
        if self.classic_view and not self._user_scrolling:
            scrollbar = self.scroll_area.verticalScrollBar()
            self._programmatic_scroll = True
            scrollbar.setValue(scrollbar.maximum())

    def add_module(self, module_name):
        if self.classic_view:
            label = QLabel(module_name)
            label.setStyleSheet("QLabel { font-weight: bold; margin: 0px; padding: 0px; }")
            label.setContentsMargins(0, 0, 0, 0)
            label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            self.layout.addWidget(label)
        status_widget = PreprocessingStatusWidget()
        self.layout.addWidget(status_widget)
        if module_name in self.status_widgets:
            raise RuntimeError(f"Module {module_name} already added")
        self.status_widgets[module_name] = status_widget
        QTimer.singleShot(10, lambda: [self.content_size_changed.emit(), self._scroll_to_bottom()])
        return len(self.status_widgets) - 1

    def get_widget(self, module_name):
        return self.status_widgets.get(module_name)

    def add_frame(self, module_name, filename, total_actions):
        status_widget = self.get_widget(module_name)
        if status_widget:
            status_widget.add_frame(filename, total_actions)
        QTimer.singleShot(10, lambda: [self.content_size_changed.emit(), self._scroll_to_bottom()])

    def set_frame_total_actions(self, module_name, filename, total_actions):
        status_widget = self.get_widget(module_name)
        if status_widget:
            status_widget.set_total_actions(filename, total_actions)

    def update_frame_status(self, module_name, filename, status_id):
        status_widget = self.get_widget(module_name)
        if status_widget:
            status_widget.update_frame_status(filename, status_id)

    def get_content_height(self):
        self.container_widget.layout().activate()
        return self.container_widget.layout().totalMinimumSize().height()

    def clear(self):
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self.status_widgets.clear()

    def capture_widget_state(self):
        state = {'modules': [], 'classic_view': self.classic_view}
        for module_name, status_widget in self.status_widgets.items():
            module_state = status_widget.capture_widget_state()
            module_state['name'] = module_name
            state['modules'].append(module_state)
        return state

    def restore_widget_state(self, state):
        self.clear()
        for module_state in state.get('modules', []):
            module_name = module_state.get('name', '')
            if module_name:
                self.add_module(module_name)
                status_widget = self.get_widget(module_name)
                if status_widget:
                    status_widget.restore_widget_state(module_state)


class FrameStatusBox(QWidget):
    def __init__(self, filename, total_actions):
        super().__init__()
        self.filename = filename
        self.total_actions = total_actions
        self.status_id = -1
        self.border_color = QColor(100, 100, 100)
        self.fill_color = QColor(200, 200, 200)
        self.custom_tooltip = None
        self.enable_doubleclick = False
        self.update_tooltip()
        self.setMinimumSize(20, 15)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

    def set_total_actions(self, filename, total_actions):
        key = os.path.basename(filename)
        widget = self.frame_widgets.get(key)
        if widget is not None:
            widget.set_total_actions(total_actions)

    def update_status(self, status_id):
        pending_color = (200, 200, 200)
        init_color = (253, 251, 212)
        completed_color = (76, 175, 80)
        failed_color = (244, 67, 54)
        preprocess_color = (253, 218, 13)
        postprocess_color = (64, 224, 208)
        unknown_color = (138, 43, 226)
        self.status_id = status_id
        self.enable_doubleclick = status_id == 1000 or status_id >= 200
        if status_id == -1:
            self.fill_color = QColor(*pending_color)
        elif status_id == 1000:
            self.fill_color = QColor(*completed_color)
        elif status_id == 1001:
            self.fill_color = QColor(*failed_color)
        elif self.status_id < 100:
            progress = status_id / 10.0
            rgb = (int(init_color[i] * (1 - progress) + completed_color[i] * progress)
                   for i in range(3))
            self.fill_color = QColor(*rgb)
        elif self.status_id == 100:
            rgb = (int((init_color[i] + preprocess_color[i]) * 0.5) for i in range(3))
            self.fill_color = QColor(*rgb)
        elif self.status_id == 101:
            self.fill_color = QColor(*preprocess_color)
        elif self.status_id == 200:
            rgb = (int((init_color[i] + postprocess_color[i]) * 0.5) for i in range(3))
            self.fill_color = QColor(*rgb)
        elif self.status_id == 201:
            self.fill_color = QColor(*postprocess_color)
        else:
            self.fill_color = QColor(*unknown_color)
        self._update_tooltip_content()
        self.update()

    def update_tooltip(self):
        if self.status_id == -1:
            status_text = "Pending"
        elif self.status_id == 1000:
            status_text = "Completed"
        elif self.status_id == 1001:
            status_text = "Failed"
        elif self.status_id < 100:
            status_text = f"Completed action {self.status_id}/{self.total_actions}"
        elif self.status_id == 100:
            status_text = "Preprocess submitted"
        elif self.status_id == 101:
            status_text = "Preprocess completed"
        elif self.status_id == 200:
            status_text = "Postprocess submitted"
        elif self.status_id == 201:
            status_text = "Postprocess completed"
        else:
            status_text = "Unknown status"
        self.tooltip_text = f"File: {os.path.basename(self.filename)}\nStatus: {status_text}"

    def _update_tooltip_content(self):
        self.update_tooltip()
        if self.custom_tooltip:
            self.custom_tooltip.setText(self.tooltip_text)
            self.custom_tooltip.adjustSize()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        margin = 1
        rect = self.rect().adjusted(margin, margin, -margin, -margin)
        painter.fillRect(rect, self.fill_color)
        painter.setPen(QPen(self.border_color, 1))
        painter.drawRect(rect)

    def enterEvent(self, _event):
        if not self.custom_tooltip:
            self.custom_tooltip = QLabel(self.tooltip_text, self.window())
            self.custom_tooltip.setStyleSheet(f"""
                QLabel {{
                    background-color: #FFFFCC;
                    color: #{ColorPalette.DARK_BLUE.hex()};
                    border: 1px solid black;
                    padding: 2px;
                }}
            """)
            self.custom_tooltip.adjustSize()
        else:
            self.custom_tooltip.setText(self.tooltip_text)
            self.custom_tooltip.adjustSize()
        global_pos = self.mapToGlobal(self.rect().topRight())
        parent_pos = self.window().mapFromGlobal(global_pos)
        self.custom_tooltip.move(parent_pos.x() + 2, parent_pos.y())
        self.custom_tooltip.show()

    def leaveEvent(self, _event):
        if self.custom_tooltip:
            self.custom_tooltip.hide()

    def mouseDoubleClickEvent(self, event):
        if self.enable_doubleclick and self.filename:
            open_file(self.filename, self.parent())
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def capture_widget_state(self):
        return {
            'filename': self.filename,
            'total_actions': self.total_actions,
            'status_id': self.status_id,
        }

    def restore_widget_state(self, state):
        self.filename = state.get('filename', '')
        self.total_actions = state.get('total_actions', 0)
        status_id = state.get('status_id', -1)
        self.update_status(status_id)


class PreprocessingStatusWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setSpacing(4)
        self.grid_layout.setContentsMargins(2, 2, 2, 2)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.frame_widgets = {}
        self.MIN_BOX_WIDTH = 30
        self.MAX_BOX_WIDTH = 60
        self.ASPECT_RATIO = 3.0 / 4.0
        self.current_box_width = self.MAX_BOX_WIDTH
        self.current_box_height = int(self.current_box_width * self.ASPECT_RATIO)
        self._in_resize = False
        self._last_size = -1

    def add_frame(self, filename, total_actions):
        if filename in self.frame_widgets:
            raise RuntimeError(f"Filename {filename} already registered")
        key = os.path.basename(filename)
        self.frame_widgets[key] = FrameStatusBox(filename, total_actions)
        self._update_layout()

    def set_total_actions(self, filename, total_actions):
        key = os.path.basename(filename)
        widget = self.frame_widgets.get(key)
        if widget is not None:
            widget.set_total_actions(total_actions)
        else:
            raise RuntimeError(f"Unknown filename {key}")

    def update_frame_status(self, filename, status_id):
        key = os.path.basename(filename)
        widget = self.frame_widgets.get(key)
        if widget is not None:
            widget.update_status(status_id)

    def resizeEvent(self, event):
        new_size = event.size()
        if self._in_resize:
            super().resizeEvent(event)
            return
        try:
            self._in_resize = True
            super().resizeEvent(event)
            if self._last_size != new_size:
                self._last_size = new_size
                self._update_layout()
        finally:
            self._in_resize = False

    def _calculate_optimal_box_width(self):
        available_width = self.width() - 10
        spacing = self.grid_layout.spacing()
        max_possible_cols = max(1, available_width // (self.MIN_BOX_WIDTH + spacing))
        needed_cols = min(len(self.frame_widgets), max_possible_cols)
        if needed_cols > 0:
            calculated_width = (available_width - (needed_cols - 1) * spacing) // needed_cols
        else:
            calculated_width = 0
        return max(self.MIN_BOX_WIDTH, min(self.MAX_BOX_WIDTH, calculated_width))

    def _update_layout(self):
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                self.grid_layout.removeWidget(widget)
        self.current_box_width = self._calculate_optimal_box_width()
        self.current_box_height = int(self.current_box_width * self.ASPECT_RATIO)
        available_width = self.width() - 10
        spacing = self.grid_layout.spacing()
        max_cols = max(1, available_width // (self.current_box_width + spacing))
        num_cols = min(len(self.frame_widgets), max_cols)
        for _k, widget in self.frame_widgets.items():
            widget.setFixedSize(self.current_box_width, self.current_box_height)
        for i, (_k, widget) in enumerate(self.frame_widgets.items()):
            row = i // num_cols
            col = i % num_cols
            self.grid_layout.addWidget(widget, row, col)
        num_rows = math.ceil(len(self.frame_widgets) / num_cols) if num_cols > 0 else 0
        total_height = num_rows * (self.current_box_height + spacing)
        new_min_height = total_height  # + 10
        if new_min_height != self.minimumHeight():
            self.blockSignals(True)
            self.setMinimumHeight(new_min_height)
            self.blockSignals(False)

    def capture_widget_state(self):
        state = {'frames': []}
        for _filename_key, frame_widget in self.frame_widgets.items():
            frame_state = frame_widget.capture_widget_state()
            state['frames'].append(frame_state)
        return state

    def restore_widget_state(self, state):
        self.frame_widgets.clear()
        for frame_state in state.get('frames', []):
            filename = frame_state.get('filename', '')
            total_actions = frame_state.get('total_actions', 0)
            if filename:
                key = os.path.basename(filename)
                self.frame_widgets[key] = FrameStatusBox(filename, total_actions)
                self.frame_widgets[key].restore_widget_state(frame_state)
        self._update_layout()
