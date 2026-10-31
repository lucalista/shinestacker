# pylint: disable=R0903, R0902, R0915
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSizePolicy, QSpacerItem
from .base_widget import ImgBaseWidget
from .sub_action_widget import SubActionWidget
from .. gui.project_model import get_action_input_path, get_action_output_path
from .. gui.time_progress_bar import TimerProgressBar
from .. common_project.processing_widget import MultiModuleStatusContainer


class ActionWidget(ImgBaseWidget):
    def __init__(self, action, dark_theme=False, vertical_subactions=False, parent=None):
        self._has_frames_content = False
        self._pending_frames_state = None
        self.progress_bar = TimerProgressBar()
        self.progress_bar.setVisible(False)
        super().__init__(action, 50, dark_theme, not vertical_subactions, 1, parent,
                         horizontal_images=True)
        self.vertical_subactions = vertical_subactions
        self.progress_container = QWidget()
        self.progress_layout = QVBoxLayout(self.progress_container)
        self.progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_layout.setSpacing(5)
        self.frames_status_box = MultiModuleStatusContainer(classic_view=False)
        self.frames_status_box.setVisible(False)
        self.frames_status_box.content_size_changed.connect(self._update_container_size)
        self.progress_layout.addWidget(self.frames_status_box)
        self.scroll_areas_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.image_scroll_area.verticalScrollBar().setEnabled(False)
        self.progress_layout.addWidget(self.scroll_areas_container)
        while self.child_container_layout.count():
            self.child_container_layout.takeAt(0)
        self.main_layout.addWidget(self.progress_container)
        spacer = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.main_layout.addSpacerItem(spacer)
        self.progress_bar_container = QWidget()
        self.progress_bar_layout = QHBoxLayout(self.progress_bar_container)
        self.progress_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_bar_layout.addWidget(self.progress_bar)
        self.main_layout.addWidget(self.progress_bar_container)
        in_path = get_action_input_path(action)[0]
        out_path = get_action_output_path(action)[0]
        path_text = f"📁 <i>{self._format_path(in_path)}</i> → " \
                    f"📂 <i>{self._format_path(out_path)}</i>"
        self._add_path_label(path_text)
        for sub_action in action.sub_actions:
            sub_action_widget = SubActionWidget(
                sub_action, dark_theme, horizontal_images=vertical_subactions)
            self.add_child_widget(sub_action_widget, add_to_layout=True, can_update=False)
        if self._pending_frames_state is not None:
            self.frames_status_box.restore_widget_state(self._pending_frames_state)
            if self._pending_frames_state.get('modules'):
                self._has_frames_content = True
                self.frames_status_box.setVisible(True)
            self._pending_frames_state = None
        QTimer.singleShot(0, self._check_and_adjust_layout)

    def _adjust_scroll_after_layout(self):
        self.image_area_widget.adjustSize()
        scrollbar = self.image_scroll_area.horizontalScrollBar()
        if scrollbar.maximum() > 0:
            scrollbar.setValue(scrollbar.maximum())

    def add_image_view(self, image_view, tag="_default", can_update=True):
        super().add_image_view(image_view, tag, can_update)
        QTimer.singleShot(0, self._adjust_scroll_after_layout)

    def _update_container_size(self):
        pass

    def widget_type(self):
        return 'ActionWidget'

    def update_path_label(self):
        in_path = get_action_input_path(self.data_object)[0]
        out_path = get_action_output_path(self.data_object)[0]
        path_text = f"📁 <i>{self._format_path(in_path)}</i> → " \
            f"📂 <i>{self._format_path(out_path)}</i>"
        self._add_path_label(path_text)

    def show_progress(self, total_steps):
        self.progress_bar.setVisible(True)
        self.progress_bar.start(total_steps)
        if self._has_frames_content:
            self.frames_status_box.setVisible(True)
        self.update_metadata()

    def update_progress(self, current_step):
        self.progress_bar.setValue(current_step)
        self.update_metadata()

    def run_progress(self):
        self.progress_bar.run()
        self.update_metadata()

    def done_progress(self):
        self.progress_bar.done()
        self.update_metadata()

    def stop_progress(self):
        self.progress_bar.stop()
        self.update_metadata()

    def fail_progress(self):
        self.progress_bar.fail()
        self.update_metadata()

    def hide_progress(self):
        self.progress_bar.clear()
        self.progress_bar.setVisible(False)
        if not self._has_frames_content:
            self.frames_status_box.setVisible(False)
        self.update_metadata()

    def add_status_box(self, module_name):
        self.frames_status_box.setVisible(True)
        self.frames_status_box.add_module(module_name)
        self._has_frames_content = True
        self.update_metadata()

    def add_frame(self, module_name, filename, total_actions):
        self.frames_status_box.setVisible(True)
        self.frames_status_box.add_frame(module_name, filename, total_actions)
        self._has_frames_content = True
        self.update_metadata()

    def update_frame_status(self, module_name, filename, status_id):
        self.frames_status_box.update_frame_status(module_name, filename, status_id)
        self.update_metadata()

    def set_frame_total_actions(self, module_name, filename, total_actions):
        self.frames_status_box.set_frame_total_actions(module_name, filename, total_actions)
        self.update_metadata()

    def clear_frames_status(self):
        self.frames_status_box.clear()
        self.frames_status_box.setVisible(False)
        self._has_frames_content = False
        self.update_metadata()

    def clear_all(self):
        self.clear_frames_status()
        self.frames_status_box.clear()
        self.frames_status_box.setVisible(False)
        self.progress_bar.clear()
        self.progress_bar.setVisible(False)
        super().clear_all()
        self.update_metadata()

    def _capture_widget_state(self):
        state = super()._capture_widget_state()
        if self._has_frames_content:
            state['frames_status'] = self.frames_status_box.capture_widget_state()
        if self.progress_bar and self.progress_bar.isVisible():
            state['progress_bar'] = self.progress_bar.capture_widget_state()
        return state

    def _restore_widget_state(self, state):
        super()._restore_widget_state(state)
        if 'frames_status' in state:
            if hasattr(self, 'frames_status_box') and self.frames_status_box:
                self.frames_status_box.restore_widget_state(state['frames_status'])
                if state['frames_status'].get('modules'):
                    self._has_frames_content = True
                    self.frames_status_box.setVisible(True)
            else:
                self._pending_frames_state = state['frames_status']
        if 'progress_bar' in state:
            self.progress_bar.restore_widget_state(state['progress_bar'])

    def clear_metadata(self):
        self.clear_frames_status()
        self.hide_progress()
        super().clear_metadata()

    def refresh_from_metadata(self):
        self.frames_status_box.clear()
        self.frames_status_box.setVisible(False)
        self._has_frames_content = False
        self.progress_bar.clear()
        self.progress_bar.setVisible(False)
        super().refresh_from_metadata()
