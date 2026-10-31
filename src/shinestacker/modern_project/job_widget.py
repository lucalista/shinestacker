# pylint: disable=E0611, R0903, R0913, R0917
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton
from ..gui.project_model import get_action_input_path
from ..config.constants import constants
from ..gui.colors import ColorPalette
from .base_widget import BaseWidget
from .action_widget import ActionWidget


class JobWidget(BaseWidget):
    retouch_clicked_signal = Signal(object)
    run_clicked_signal = Signal(object)

    def __init__(self, job, dark_theme=False, horizontal_layout=False,
                 vertical_subactions=False, handle_run_clicked=None,
                 handle_retouch_clicked=None, parent=None):
        self.run_button = QPushButton()
        self.run_button.setToolTip("Run this job")
        self.run_button.clicked.connect(lambda: self.run_clicked_signal.emit(self))
        self.retouch_button = QPushButton()
        self.retouch_button.setToolTip("Retouch outputs")
        self.retouch_button.clicked.connect(lambda: self.retouch_clicked_signal.emit(self))
        super().__init__(job, 50, dark_theme, horizontal_layout, 2, parent)
        self.run_button.setFixedSize(self.icon_size, self.icon_size)
        self.retouch_button.setFixedSize(self.icon_size, self.icon_size)
        self._update_icons()
        in_path = get_action_input_path(job)[0]
        self._add_path_label(f"📁 {self._format_path(in_path)}")
        if hasattr(job, 'sub_actions') and job.sub_actions:
            for action in job.sub_actions:
                action_widget = ActionWidget(action, dark_theme, vertical_subactions)
                self.add_child_widget(action_widget, add_to_layout=True)
        self.icons_layout.insertWidget(0, self.retouch_button)
        self.icons_layout.insertWidget(1, self.run_button)
        self._update_button_style()
        self.retouch_button.setVisible(self._should_show_retouch_button())
        if handle_retouch_clicked:
            self.retouch_clicked_signal.connect(handle_retouch_clicked)
        self.run_clicked_signal.connect(handle_run_clicked)

    def update(self, data_object=None):
        super().update(data_object)
        self.retouch_button.setVisible(self._should_show_retouch_button())
        self._update_button_style()

    def update_path_label(self):
        in_path = get_action_input_path(self.data_object)[0]
        path_text = f"📁 <i>{self._format_path(in_path)}</i>"
        self._add_path_label(path_text)

    def set_dark_theme(self, dark_theme):
        super().set_dark_theme(dark_theme)
        self._update_button_style()

    def widget_type(self):
        return 'JobWidget'

    def _update_icons(self):
        super()._update_icons()
        self.set_button_icon(self.retouch_button, "paint-small-icon")
        self.set_button_icon(self.run_button, "play-button-small-icon")

    def _update_button_style(self):
        if self.dark_theme:
            color = ColorPalette.LIGHT_BLUE.hex()
        else:
            color = ColorPalette.DARK_BLUE.hex()
        style = f"""
            QPushButton {{
                color: #{color};
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
                font-size: 14px;
            }}
            QPushButton:hover {{
                color: #{ColorPalette.MEDIUM_BLUE.hex()};
            }}
        """
        self.run_button.setStyleSheet(style)
        self.retouch_button.setStyleSheet(style)

    def _should_show_retouch_button(self):
        job = self.data_object
        if not hasattr(job, 'sub_actions'):
            return False
        for action in job.sub_actions:
            if action.type_name in [constants.ACTION_COMBO,
                                    constants.ACTION_FOCUSSTACK,
                                    constants.ACTION_FOCUSSTACKBUNCH]:
                return True
        return False
