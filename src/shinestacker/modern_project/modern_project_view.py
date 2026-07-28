# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0904, R0913, R0914, R0917, R0912, R0915, E1101
# pylint: disable=R1716, C0302, R0911, R0903, W0718, W0613, R0801, R1702, E1121
import os
import traceback
import warnings
from functools import partial
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QEvent
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QScrollArea
from ..gui.gui_logging import QTextEditLogger
from ..config.constants import constants
from ..common_project.run_worker import JobLogWorker, ProjectLogWorker
from ..common_project.project_view import ProjectView
from ..common_project.selection_state import SelectionState
from .job_widget import JobWidget
from .progress_mapper import ProgressMapper
from .progress_signal_handler import ProgressSignalHandler
from .selection_navigation_manager import SelectionNavigationManager
from .action_widget import ActionWidget
from .sub_action_widget import SubActionWidget


class ModernProjectView(ProjectView):
    update_gui_actions_enable_requested = Signal()
    show_status_message_requested = Signal(str, int)
    run_job_requested = Signal(int)
    run_retouch_job_requested = Signal(int)

    def __init__(self, project, selection_state, dark_theme, parent=None):
        ProjectView.__init__(self, project, selection_state, dark_theme, parent)
        self.job_widgets = []
        self.scroll_area = None
        self.scroll_content = None
        self.project_layout = None
        self.selected_widget = None
        self._user_scrolling = False
        self._scrolling_timer = QTimer()
        self._scrolling_timer.setSingleShot(True)
        self._scrolling_timer.timeout.connect(self._reset_user_scrolling)
        self._scrolling_cooldown = 4000  # 4 seconds
        self.show_status_message = None
        self._worker = None
        self.progress_mapper = ProgressMapper()
        self.actions_layout_horizontal = False
        self.subactions_layout_vertical = False
        self.progress_handler = ProgressSignalHandler(
            self.progress_mapper,
            self._find_widget,
            self._scroll_to_widget
        )
        self.selection_nav = SelectionNavigationManager(
            self.project(),
            self.selection_state,
            self._selection_callback
        )
        self._setup_ui()
        self.set_dark_theme(dark_theme)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

    def _setup_ui(self):
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFocusPolicy(Qt.NoFocus)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_user_scroll)
        self.scroll_content = QWidget()
        self.scroll_content.setFocusPolicy(Qt.NoFocus)
        self.scroll_content.setContentsMargins(2, 2, 2, 2)
        self.project_layout = QVBoxLayout(self.scroll_content)
        self.project_layout.setSpacing(2)
        self.project_layout.setContentsMargins(2, 2, 2, 2)
        self.project_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        main_splitter.addWidget(self.scroll_area)
        self.console_area = QTextEditLogger(self)
        self.add_gui_logger(self.console_area)
        console_layout = QVBoxLayout(self.console_area)
        self.console_area.text_edit.setFocusPolicy(Qt.ClickFocus)
        self.console_area.text_edit.installEventFilter(self)
        console_layout.setContentsMargins(0, 0, 0, 0)
        console_layout.addWidget(self.console_area.text_edit)
        main_splitter.addWidget(self.console_area)
        main_splitter.setSizes([600, 200])
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)
        ico_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                "gui", "ico", "shinestacker.png")
        self.console_area.handle_html_message(
            f"<img width=100 src='{ico_path}'><hr><br>")

    def _on_user_scroll(self, value):
        self._user_scrolling = True
        self._scrolling_timer.start(self._scrolling_cooldown)

    def _reset_user_scrolling(self):
        self._user_scrolling = False

    def _select_widget(self, state):
        if not state or not state.is_valid():
            return
        widget = self._find_widget(state)
        if not widget:
            return
        if self.selected_widget:
            self.selected_widget.set_selected(False)
        widget.set_selected(True)
        self.selected_widget = widget
        self.selection_state.copy_from(state)
        self.update_gui_actions_enable_requested.emit()
        self._ensure_selected_visible()

    def _selection_callback(self, widget_type, job_index, action_index=-1, subaction_index=-1):
        state = SelectionState(job_index, action_index, subaction_index)
        self._select_widget(state)

    def connect_signals(self, update_gui_actions_enable, show_status_message,
                        enable_sub_actions, on_run_job_requested,
                        on_run_retouch_job_requested):
        self.update_gui_actions_enable_requested.connect(update_gui_actions_enable)
        self.show_status_message_requested.connect(show_status_message)
        self.enable_sub_actions_requested.connect(enable_sub_actions)
        self.run_job_requested.connect(on_run_job_requested)
        self.run_retouch_job_requested.connect(on_run_retouch_job_requested)

    def _on_job_run_clicked(self, job_widget):
        job_index = self.job_widgets.index(job_widget)
        self.selection_state.set_indices(job_index)
        self.run_job_requested.emit(job_index)

    def _on_job_retouch_clicked(self, job_widget):
        job_index = self.job_widgets.index(job_widget)
        self.selection_state.set_indices(job_index)
        self.run_retouch_job_requested.emit(job_index)

    # pylint: disable=C0103
    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus()

    def eventFilter(self, obj, event):
        if obj == self.console_area.text_edit and event.type() == event.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right, Qt.Key_Home, Qt.Key_End):
                self.keyPressEvent(event)
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        key = event.key()
        key_map = {
            Qt.Key_Up: "up",
            Qt.Key_Down: "down",
            Qt.Key_Left: "left",
            Qt.Key_Right: "right",
            Qt.Key_Home: "home",
            Qt.Key_End: "end"
        }
        if key in key_map:
            if self.selection_nav.handle_key_navigation(key_map[key]):
                event.accept()
                return
        if key in [Qt.Key_Return, Qt.Key_Enter]:
            self.edit_element_signal.emit()
            event.accept()
        elif key == Qt.Key_Tab:
            super().keyPressEvent(event)
        elif key == Qt.Key_Backtab:
            super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        pos = self.mapFromGlobal(QCursor.pos())
        widget = self.childAt(pos)
        current_action = None
        if widget:
            while widget and widget != self:
                if hasattr(widget, 'data_object'):
                    current_action = widget.data_object
                    break
                widget = widget.parentWidget()
        if not current_action and self.selected_widget:
            current_action = self.selected_widget.data_object
        if current_action:
            menu = self.create_common_context_menu(current_action)
            menu.exec(event.globalPos())
    # pylint: enable=C0103

    def _build_progress_mapping(self, job_indices=None):
        self.progress_mapper.build_mapping(self.project(), job_indices)

    def _find_widget(self, selection):
        if not selection or not selection.is_valid():
            return None
        if not 0 <= selection.job_index < len(self.job_widgets):
            return None
        job_widget = self.job_widgets[selection.job_index]
        if selection.is_job_selected():
            return job_widget
        if not 0 <= selection.action_index < len(job_widget.child_widgets):
            return None
        action_widget = job_widget.child_widgets[selection.action_index]
        if selection.is_action_selected():
            return action_widget
        if not 0 <= selection.subaction_index < len(action_widget.child_widgets):
            return None
        return action_widget.child_widgets[selection.subaction_index]

    def _reset_selection(self):
        self.selected_widget = None
        self.selection_state.reset()

    def clear_job_list(self):
        for widget in self.job_widgets:
            widget.clicked.disconnect()
            widget.deleteLater()
        self.job_widgets.clear()
        if self.project_layout:
            while self.project_layout.count():
                item = self.project_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        self.selection_state.set_indices()
        self.selected_widget = None

    def clear_project(self):
        super().clear_project()
        self.clear_job_list()
        self._reset_selection()
        self.update_gui_actions_enable_requested.emit()

    # pylint: disable=W0212
    def _refresh_job_widget_signals(self):
        signal_types = ["clicked", "double_clicked", "enabled_toggled"]

        def disconnect_signals(widget):
            for signal in signal_types:
                try:
                    signal_obj = getattr(widget, signal)
                    if signal_obj:
                        try:
                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore")
                                signal_obj.disconnect()
                        except TypeError:
                            pass
                except AttributeError:
                    pass

        def connect_widget_signals(widget, widget_type, position):
            widget._slots = {}
            if widget_type == "job":
                job_index = position[0]
                widget._slots["clicked"] = partial(self._on_widget_clicked, widget, job_index)
                widget._slots["double_clicked"] = self.edit_element_signal.emit
            elif widget_type == "action":
                job_index, action_index = position
                widget._slots["clicked"] = partial(
                    self._on_widget_clicked, widget, job_index, action_index)
                widget._slots["double_clicked"] = self.edit_element_signal.emit
            else:
                job_index, action_index, subaction_index = position
                widget._slots["clicked"] = partial(
                    self._on_widget_clicked, widget, job_index, action_index, subaction_index)
                widget._slots["double_clicked"] = self.edit_element_signal.emit
            widget._slots["enabled_toggled"] = self._on_widget_enabled_toggled
            for signal in signal_types:
                getattr(widget, signal).connect(widget._slots[signal])

        for job_index, job_widget in enumerate(self.job_widgets):
            disconnect_signals(job_widget)
            for action_widget in job_widget.child_widgets:
                disconnect_signals(action_widget)
                for subaction_widget in action_widget.child_widgets:
                    disconnect_signals(subaction_widget)
            connect_widget_signals(job_widget, "job", (job_index,))
            for action_index, action_widget in enumerate(job_widget.child_widgets):
                connect_widget_signals(action_widget, "action", (job_index, action_index))
                for subaction_index, subaction_widget in enumerate(action_widget.child_widgets):
                    connect_widget_signals(
                        subaction_widget, "subaction", (job_index, action_index, subaction_index))
    # pylint: enable=W0212

    def select_current(self):
        self._select_widget(self.selection_state)

    def _clear_hover_on_widget(self, widget):
        if widget is None:
            return
        try:
            widget.event(QEvent(QEvent.Type.Leave))
        except RuntimeError:
            pass

    def _on_widget_clicked(self, widget, job_index, action_index=-1, subaction_index=-1):
        if self.selected_widget:
            self.selected_widget.set_selected(False)
        widget.set_selected(True)
        self.selected_widget = widget
        self.selection_state.from_tuple((job_index, action_index, subaction_index))
        self.update_gui_actions_enable_requested.emit()
        element = self.project_element(job_index, action_index, subaction_index)
        self.enable_sub_actions_requested.emit(
            subaction_index >= 0 or element.type_name == constants.ACTION_COMBO)
        self.setFocus()

    def _update_widget(self, selection, element):
        if not selection.is_valid():
            return
        widget = self._find_widget(selection)
        widget.update(element)

    def delete_element(self, old_selection):
        if old_selection:
            self._remove_widget(old_selection)
        if self.selection_state:
            self.selection_nav.restore_selection(self.selection_state)
            self._ensure_selected_visible()
        else:
            self._reset_selection()

    def insert_element(self, old_selection):
        if not old_selection or not old_selection.is_valid():
            return
        try:
            new_widget = self._insert_widget(
                self.selection_state, self.project_element(*self.selection_state.to_tuple()))
            if new_widget:
                if self.selected_widget:
                    self._clear_hover_on_widget(self.selected_widget)
                    self.selected_widget.set_selected(False)
                new_widget.set_selected(True)
                self.selected_widget = new_widget
                self._ensure_selected_visible()
                self.update_gui_actions_enable_requested.emit()
        except Exception:
            self.refresh_ui()

    def set_enabled_all(self):
        for job_widget in self.job_widgets:
            job_widget.update_enabled()
            for action_widget in job_widget.child_widgets:
                action_widget.update_enabled()
                for subaction_widget in action_widget.child_widgets:
                    subaction_widget.update_enabled()

    def _move_widgets(self, from_state, to_state):
        try:
            if from_state.is_job_selected() and to_state.is_job_selected():
                if not (0 <= from_state.job_index < len(self.job_widgets) and
                        0 <= to_state.job_index < len(self.job_widgets)):
                    self.refresh_ui()
                    return
                job_widgets = self.job_widgets
                project_layout = self.project_layout
                project_layout.removeWidget(job_widgets[from_state.job_index])
                project_layout.removeWidget(job_widgets[to_state.job_index])
                a, b = from_state.job_index, to_state.job_index
                job_widgets[a], job_widgets[b] = job_widgets[b], job_widgets[a]
                insert_first = min(a, b)
                insert_second = max(a, b)
                project_layout.insertWidget(insert_first, job_widgets[insert_first])
                project_layout.insertWidget(insert_second, job_widgets[insert_second])
            elif from_state.is_action_selected() and to_state.is_action_selected() and \
                    from_state.job_index == to_state.job_index:
                if not 0 <= from_state.job_index < len(self.job_widgets):
                    self.refresh_ui()
                    return
                job_widget = self.job_widgets[from_state.job_index]
                child_widgets = job_widget.child_widgets
                if not (0 <= from_state.action_index < len(child_widgets) and
                        0 <= to_state.action_index < len(child_widgets)):
                    self.refresh_ui()
                    return
                job_widget.child_container_layout.removeWidget(
                    child_widgets[from_state.action_index])
                job_widget.child_container_layout.removeWidget(
                    child_widgets[to_state.action_index])
                a, b = from_state.action_index, to_state.action_index
                child_widgets[a], child_widgets[b] = child_widgets[b], child_widgets[a]
                insert_first = min(a, b)
                insert_second = max(a, b)
                job_widget.child_container_layout.insertWidget(
                    insert_first, child_widgets[insert_first])
                job_widget.child_container_layout.insertWidget(
                    insert_second, child_widgets[insert_second])
            elif from_state.is_subaction_selected() and to_state.is_subaction_selected() and \
                    from_state.job_index == to_state.job_index and \
                    from_state.action_index == to_state.action_index:
                if not 0 <= from_state.job_index < len(self.job_widgets):
                    self.refresh_ui()
                    return
                job_widget = self.job_widgets[from_state.job_index]
                if not 0 <= from_state.action_index < len(job_widget.child_widgets):
                    self.refresh_ui()
                    return
                action_widget = job_widget.child_widgets[from_state.action_index]
                child_widgets = action_widget.child_widgets
                if not (0 <= from_state.subaction_index < len(child_widgets) and
                        0 <= to_state.subaction_index < len(child_widgets)):
                    self.refresh_ui()
                    return
                action_widget.child_container_layout.removeWidget(
                    child_widgets[from_state.subaction_index])
                action_widget.child_container_layout.removeWidget(
                    child_widgets[to_state.subaction_index])
                a, b = from_state.subaction_index, to_state.subaction_index
                child_widgets[a], child_widgets[b] = child_widgets[b], child_widgets[a]
                insert_first = min(a, b)
                insert_second = max(a, b)
                action_widget.child_container_layout.insertWidget(
                    insert_first, child_widgets[insert_first])
                action_widget.child_container_layout.insertWidget(
                    insert_second, child_widgets[insert_second])
            else:
                self.refresh_ui()
        except Exception:
            self.refresh_ui()

    def shift_element(self, old_selection):
        self._move_widgets(old_selection, self.selection_state)
        self.selection_nav.restore_selection(self.selection_state)
        self._ensure_selected_visible()
        self._refresh_job_widget_signals()

    def set_style_sheet(self, dark_theme):
        pass

    def _on_widget_enabled_toggled(self, enabled):
        widget = self.sender()
        if not widget:
            return
        self.widget_enable_signal.emit(enabled)

    def set_enabled(self, selection):
        widget = self._find_widget(selection)
        if widget:
            widget.update_enabled()

    def _scroll_to_widget(self, widget):
        if not widget or self._user_scrolling:
            return
        if not widget.isVisible() or widget.height() == 0:
            QTimer.singleShot(10, lambda: self._scroll_to_widget(widget))
            return
        viewport_height = self.scroll_area.viewport().height()
        widget_height = widget.height()
        if widget_height <= viewport_height:
            y_margin = (viewport_height - widget_height) // 2
        else:
            y_margin = 0
        self.scroll_area.ensureWidgetVisible(widget, 0, y_margin)

    def _ensure_selected_visible(self):
        self._scroll_to_widget(self.selected_widget)

    def current_job_index(self):
        return self.selection_state.job_index

    def update_added_element(self):
        element = self.project_element(*self.selection_state.to_tuple())
        if element is None:
            return False
        try:
            self._insert_widget(self.selection_state, element)
            self._select_widget(self.selection_state)
            return True
        except Exception:
            pass
        return False

    def update_widget(self, selection):
        if not selection.is_valid():
            return
        widget = self._find_widget(selection)
        if widget is None:
            return
        widget.update()

    def update_widget_recursive(self, selection):
        if not selection.is_valid():
            return
        widget = self._find_widget(selection)
        if widget is None:
            return
        widget.update_recursive()

    def horizontal_actions_layout(self, horizontal=True):
        if self.actions_layout_horizontal != horizontal:
            self.actions_layout_horizontal = horizontal
            for job_widget in self.job_widgets:
                job_widget.set_horizontal_layout(horizontal)
            self.progress_handler.set_horizontal_layout(horizontal)
            txt = "horizontal" if horizontal else "vertical"
            self.vertical_subactions_layout(vertical=horizontal)
            self.show_status_message_requested.emit(f"Actions layout set to {txt}", 2000)

    def vertical_subactions_layout(self, vertical=True):
        if self.subactions_layout_vertical != vertical:
            self.subactions_layout_vertical = vertical
            for job_widget in self.job_widgets:
                for action_widget in job_widget.child_widgets:
                    action_widget.set_horizontal_layout(not vertical)
                    image_horizontal = True  # Always horizontal images
                    for subaction_widget in action_widget.child_widgets:
                        subaction_widget.set_image_orientation(image_horizontal)
                    if vertical:
                        action_widget.child_container_layout.setSpacing(5)
                    else:
                        action_widget.child_container_layout.setSpacing(2)

    def refresh_ui(self, restore_state=None):
        old_state = restore_state if restore_state else self.selection_state.copy()
        self.clear_job_list()
        for job in self.project_jobs():
            self._add_job_widget(job)
        if old_state:
            self.selection_state.copy_from(old_state)
            self.selection_nav.restore_selection(old_state)
            self._ensure_selected_visible()
        ProjectView.refresh_ui(self)

    def _add_job_widget(self, job):
        job_widget = JobWidget(
            job, self.dark_theme, self.actions_layout_horizontal,
            self.subactions_layout_vertical, self._on_job_run_clicked,
            self._on_job_retouch_clicked)
        job_widget.setFocusPolicy(Qt.NoFocus)
        job_index = len(self.job_widgets)
        job_widget.clicked.connect(
            lambda checked=False, w=job_widget, idx=job_index:
                self._on_widget_clicked(w, idx)
        )
        job_widget.double_clicked.connect(self.edit_element_signal.emit)
        job_widget.enabled_toggled.connect(self._on_widget_enabled_toggled)
        self.job_widgets.append(job_widget)
        self.project_layout.addWidget(job_widget)
        for action_idx, action_widget in enumerate(job_widget.child_widgets):
            def make_action_click_handler(job_index, action_index, widget):
                def handler():
                    self._on_widget_clicked(widget, job_index, action_index)
                return handler
            action_widget.clicked.connect(
                make_action_click_handler(job_index, action_idx, action_widget))
            action_widget.double_clicked.connect(self.edit_element_signal.emit)
            action_widget.enabled_toggled.connect(self._on_widget_enabled_toggled)
            for subaction_idx, subaction_widget in enumerate(action_widget.child_widgets):
                def make_subaction_click_handler(job_index, action_index, subaction_index, widget):
                    def handler():
                        self._on_widget_clicked(widget, job_index, action_index, subaction_index)
                    return handler
                subaction_widget.clicked.connect(
                    make_subaction_click_handler(
                        job_index, action_idx, subaction_idx, subaction_widget)
                )
                subaction_widget.double_clicked.connect(self.edit_element_signal.emit)
                subaction_widget.enabled_toggled.connect(self._on_widget_enabled_toggled)
        if len(self.job_widgets) == 1:
            self._on_widget_clicked(job_widget, 0)

    def _safe_disconnect_all(self, widget):
        try:
            if hasattr(widget, 'clicked'):
                widget.clicked.disconnect()
        except Exception:
            pass
        try:
            if hasattr(widget, 'double_clicked'):
                widget.double_clicked.disconnect()
        except Exception:
            pass

    def _remove_widget(self, state):
        if not state.is_valid():
            return False
        try:
            if state.is_job_selected():
                if 0 <= state.job_index < len(self.job_widgets):
                    job_widget = self.job_widgets.pop(state.job_index)
                    self.project_layout.removeWidget(job_widget)
                    if self.selected_widget is job_widget:
                        self.selected_widget = None
                    self._safe_disconnect_all(job_widget)
                    job_widget.deleteLater()
                    self._refresh_job_widget_signals()
                    return True
            elif state.is_action_selected():
                if 0 <= state.job_index < len(self.job_widgets) and \
                        0 <= state.action_index < \
                        len(self.job_widgets[state.job_index].child_widgets):
                    job_widget = self.job_widgets[state.job_index]
                    action_widget = job_widget.child_widgets.pop(state.action_index)
                    job_widget.child_container_layout.removeWidget(action_widget)
                    if self.selected_widget is action_widget:
                        self.selected_widget = None
                    self._safe_disconnect_all(action_widget)
                    action_widget.deleteLater()
                    self._refresh_job_widget_signals()
                    return True
            elif state.is_subaction_selected():
                if 0 <= state.job_index < len(self.job_widgets) and \
                        0 <= state.action_index < len(
                            self.job_widgets[state.job_index].child_widgets):
                    job_widget = self.job_widgets[state.job_index]
                    action_widget = job_widget.child_widgets[state.action_index]
                    if 0 <= state.subaction_index < len(action_widget.child_widgets):
                        subaction_widget = action_widget.child_widgets.pop(state.subaction_index)
                        action_widget.child_container_layout.removeWidget(subaction_widget)
                        if self.selected_widget is subaction_widget:
                            self.selected_widget = None
                        self._safe_disconnect_all(subaction_widget)
                        subaction_widget.deleteLater()
                        self._refresh_job_widget_signals()
                        return True
        except Exception:
            pass
        return False

    def _insert_widget(self, selection, element):
        if not selection.is_valid():
            return None
        inserted_widget = None
        job_index, action_index, subaction_index = selection.to_tuple()
        insert_index, container = -1, None
        if selection.is_job_selected():
            if not 0 <= job_index <= len(self.job_widgets):
                return None
            inserted_widget = JobWidget(
                element, self.dark_theme, self.actions_layout_horizontal,
                self.subactions_layout_vertical, self._on_job_run_clicked,
                self._on_job_retouch_clicked)
            inserted_widget.setFocusPolicy(Qt.NoFocus)
            inserted_widget.clicked.connect(
                lambda: self._on_widget_clicked(inserted_widget, job_index))
            inserted_widget.double_clicked.connect(self.edit_element_signal.emit)
            self.job_widgets.insert(job_index, inserted_widget)
            insert_index, container = job_index, self.project_layout
        elif selection.is_action_selected():
            if not 0 <= job_index < len(self.job_widgets):
                return None
            job_widget = self.job_widgets[job_index]
            if not 0 <= action_index <= len(self.job_widgets[job_index].child_widgets):
                return None
            inserted_widget = ActionWidget(
                element, self.dark_theme, self.subactions_layout_vertical)
            inserted_widget.clicked.connect(
                lambda: self._on_widget_clicked(inserted_widget, job_index, action_index))
            inserted_widget.double_clicked.connect(self.edit_element_signal.emit)
            job_widget.child_widgets.insert(action_index, inserted_widget)
            insert_index, container = action_index, job_widget.child_container_layout
        elif selection.is_subaction_selected():
            if not 0 <= job_index < len(self.job_widgets):
                return None
            job_widget = self.job_widgets[job_index]
            if not 0 <= action_index < len(self.job_widgets[job_index].child_widgets):
                return None
            action_widget = job_widget.child_widgets[action_index]
            if not 0 <= subaction_index <= len(action_widget.child_widgets):
                return None
            inserted_widget = SubActionWidget(
                element, self.dark_theme,
                horizontal_images=not self.subactions_layout_vertical)
            inserted_widget.clicked.connect(lambda: self._on_widget_clicked(
                inserted_widget, job_index, action_index,
                subaction_index))
            inserted_widget.double_clicked.connect(self.edit_element_signal.emit)
            action_widget.child_widgets.insert(subaction_index, inserted_widget)
            insert_index, container = subaction_index, action_widget.child_container_layout
        if inserted_widget:
            container.insertWidget(insert_index, inserted_widget)
            self._refresh_job_widget_signals()
        return inserted_widget

    def has_run_metadata(self):
        return True

    def clear_run_metadata(self):
        for job_widget in self.job_widgets:
            self._clear_widget_metadata(job_widget)

    def _start_job_worker(self, job_index, job):
        self._prepare_job_run_ui(job_index, job)
        self._worker = JobLogWorker(job, self.last_id_str())
        self._connect_worker_signals(self._worker)
        self.start_thread(self._worker)
        return True

    def _start_project_worker(self):
        self._prepare_project_run_ui()
        self._worker = ProjectLogWorker(self.project(), self.last_id_str())
        self._connect_worker_signals(self._worker)
        self.start_thread(self._worker)
        return True

    def _prepare_job_run_ui(self, job_index, job):
        self.job_widgets[job_index].clear_all()
        self._build_progress_mapping([job_index])

    def _prepare_project_run_ui(self):
        for job_widget in self.job_widgets:
            job_widget.clear_all()
        self._build_progress_mapping()

    def stop(self):
        if self._worker:
            self._worker.stop()
            return True
        return False

    def is_running(self):
        return self._worker is not None and self._worker.isRunning()

    def _connect_worker_signals(self, worker):
        self.connect_worker_signals(worker, self.progress_handler)
        worker.run_completed_signal.connect(
            self.handle_run_completed, Qt.ConnectionType.UniqueConnection)
        worker.run_stopped_signal.connect(
            self.handle_run_completed, Qt.ConnectionType.UniqueConnection)
        worker.run_failed_signal.connect(
            self.handle_run_completed, Qt.ConnectionType.UniqueConnection)
        worker.plot_manager.save_plot_signal.connect(self.progress_handler.plot_manager.save_plot)

    def _clear_widget_metadata(self, widget):
        widget.clear_metadata()
        for child in widget.child_widgets:
            self._clear_widget_metadata(child)

    @Slot(int, str)
    def handle_run_completed(self, _run_id, _name):
        self.run_finished_signal.emit()

    def quit(self):
        if self._worker:
            self._worker.stop()
        self.close()
        return True

    def set_dark_theme(self, dark_theme):
        self.dark_theme = dark_theme
        for job_widget in self.job_widgets:
            job_widget.set_dark_theme(dark_theme)

    def select_first_job(self):
        self._select_widget(SelectionState(0, -1, -1))

    def perform_undo(self, entry, old_selection):
        if entry:
            self.targeted_undo(entry)
            self.refresh_existing_widget_references()
            if entry.get('action_type', '') == 'rename':
                self._refresh_widget_recursive(self._find_widget(old_selection))
            old_position = entry.get('old_position', (-1, -1, -1))
            self.selection_nav.restore_selection(SelectionState(*old_position))
        else:
            self.refresh_ui()

    def perform_redo(self, entry, old_selection):
        if entry:
            self.targeted_redo(entry)
            self.refresh_existing_widget_references()
            if entry.get('action_type', '') == 'rename':
                self._refresh_widget_recursive(self._find_widget(old_selection))
            new_position = entry.get('new_position', (-1, -1, -1))
            self.selection_nav.restore_selection(SelectionState(*new_position))
        else:
            self.refresh_ui()

    def refresh_existing_widget_references(self):
        for job_idx, job_widget in enumerate(self.job_widgets):
            if job_idx < self.num_project_jobs():
                job = self.project_job(job_idx)
                job_widget.data_object = job
                for action_idx, action_widget in enumerate(job_widget.child_widgets):
                    if action_idx < len(job.sub_actions):
                        action = job.sub_actions[action_idx]
                        action_widget.data_object = action
                        for subaction_idx, subaction_widget in \
                                enumerate(action_widget.child_widgets):
                            if subaction_idx < len(action.sub_actions):
                                subaction = action.sub_actions[subaction_idx]
                                subaction_widget.data_object = subaction

    def targeted_undo(self, entry):
        action_type = entry.get('action_type', '')
        old_position = entry.get('old_position', (-1, -1, -1))
        new_position = entry.get('new_position', (-1, -1, -1))
        if action_type == 'clone':
            clone_position = SelectionState(*new_position)
            return self._undo_clone_action(clone_position, entry)
        if action_type == 'move':
            from_position = SelectionState(*new_position)
            to_position = SelectionState(*old_position)
            self._undo_move_action(from_position, to_position)
            return True
        if action_type == 'paste':
            original_position = SelectionState(*old_position)
            pasted_position = SelectionState(*new_position)
            return self._undo_paste_action(original_position, pasted_position, entry)
        if action_type == 'edit_all':
            return self._undo_edit_all_action()
        if action_type in ['run', 'run_all', 'clear_run_info']:
            return self._refresh_all_widgets_from_metadata()
        if action_type == 'rename':
            return True
        if action_type == 'add':
            state = SelectionState(*new_position)
            return self._undo_add_action(state, entry)
        if action_type == 'delete':
            state = SelectionState(*old_position)
            return self._insert_widget_for_undo(state, entry)
        if action_type == 'edit':
            state = SelectionState(*old_position)
            return self._undo_edit_action(state)
        self.refresh_ui()
        return False

    def targeted_redo(self, entry):
        action_type = entry.get('action_type', '')
        old_position = entry.get('old_position', (-1, -1, -1))
        new_position = entry.get('new_position', (-1, -1, -1))
        if action_type == 'clone':
            clone_position = SelectionState(*new_position)
            return self._redo_insert_common(clone_position, entry)
        if action_type == 'move':
            from_position = SelectionState(*old_position)
            to_position = SelectionState(*new_position)
            self._move_widgets(from_position, to_position)
            return True
        if action_type == 'paste':
            pasted_position = SelectionState(*new_position)
            return self._insert_widget_for_undo(pasted_position, entry)
        if action_type == 'edit_all':
            return self._undo_edit_all_action()
        if action_type in ['run', 'run_all', 'clear_run_info']:
            return self._refresh_all_widgets_from_metadata()
        if action_type == 'rename':
            return True
        if action_type == 'add':
            state = SelectionState(*new_position)
            return self._insert_widget_for_undo(state, entry)
        if action_type == 'delete':
            state = SelectionState(*old_position)
            return self._redo_delete_action(state)
        if action_type == 'edit':
            state = SelectionState(*new_position)
            return self._undo_edit_action(state)
        self.refresh_ui()
        return False

    def _refresh_widget_recursive(self, widget):
        widget.refresh_from_metadata()
        for sub in widget.child_widgets:
            self._refresh_widget_recursive(sub)
        return True

    def _refresh_all_widgets_from_metadata(self):
        for job_idx, job_widget in enumerate(self.job_widgets):
            if job_idx < len(self.project_jobs()):
                job = self.project_job(job_idx)
                job_widget.data_object = job
                job_widget.refresh_from_metadata()
                for action_idx, action_widget in enumerate(job_widget.child_widgets):
                    if action_idx < len(job.sub_actions):
                        action = job.sub_actions[action_idx]
                        action_widget.data_object = action
                        action_widget.refresh_from_metadata()
                        for subaction_idx, subaction_widget \
                                in enumerate(action_widget.child_widgets):
                            if subaction_idx < len(action.sub_actions):
                                subaction = action.sub_actions[subaction_idx]
                                subaction_widget.data_object = subaction
                                subaction_widget.refresh_from_metadata()
        return True

    def _remove_widget_for_undo(self, selection, entry=None):
        try:
            self._remove_widget(selection)
            self._refresh_job_widget_signals()
            self.update_gui_actions_enable_requested.emit()
            return True
        except Exception:
            self.refresh_ui()
            return False

    def _insert_widget_for_undo(self, selection, entry):
        if not selection.is_valid():
            return True
        position = selection.to_tuple()
        try:
            if not self.valid_indices(*position):
                return True
            element = self.project_element(*position)
            if not element:
                return True
            self._insert_widget(selection, element)
            widget = self._find_widget(selection)
            if widget:
                if self.selected_widget:
                    self._clear_hover_on_widget(self.selected_widget)
                    self.selected_widget.set_selected(False)
                widget.set_selected(True)
                self.selected_widget = widget
                self.selection_state.copy_from(selection)
            self._refresh_job_widget_signals()
            self.update_gui_actions_enable_requested.emit()
            self._select_widget(selection)
            return True
        except Exception:
            traceback.print_exc()
            self.refresh_ui()
            return False

    def _undo_edit_action(self, selection):
        position = selection.to_tuple()
        try:
            if not self.valid_indices(*position):
                return True
            element = self.project_element(*position)
            if element:
                self._update_widget(selection, element)
            return True
        except Exception:
            self.refresh_ui()
            return False

    def _undo_move_action(self, from_position, to_position):
        self._move_widgets(from_position, to_position)
        return True

    def _undo_edit_all_action(self):
        for job_idx, job_widget in enumerate(self.job_widgets):
            if job_idx < len(self.project_jobs()):
                job = self.project_job(job_idx)
                job_widget.data_object = job
                job_widget.update()
                for action_idx, action_widget in enumerate(job_widget.child_widgets):
                    if action_idx < len(job.sub_actions):
                        action = job.sub_actions[action_idx]
                        action_widget.data_object = action
                        action_widget.update()
                        for subaction_idx, subaction_widget \
                                in enumerate(action_widget.child_widgets):
                            if subaction_idx < len(action.sub_actions):
                                subaction = action.sub_actions[subaction_idx]
                                subaction_widget.data_object = subaction
                                subaction_widget.update()
        return True

    def _undo_add_action(self, selection, entry):
        return self._remove_widget_for_undo(selection, entry)

    def _undo_clone_action(self, selection, entry):
        return self._remove_widget_for_undo(selection, entry)

    def _undo_paste_action(self, original_position, pasted_position, entry):
        return self._remove_widget_for_undo(pasted_position, entry)

    def _redo_delete_action(self, selection):
        return self._remove_widget_for_undo(selection, None)

    def _redo_insert_common(self, selection, entry):
        return self._insert_widget_for_undo(selection, entry)
