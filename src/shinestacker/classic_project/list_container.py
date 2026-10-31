# pylint: disable=E0611, R0903, R0904, R0913, R0917, E1101, R0911, R0902
import os
from PySide6.QtCore import Qt, QEvent, QSize, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QLabel, QSizePolicy
from .. config.constants import constants
from .. gui.colors import ColorPalette
from .. gui.project_model import get_action_input_path, get_action_output_path
from .. common_project.selection_state import SelectionState


class HandCursorListWidget(QListWidget):
    arrow_key_pressed = Signal(str)
    enter_key_pressed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setWordWrap(False)

    def event(self, event):
        if event.type() == QEvent.HoverMove:
            pos = event.position().toPoint()
            item = self.itemAt(pos)
            if item:
                self.viewport().setCursor(Qt.PointingHandCursor)
            else:
                self.viewport().setCursor(Qt.ArrowCursor)
        elif event.type() == QEvent.Leave:
            self.viewport().setCursor(Qt.ArrowCursor)
        return super().event(event)

    # pylint: disable=C0103
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.enter_key_pressed.emit()
            event.accept()
        if event.key() == Qt.Key_Right:
            self.arrow_key_pressed.emit("right")
            event.accept()
        elif event.key() == Qt.Key_Left:
            self.arrow_key_pressed.emit("left")
            event.accept()
        else:
            super().keyPressEvent(event)
    # pylint: enable=C0103


def get_action_row(selection_state, actions):
    if not (selection_state.is_action_selected() or selection_state.is_subaction_selected()):
        return -1
    if not actions or not 0 <= selection_state.action_index < len(actions):
        return -1
    row = -1
    for i, action in enumerate(actions):
        row += 1
        if i == selection_state.action_index:
            if selection_state.is_subaction_selected():
                row += selection_state.subaction_index + 1
            return row
        row += len(getattr(action, 'sub_actions', []))
    return -1


class ListContainer:
    INDENT_SPACE = "&nbsp;&nbsp;&nbsp;↪&nbsp;&nbsp;&nbsp;"

    def __init__(self, dark_theme, job_list=False, action_list=False):
        self._job_list = HandCursorListWidget() if job_list is False else job_list
        self._action_list = HandCursorListWidget() if action_list is False else action_list
        self._job_list.setFocusPolicy(Qt.StrongFocus)
        self._action_list.setFocusPolicy(Qt.StrongFocus)
        self._job_list.arrow_key_pressed.connect(self.handle_arrow_key)
        self._action_list.arrow_key_pressed.connect(self.handle_arrow_key)
        self._job_list.itemClicked.connect(self.update_focus_styles)
        self._action_list.itemClicked.connect(self.update_focus_styles)
        self._focused_style_light = f"""
            QListWidget::item:selected {{
                background-color: #{ColorPalette.LIGHT_BLUE.hex()};
            }}
            QListWidget::item:hover {{
                background-color: #F0F0F0;
            }}
        """
        self._focused_style_dark = f"""
            QListWidget::item:selected {{
                background-color: #{ColorPalette.DARK_BLUE.hex()};
            }}
            QListWidget::item:hover {{
                background-color: #303030;
            }}
        """
        self._unfocused_style_light = """
            QListWidget::item:hover {
                background-color: #F0F0F0;
            }
        """
        self._unfocused_style_dark = """
            QListWidget::item:hover {
                background-color: #303030;
            }
        """
        self.set_style_sheet(dark_theme)

    def set_style_sheet(self, dark_theme):
        self._current_focused_style = self._focused_style_dark if dark_theme \
            else self._focused_style_light
        self._current_unfocused_style = self._unfocused_style_dark if dark_theme \
            else self._unfocused_style_light
        self.update_focus_styles()

    def update_focus_styles(self):
        if not hasattr(self, '_current_focused_style'):
            return
        if self._job_list.hasFocus():
            self._job_list.setStyleSheet(self._current_focused_style)
            self._action_list.setStyleSheet(self._current_unfocused_style)
        elif self._action_list.hasFocus():
            self._action_list.setStyleSheet(self._current_focused_style)
            self._job_list.setStyleSheet(self._current_unfocused_style)
        else:
            self._job_list.setStyleSheet(self._current_unfocused_style)
            self._action_list.setStyleSheet(self._current_unfocused_style)

    def handle_arrow_key(self, direction):
        if direction == "right" and self.sender() == self._job_list:
            if self._action_list.count() > 0:
                self._action_list.setCurrentRow(0)
            self._action_list.setFocus()
            self.update_focus_styles()
        elif direction == "left" and self.sender() == self._action_list:
            current_job = self.current_job_index()
            if current_job >= 0:
                self._job_list.setCurrentRow(current_job)
            self._job_list.setFocus()
            self.update_focus_styles()

    def job_list(self):
        return self._job_list

    def action_list(self):
        return self._action_list

    def current_job_index(self):
        return self._job_list.currentRow()

    def current_action_index(self):
        return self._action_list.currentRow()

    def set_current_job(self, index):
        self._job_list.setCurrentRow(index)

    def set_current_action(self, index):
        self._action_list.setCurrentRow(index)

    def job_list_has_focus(self):
        return self._job_list.hasFocus()

    def action_list_has_focus(self):
        return self._action_list.hasFocus()

    def clear_job_list(self):
        self._job_list.clear()

    def clear_action_list(self):
        self._action_list.clear()

    def num_selected_jobs(self):
        return len(self._job_list.selectedItems())

    def num_selected_actions(self):
        return len(self._action_list.selectedItems())

    def get_current_action(self):
        return self.get_action_at(self.current_action_index())

    def job_text(self, job, long_name=False, html=False):
        txt = f"{job.params.get('name', '(job)')}"
        if html:
            txt = f"<b>{txt}</b>"
        in_path = get_action_input_path(job)[0]
        if os.path.isabs(in_path):
            in_path = ".../" + os.path.basename(in_path)
        ico = constants.ACTION_ICONS[constants.ACTION_JOB]
        return txt + (f" [{ico}Job] - 📁 {in_path} → 📂 ..." if long_name else "")

    def action_text(self, action, is_sub_action=False, indent=True, long_name=False, html=False):
        ico = constants.ACTION_ICONS.get(action.type_name, '')
        if is_sub_action and indent:
            txt = self.INDENT_SPACE
        else:
            txt = ''
        if action.params.get('name', '') != '':
            txt += f"{action.params['name']}"
            if html:
                txt = f"<b>{txt}</b>"
        in_path, out_path = get_action_input_path(action)[0], get_action_output_path(action)[0]
        if os.path.isabs(in_path):
            in_path = ".../" + os.path.basename(in_path)
        if os.path.isabs(out_path):
            out_path = ".../" + os.path.basename(out_path)
        return f"{txt} [{ico}{action.type_name}]" + \
               (f" - 📁 <i>{in_path}</i> → 📂 <i>{out_path}</i>"
                if long_name and not is_sub_action else "")

    def add_list_item(self, widget_list, action, is_sub_action, position=None):
        if action.type_name == constants.ACTION_JOB:
            text = self.job_text(action, long_name=True, html=True)
        else:
            text = self.action_text(action, long_name=True, html=True, is_sub_action=is_sub_action)
        item = QListWidgetItem()
        item.setText('')
        item.setToolTip(
            "<b>Double-click:</b> configure parameters<br>"
            "<b>Right-click:</b> show menu")
        item.setData(Qt.ItemDataRole.UserRole, True)
        if position is None:
            widget_list.addItem(item)
        else:
            widget_list.insertItem(position, item)
        html_text = ("✅ " if action.enabled() else "🚫 ") + text
        label = QLabel(html_text)
        label.setProperty("color-type", "enabled" if action.enabled() else "disabled")
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(False)
        label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        label.adjustSize()
        ideal_width = label.sizeHint().width()
        widget_list.setItemWidget(item, label)
        item.setSizeHint(QSize(ideal_width, label.sizeHint().height()))
        widget_list.setItemWidget(item, label)

    def on_job_selected(self, index):
        self.clear_action_list()
        if 0 <= index < self.num_project_jobs():
            job = self.project_job(index)
            position = 0
            for action in job.sub_actions:
                self.add_list_item(self.action_list(), action, False, position)
                position += 1
                if len(action.sub_actions) > 0:
                    for sub_action in action.sub_actions:
                        self.add_list_item(self.action_list(), sub_action, True, position)
                        position += 1

    def get_action_at(self, action_row):
        job_row = self.current_job_index()
        if job_row < 0 or action_row < 0:
            return (job_row, action_row, None)
        action, _sub_action, subaction_index = self.find_action_position(job_row, action_row)
        if not action:
            return (job_row, action_row, None)
        job = self.project_job(job_row)
        state = SelectionState(job_row, job.sub_actions.index(action), subaction_index)
        return (job_row, action_row, state)

    def find_action_position(self, job_index, ui_index):
        if not 0 <= job_index < self.num_project_jobs():
            return (None, None, -1)
        actions = self.project_job(job_index).sub_actions
        counter = -1
        for action in actions:
            counter += 1
            if counter == ui_index:
                return (action, None, -1)
            for subaction_index, sub_action in enumerate(action.sub_actions):
                counter += 1
                if counter == ui_index:
                    return (action, sub_action, subaction_index)
        return (None, None, -1)
