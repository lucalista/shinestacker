# pylint: disable=C0114, C0115, C0116, R0904, E0611, R0902, W0201, R0913, R0917
from functools import partial
from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QAction, QKeySequence, QActionGroup
from PySide6.QtWidgets import QMenu, QComboBox
from ..config.constants import constants
from ..config.app_config import AppConfig
from ..gui.recent_file_manager import RecentFileManager
from ..gui.icon_manager import IconManager


class MenuManager(QObject, IconManager):
    open_file_requested = Signal(str)

    def __init__(self, menubar, actions, toggle_fullscreen, add_action, add_subaction,
                 dark_theme, parent):
        IconManager.__init__(self, dark_theme)
        QObject.__init__(self, parent)
        self._recent_file_manager = RecentFileManager("shinestacker-recent-project-files.txt")
        self.toggle_fullscreen = toggle_fullscreen
        self.add_action = add_action
        self.add_subaction = add_subaction
        self.dark_theme = dark_theme
        self.parent = parent
        self.menubar = menubar
        self.actions = actions
        self.action_selector = None
        self.subaction_selector = None
        self.shortcuts = {
            "&New...": "Ctrl+N",
            "&Open...": "Ctrl+O",
            "Open Project As Template": "Ctrl+T",
            "&Close": "Ctrl+W",
            "&Save": "Ctrl+S",
            "Save &As...": "Ctrl+Shift+S",
            "&Undo": "Ctrl+Z",
            "&Redo": [QKeySequence("Ctrl+Shift+Z"), QKeySequence("Ctrl+Y")],
            "&Cut": "Ctrl+X",
            "Cop&y": "Ctrl+C",
            "&Paste": "Ctrl+V",
            "Duplicate": "Ctrl+K",
            "Delete": [QKeySequence("Backspace"), QKeySequence("Del")],
            "Move &Up": [QKeySequence("Ctrl+Shift+Up"), QKeySequence("Ctrl+Shift+Left")],
            "Move &Down": [QKeySequence("Ctrl+Shift+Down"), QKeySequence("Ctrl+Shift+Right")],
            "E&nable": "Ctrl+E",
            "Di&sable": "Ctrl+D",
            "Enable All": "Ctrl+Shift+E",
            "Disable All": "Ctrl+Shift+D",
            "Expert Options": "Ctrl+Shift+X",
            "Edit Parameters": "Ctrl+Enter",
            "Rename": "Ctrl+M",
            "Modern Horizontal": "Ctrl+1",
            "Modern Vertical": "Ctrl+2",
            "Classic View": "Ctrl+3",
            "Add Job": "Ctrl+J",
            "Run Job": "Ctrl+R",
            "Run All Jobs": "Ctrl+Shift+R",
            "Stop": "Ctrl+.",
            "Clear Run Information": "Ctrl+Shift+L",
            "Clear Project Outputs": "Ctrl+Shift+O"
        }
        self.icons = {
            "Delete": "close-round-line-icon",
            "Add Job": "plus-round-line-icon",
            "Run Job": "play-button-round-icon",
            "Run All Jobs": "forward-button-icon",
            "Stop": "stop-button-round-icon",
            "Retouch Job Output": "paint-round-icon"
        }
        self.tooltips = {
            "Delete": "Delete selected element",
            "Add Job": "Add job",
            "Run Job": "Run selected job",
            "Run All Jobs": "Run all jobs",
            "Stop": "Stop run",
            "Retouch Job Output": "Retouch job output"
        }

    def action(self, name, requires_file=False):
        action = QAction(name, self.parent)
        if requires_file:
            action.setProperty("requires_file", True)
        shortcut = self.shortcuts.get(name, '')
        if shortcut:
            if isinstance(shortcut, str):
                action.setShortcut(shortcut)
            elif isinstance(shortcut, list):
                action.setShortcuts(shortcut)
        icon_name = self.icons.get(name, '')
        if icon_name:
            action.setIcon(self.get_icon(icon_name))
            action.setProperty('theme_dependent', True)
            action.setProperty('base_icon_name', icon_name)
        tooltip = self.tooltips.get(name, '')
        if tooltip:
            action.setToolTip(tooltip)
        action_fun = self.actions.get(name, None)
        if action_fun is not None:
            action.triggered.connect(action_fun)
        return action

    def update_recent_files(self):
        self.recent_files_menu.clear()
        recent_files = self._recent_file_manager.get_files_with_display_names()
        for file_path, display_name in recent_files.items():
            action = self.recent_files_menu.addAction(display_name)
            action.setData(file_path)
            action.triggered.connect(partial(self.open_file_requested.emit, file_path))
        self.recent_files_menu.setEnabled(len(recent_files) > 0)

    def add_recent_file(self, file_path):
        self._recent_file_manager.add_file(file_path)
        self.update_recent_files()

    def add_file_menu(self):
        menu = self.menubar.addMenu("&File")
        for name in ["&New...", "&Open..."]:
            menu.addAction(self.action(name))
        self.recent_files_menu = QMenu("Open &Recent", menu)
        menu.addMenu(self.recent_files_menu)
        self.update_recent_files()
        menu.addAction(self.action("Open Project As Template"))
        menu.addAction(self.action("&Close"))
        menu.addSeparator()
        self.save_action = self.action("&Save")
        menu.addAction(self.save_action)
        self.save_as_action = self.action("Save &As...")
        menu.addAction(self.save_as_action)
        self.save_actions_set_enabled(False)

    def add_edit_menu(self):
        menu = self.menubar.addMenu("&Edit")
        self.undo_action = self.action("&Undo")
        self.undo_action.setEnabled(False)
        menu.addAction(self.undo_action)
        self.redo_action = self.action("&Redo")
        self.redo_action.setEnabled(False)
        menu.addAction(self.redo_action)
        self.cut_action = self.action("&Cut", requires_file=True)
        menu.addAction(self.cut_action)
        self.copy_action = self.action("Cop&y", requires_file=True)
        menu.addAction(self.copy_action)
        self.paste_action = self.action("&Paste", requires_file=True)
        menu.addAction(self.paste_action)
        self.duplicate_action = self.action("Duplicate", requires_file=True)
        menu.addAction(self.duplicate_action)
        self.delete_element_action = self.action("Delete", requires_file=True)
        self.delete_element_action.setEnabled(False)
        menu.addAction(self.delete_element_action)
        menu.addSeparator()
        for name in ["Move &Up", "Move &Down"]:
            menu.addAction(self.action(name, requires_file=True))
        menu.addSeparator()
        self.edit_element_action = self.action("Edit Parameters", requires_file=True)
        menu.addAction(self.edit_element_action)
        self.rename_action = self.action("Rename", requires_file=True)
        menu.addAction(self.rename_action)
        menu.addSeparator()
        self.enable_action = self.action("E&nable", requires_file=True)
        menu.addAction(self.enable_action)
        self.disable_action = self.action("Di&sable", requires_file=True)
        menu.addAction(self.disable_action)
        for name in ["Enable All", "Disable All"]:
            menu.addAction(self.action(name, requires_file=True))

    def add_view_menu(self):
        menu = self.menubar.addMenu("&View")
        fullscreen_action = QAction("Full Screen", self)
        fullscreen_action.setShortcuts([QKeySequence("Ctrl+Meta+F"), QKeySequence("F11")])
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        fullscreen_action.setCheckable(True)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        menu.addAction(fullscreen_action)
        menu.addSeparator()
        self.expert_options_action = self.action("Expert Options")
        self.expert_options_action.setCheckable(True)
        self.expert_options_action.setChecked(AppConfig.get('expert_options'))
        menu.addAction(self.expert_options_action)
        menu.addSeparator()
        view_group = QActionGroup(self.parent)
        view_group.setExclusive(True)
        self.modern_horizontal_action = QAction("Modern Horizontal", self.parent)
        self.modern_horizontal_action.setCheckable(True)
        self.modern_horizontal_action.setShortcut("Ctrl+1")
        self.modern_horizontal_action.triggered.connect(
            lambda: self.parent.set_view('modern_horizontal'))
        view_group.addAction(self.modern_horizontal_action)
        menu.addAction(self.modern_horizontal_action)
        self.modern_vertical_action = QAction("Modern Vertical", self.parent)
        self.modern_vertical_action.setCheckable(True)
        self.modern_vertical_action.setShortcut("Ctrl+2")
        self.modern_vertical_action.triggered.connect(
            lambda: self.parent.set_view('modern_vertical'))
        view_group.addAction(self.modern_vertical_action)
        menu.addAction(self.modern_vertical_action)
        self.classic_view_action = QAction("Classic View", self.parent)
        self.classic_view_action.setCheckable(True)
        self.classic_view_action.setShortcut("Ctrl+3")
        self.classic_view_action.triggered.connect(lambda: self.parent.set_view('classic'))
        view_group.addAction(self.classic_view_action)
        menu.addAction(self.classic_view_action)

    def set_modern_layout(self, action_name):
        if action_name == 'Horizontal Layout':
            self.horizontal_layout_action.setChecked(True)
            self.horizontal_layout_action.setEnabled(False)
            self.vertical_layout_action.setChecked(False)
            self.vertical_layout_action.setEnabled(True)
        elif action_name == 'Vertical Layout':
            self.vertical_layout_action.setChecked(True)
            self.vertical_layout_action.setEnabled(False)
            self.horizontal_layout_action.setChecked(False)
            self.horizontal_layout_action.setEnabled(True)
        action_func = self.actions.get(action_name)
        if action_func:
            action_func()

    def set_view(self, mode):
        actions = {
            'classic': self.classic_view_action,
            'modern_horizontal': self.modern_horizontal_action,
            'modern_vertical': self.modern_vertical_action
        }
        for key, action in actions.items():
            is_current = key == mode
            action.setChecked(is_current)
            action.setEnabled(not is_current)

    def add_job_menu(self):
        menu = self.menubar.addMenu("&Jobs")
        self.add_job_action = self.action("Add Job")
        menu.addAction(self.add_job_action)
        menu.addSeparator()
        self.run_job_action = self.action("Run Job", requires_file=True)
        self.run_job_action.setEnabled(False)
        menu.addAction(self.run_job_action)
        self.run_all_jobs_action = self.action("Run All Jobs", requires_file=True)
        self.set_enabled_run_all_jobs(False)
        menu.addAction(self.run_all_jobs_action)
        self.stop_action = self.action("Stop", requires_file=True)
        self.stop_action.setEnabled(False)
        menu.addAction(self.stop_action)
        menu.addSeparator()
        self.clear_run_info_action = self.action("Clear Run Information", requires_file=True)
        menu.addAction(self.clear_run_info_action)
        self.clear_project_images = self.action("Clear Project Outputs", requires_file=True)
        menu.addAction(self.clear_project_images)
        menu.addSeparator()
        self.run_retouch_selected_job_action = self.action("Retouch Job Output", requires_file=True)
        menu.addAction(self.run_retouch_selected_job_action)

    def add_actions_menu(self):
        menu = self.menubar.addMenu("&Actions")
        add_action_menu = QMenu("Add Action", self.parent)
        for action in constants.ACTION_TYPES:
            entry_action = QAction(action, self.parent)
            entry_action.setProperty("requires_file", True)
            entry_action.triggered.connect({
                constants.ACTION_COMBO: self.add_action_combined_actions,
                constants.ACTION_NOISEDETECTION: self.add_action_noise_detection,
                constants.ACTION_FOCUSSTACK: self.add_action_focus_stack,
                constants.ACTION_FOCUSSTACKBUNCH: self.add_action_focus_stack_bunch,
                constants.ACTION_MULTILAYER: self.add_action_multilayer
            }[action])
            add_action_menu.addAction(entry_action)
        menu.addMenu(add_action_menu)
        add_subaction_menu = QMenu("Add Sub Action", self.parent)
        self.subaction_menu_entries = []
        for action in constants.SUB_ACTION_TYPES:
            entry_action = QAction(action, self.parent)
            entry_action.setProperty("requires_file", True)
            entry_action.triggered.connect({
                constants.ACTION_MASKNOISE: self.add_subaction_make_noise,
                constants.ACTION_VIGNETTING: self.add_subaction_vignetting,
                constants.ACTION_ALIGNFRAMES: self.add_subaction_align_frames,
                constants.ACTION_BALANCEFRAMES: self.add_subaction_balance_frames
            }[action])
            entry_action.setEnabled(False)
            self.subaction_menu_entries.append(entry_action)
            add_subaction_menu.addAction(entry_action)
        menu.addMenu(add_subaction_menu)

    def add_help_menu(self):
        menu = self.menubar.addMenu("&Help")
        menu.setObjectName("Help")

    def add_menus(self):
        self.add_file_menu()
        self.add_edit_menu()
        self.add_view_menu()
        self.add_job_menu()
        self.add_actions_menu()
        self.add_help_menu()

    def handle_fill_context_menu(self, menu, enabled):
        menu.addAction(self.edit_element_action)
        menu.addAction(self.rename_action)
        menu.addSeparator()
        if enabled:
            menu.addAction(self.disable_action)
        else:
            menu.addAction(self.enable_action)
        menu.addSeparator()
        menu.addAction(self.cut_action)
        menu.addAction(self.copy_action)
        menu.addAction(self.paste_action)
        menu.addAction(self.duplicate_action)
        menu.addAction(self.delete_element_action)
        menu.addSeparator()
        menu.addAction(self.run_job_action)
        menu.addAction(self.run_all_jobs_action)

    def perform_add_action(self):
        type_name = self.action_selector.currentText()
        if self.add_action(type_name):
            self.delete_element_action.setEnabled(False)

    def perform_add_subaction(self):
        type_name = self.subaction_selector.currentText()
        self.add_subaction(type_name)

    def save_actions_set_enabled(self, enabled):
        self.save_action.setEnabled(enabled)
        self.save_as_action.setEnabled(enabled)

    def add_action_combined_actions(self):
        self.add_action(constants.ACTION_COMBO)

    def add_action_noise_detection(self):
        self.add_action(constants.ACTION_NOISEDETECTION)

    def add_action_focus_stack(self):
        self.add_action(constants.ACTION_FOCUSSTACK)

    def add_action_focus_stack_bunch(self):
        self.add_action(constants.ACTION_FOCUSSTACKBUNCH)

    def add_action_multilayer(self):
        self.add_action(constants.ACTION_MULTILAYER)

    def add_subaction_make_noise(self):
        self.add_subaction(constants.ACTION_MASKNOISE)

    def add_subaction_vignetting(self):
        self.add_subaction(constants.ACTION_VIGNETTING)

    def add_subaction_align_frames(self):
        self.add_subaction(constants.ACTION_ALIGNFRAMES)

    def add_subaction_balance_frames(self):
        self.add_subaction(constants.ACTION_BALANCEFRAMES)

    def fill_toolbar(self, toolbar):
        toolbar.addAction(self.add_job_action)
        toolbar.addSeparator()
        self.action_selector = QComboBox()
        self.action_selector.addItems(constants.ACTION_TYPES)
        self.action_selector.setEnabled(False)
        toolbar.addWidget(self.action_selector)
        self.add_action_entry_action = QAction("Add Action", self.parent)
        self.add_action_entry_action.setIcon(
            self.get_icon("plus-round-line-icon"))
        self.add_action_entry_action.setToolTip("Add action")
        self.add_action_entry_action.triggered.connect(self.perform_add_action)
        self.add_action_entry_action.setEnabled(False)
        toolbar.addAction(self.add_action_entry_action)
        self.subaction_selector = QComboBox()
        self.subaction_selector.addItems(constants.SUB_ACTION_TYPES)
        self.subaction_selector.setEnabled(False)
        toolbar.addWidget(self.subaction_selector)
        self.add_subaction_entry_action = QAction("Add Sub Action", self.parent)
        self.add_subaction_entry_action.setIcon(
            self.get_icon("plus-round-line-icon"))
        self.add_subaction_entry_action.setToolTip("Add sub action")
        self.add_subaction_entry_action.triggered.connect(self.perform_add_subaction)
        self.add_subaction_entry_action.setEnabled(False)
        toolbar.addAction(self.add_subaction_entry_action)
        toolbar.addSeparator()
        toolbar.addAction(self.delete_element_action)
        toolbar.addSeparator()
        toolbar.addAction(self.run_job_action)
        toolbar.addAction(self.run_all_jobs_action)
        toolbar.addAction(self.stop_action)
        toolbar.addAction(self.run_retouch_selected_job_action)

    def set_enabled_subactions_gui(self, enabled):
        self.add_subaction_entry_action.setEnabled(enabled)
        self.subaction_selector.setEnabled(enabled)
        for a in self.subaction_menu_entries:
            a.setEnabled(enabled)

    def set_enabled_run_all_jobs(self, enabled):
        tooltip = self.tooltips["Run All Jobs"]
        self.run_all_jobs_action.setEnabled(enabled)
        if not enabled:
            tooltip = "Run all jobs (requires more than one job)"
        else:
            tooltip = "Run all jobs"
        self.run_all_jobs_action.setToolTip(tooltip)

    def set_enabled_undo_action(self, enabled, description):
        self.undo_action.setEnabled(enabled)
        self.undo_action.setText(f"&Undo {description}")

    def set_enabled_redo_action(self, enabled, description):
        self.redo_action.setEnabled(enabled)
        self.redo_action.setText(f"&Redo {description}")
