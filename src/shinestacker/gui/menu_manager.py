# pylint: disable=C0114, C0115, C0116, R0904, E0611, R0902, W0201
import os
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QComboBox
from .. config.constants import constants


class MenuManager:
    def __init__(self, menubar, actions, project_editor, parent):
        self.script_dir = os.path.dirname(__file__)
        self.project_editor = project_editor
        self.parent = parent
        self.menubar = menubar
        self.actions = actions
        self.action_selector = None
        self.sub_action_selector = None
        self.shortcuts = {
            "&New...": "Ctrl+N",
            "&Open...": "Ctrl+O",
            "&Close": "Ctrl+W",
            "&Save": "Ctrl+S",
            "Save &As...": "Ctrl+Shift+S",
            "&Undo": "Ctrl+Z",
            "&Cut": "Ctrl+X",
            "Cop&y": "Ctrl+C",
            "&Paste": "Ctrl+V",
            "Duplicate": "Ctrl+D",
            "Delete": "Del",
            "Move &Up": "Ctrl+Up",
            "Move &Down": "Ctrl+Down",
            "E&nable": "Ctrl+E",
            "Di&sable": "Ctrl+B",
            "Enable All": "Ctrl+Shift+E",
            "Disable All": "Ctrl+Shift+B",
            "Expert Options": "Ctrl+Shift+X",
            "Add Job": "Ctrl+P",
            "Run Job": "Ctrl+J",
            "Run All Jobs": "Ctrl+Shift+J"
        }
        self.icons = {
            "Delete": "close-round-line-icon",
            "Add Job": "plus-round-line-icon",
            "Run Job": "play-button-round-icon",
            "Run All Jobs": "forward-button-icon",
        }
        self.tooltips = {
            "Delete": "Delete",
            "Add Job": "Add job",
            "Run Job": "Run job",
            "Run All Jobs": "Run all jobs",
        }

    def get_icon(self, icon):
        return QIcon(os.path.join(self.script_dir, f"img/{icon}.png"))

    def action(self, name):
        action = QAction(name, self.parent)
        shortcut = self.shortcuts.get(name, '')
        if shortcut:
            action.setShortcut(shortcut)
        icon = self.icons.get(name, '')
        if icon:
            action.setIcon(self.get_icon(icon))
        tooltip = self.tooltips.get(name, '')
        if tooltip:
            action.setToolTip(tooltip)
        action_fun = self.actions.get(name, None)
        if action_fun is not None:
            action.triggered.connect(action_fun)
        return action

    def add_file_menu(self):
        menu = self.menubar.addMenu("&File")
        for name in ["&New...", "&Open...", "&Close"]:
            menu.addAction(self.action(name))
        menu.addSeparator()
        self.save_action = self.action("&Save")
        menu.addAction(self.save_action)
        self.save_as_action = self.action("Save &As...")
        menu.addAction(self.save_as_action)
        self.save_actions_set_enabled(False)

    def add_edit_menu(self):
        menu = self.menubar.addMenu("&Edit")
        for name in ["&Undo", "&Cut", "Cop&y", "&Paste", "Duplicate"]:
            menu.addAction(self.action(name))
        self.delete_element_action = self.action("Delete")
        self.delete_element_action.setEnabled(False)
        menu.addAction(self.delete_element_action)
        menu.addSeparator()
        for name in ["Move &Up", "Move &Down"]:
            menu.addAction(self.action(name))
        menu.addSeparator()
        self.enable_action = self.action("E&nable")
        menu.addAction(self.enable_action)
        self.disable_action = self.action("Di&sable")
        menu.addAction(self.disable_action)
        for name in ["Enable All", "Disable All"]:
            menu.addAction(self.action(name))

    def add_view_menu(self):
        menu = self.menubar.addMenu("&View")
        self.expert_options_action = self.action("Expert Options")
        self.expert_options_action.setCheckable(True)
        menu.addAction(self.expert_options_action)

    def add_job_menu(self):
        menu = self.menubar.addMenu("&Jobs")
        self.add_job_action = self.action("Add Job")
        menu.addAction(self.add_job_action)
        menu.addSeparator()
        self.run_job_action = self.action("Run Job")
        self.run_job_action.setEnabled(False)
        menu.addAction(self.run_job_action)
        self.run_all_jobs_action = self.action("Run All Jobs")
        self.run_all_jobs_action.setEnabled(False)
        menu.addAction(self.run_all_jobs_action)

    def add_actions_menu(self):
        menu = self.menubar.addMenu("&Actions")
        add_action_menu = QMenu("Add Action", self.parent)
        for action in constants.ACTION_TYPES:
            entry_action = QAction(action, self.parent)
            entry_action.triggered.connect({
                constants.ACTION_COMBO: self.add_action_combined_actions,
                constants.ACTION_NOISEDETECTION: self.add_action_noise_detection,
                constants.ACTION_FOCUSSTACK: self.add_action_focus_stack,
                constants.ACTION_FOCUSSTACKBUNCH: self.add_action_focus_stack_bunch,
                constants.ACTION_MULTILAYER: self.add_action_multilayer
            }[action])
            add_action_menu.addAction(entry_action)
        menu.addMenu(add_action_menu)
        add_sub_action_menu = QMenu("Add Sub Action", self.parent)
        self.sub_action_menu_entries = []
        for action in constants.SUB_ACTION_TYPES:
            entry_action = QAction(action, self.parent)
            entry_action.triggered.connect({
                constants.ACTION_MASKNOISE: self.add_sub_action_make_noise,
                constants.ACTION_VIGNETTING: self.add_sub_action_vignetting,
                constants.ACTION_ALIGNFRAMES: self.add_sub_action_align_frames,
                constants.ACTION_BALANCEFRAMES: self.add_sub_action_balance_frames
            }[action])
            entry_action.setEnabled(False)
            self.sub_action_menu_entries.append(entry_action)
            add_sub_action_menu.addAction(entry_action)
        menu.addMenu(add_sub_action_menu)

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

    def add_action(self, type_name=False):
        if type_name is False:
            type_name = self.action_selector.currentText()
        self.project_editor.add_action(type_name)

    def add_sub_action(self, type_name=False):
        if type_name is False:
            type_name = self.sub_action_selector.currentText()
        self.project_editor.add_sub_action(type_name)

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

    def add_sub_action_make_noise(self):
        self.add_sub_action(constants.ACTION_MASKNOISE)

    def add_sub_action_vignetting(self):
        self.add_sub_action(constants.ACTION_VIGNETTING)

    def add_sub_action_align_frames(self):
        self.add_sub_action(constants.ACTION_ALIGNFRAMES)

    def add_sub_action_balance_frames(self):
        self.add_sub_action(constants.ACTION_BALANCEFRAMES)

    def fill_toolbar(self, toolbar):
        toolbar.addAction(self.add_job_action)
        toolbar.addSeparator()
        self.action_selector = QComboBox()
        self.action_selector.addItems(constants.ACTION_TYPES)
        self.action_selector.setEnabled(False)
        toolbar.addWidget(self.action_selector)
        self.add_action_entry_action = QAction("Add Action", self.parent)
        self.add_action_entry_action.setIcon(
            QIcon(os.path.join(self.script_dir, "img/plus-round-line-icon.png")))
        self.add_action_entry_action.setToolTip("Add action")
        self.add_action_entry_action.triggered.connect(self.add_action)
        self.add_action_entry_action.setEnabled(False)
        toolbar.addAction(self.add_action_entry_action)
        self.sub_action_selector = QComboBox()
        self.sub_action_selector.addItems(constants.SUB_ACTION_TYPES)
        self.sub_action_selector.setEnabled(False)
        toolbar.addWidget(self.sub_action_selector)
        self.add_sub_action_entry_action = QAction("Add Sub Action", self.parent)
        self.add_sub_action_entry_action.setIcon(
            QIcon(os.path.join(self.script_dir, "img/plus-round-line-icon.png")))
        self.add_sub_action_entry_action.setToolTip("Add sub action")
        self.add_sub_action_entry_action.triggered.connect(self.add_sub_action)
        self.add_sub_action_entry_action.setEnabled(False)
        toolbar.addAction(self.add_sub_action_entry_action)
        toolbar.addSeparator()
        toolbar.addAction(self.delete_element_action)
        toolbar.addSeparator()
        toolbar.addAction(self.run_job_action)
        toolbar.addAction(self.run_all_jobs_action)

    def set_enabled_sub_actions_gui(self, enabled):
        self.add_sub_action_entry_action.setEnabled(enabled)
        self.sub_action_selector.setEnabled(enabled)
        for a in self.sub_action_menu_entries:
            a.setEnabled(enabled)
