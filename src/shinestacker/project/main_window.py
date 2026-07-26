# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0915, R0904, R0914
# pylint: disable=R0912, E1101, W0201, E1121, R0913, R0917, W0718, R1702
import os
import traceback
import json
import jsonpickle
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QAction, QPalette
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QToolBar, QMainWindow, QApplication, QStackedWidget, QMessageBox,
    QFileDialog)
from ..config.constants import constants
from ..config.app_config import AppConfig
from ..core.exceptions import InvalidProjectError
from ..core.core_utils import get_app_base_path
from ..gui.folder_file_selection import SessionFileDialog
from ..gui.project_model import Project, get_retouch_path
from ..gui.sys_mon import StatusBarSystemMonitor
from ..gui.action_config_dialog import ActionConfigDialog
from ..common_project.project_handler import ProjectHandler
from ..common_project.selection_state import SelectionState
from ..classic_project.classic_project_view import ClassicProjectView
from ..modern_project.modern_project_view import ModernProjectView
from .menu_manager import MenuManager
from .project_undo_manager import ProjectUndoManager
from .element_action_manager import ElementActionManager
from .new_project import fill_new_project
from .clear_images import clear_project_images


CURRENT_PROJECT_FILE_VERSION = 1


class MainWindow(ProjectHandler, QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self._undo_manager = ProjectUndoManager()
        self._project = Project()
        ProjectHandler.__init__(self, self._project)
        self.setObjectName("mainWindow")
        dark_theme = self.is_dark_theme()
        self.selection_state = SelectionState()
        self.element_action = ElementActionManager(
            self._project, self._undo_manager, self.selection_state, self)
        self.classic_view = ClassicProjectView(
            self._project, self.selection_state, dark_theme, self)
        self.modern_view = ModernProjectView(
            self._project, self.selection_state, dark_theme, self)
        self.views = {
            'classic': self.classic_view,
            'modern': self.modern_view
        }
        self.current_view = self.classic_view
        self.view_idx = {'classic': 0, 'modern': 1}
        saved_mode = AppConfig.get('project_view_strategy')
        if saved_mode == 'modern':
            saved_mode = 'modern_horizontal'
        if saved_mode not in ['classic', 'modern_horizontal', 'modern_vertical']:
            saved_mode = 'modern_horizontal'
        self.current_mode = saved_mode
        actions = {
            "&New...": self.new_project,
            "&Open...": self.open_project,
            "Open Project As Template": self.open_template,
            "&Close": self.close_project,
            "&Save": self.save_project,
            "Save &As...": self.save_project_as,
            "&Undo": self.perform_undo,
            "&Redo": self.perform_redo,
            "&Cut": self.cut_element,
            "Cop&y": self.copy_element,
            "&Paste": self.paste_element,
            "Duplicate": self.clone_element,
            "Delete": self.delete_element,
            "Move &Up": self.move_element_up,
            "Move &Down": self.move_element_down,
            "E&nable": self.enable,
            "Di&sable": self.disable,
            "Enable All": self.enable_all,
            "Disable All": self.disable_all,
            "Edit Parameters": self.edit_element,
            "Rename": self.rename,
            "Expert Options": self.toggle_expert_options,
            "Add Job": self.add_job,
            "Run Job": self.run_job,
            "Run All Jobs": self.run_all_jobs,
            "Retouch Job Output": self.run_retouch_selected_job,
            "Stop": self.stop,
            "Classic View": lambda: self.set_view('classic'),
            "Modern Horizontal": lambda: self.set_view('modern_horizontal'),
            "Modern Vertical": lambda: self.set_view('modern_vertical'),
            "Clear Run Information": self.clear_run_metadata,
            "Clear Project Outputs": self.clear_project_images,
        }
        self.menu_manager = MenuManager(
            self.menuBar(), actions, self.toggle_fullscreen, self.add_action, self.add_subaction,
            dark_theme, self)
        self.classic_view.connect_signals(
            self.update_gui_actions_enable,
            self.menu_manager.set_enabled_subactions_gui,
            self.edit_element)
        self.modern_view.connect_signals(
            self.update_gui_actions_enable,
            self.show_status_message,
            self.menu_manager.set_enabled_subactions_gui,
            self.run_job,
            self.run_retouch_selected_job)
        signal_map = [
            ('widget_enable_signal', self.set_enabled),
            ('widget_updated_signal', self.handle_widget_updated),
            ('run_finished_signal', self.handle_run_finished),
            ('fill_context_menu_signal', self.menu_manager.handle_fill_context_menu),
            ('refresh_ui_signal', self.refresh_ui),
            ('edit_element_signal', self.edit_element)
        ]
        for view in self.views.values():
            for signal_name, handler in signal_map:
                if hasattr(view, signal_name):
                    getattr(view, signal_name).connect(handler)
        self.element_action.project_modified_signal.connect(
            self.menu_manager.save_actions_set_enabled)
        self.script_dir = os.path.dirname(__file__)
        self.retouch_callback = None
        for _k, v in self.views.items():
            v.set_style_sheet(dark_theme)
        self.menu_manager.add_menus()
        toolbar = QToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        self.menu_manager.fill_toolbar(toolbar)
        self.resize(1200, 800)
        self.move(QGuiApplication.primaryScreen().geometry().center() -
                  self.rect().center())
        self.set_project(Project())
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.view_stack = QStackedWidget()
        for _k, v in self.views.items():
            self.view_stack.addWidget(v)
        self.view_stack.setCurrentIndex(0)
        self.view_stack.currentChanged.connect(self.on_view_changed)
        layout.addWidget(self.view_stack)
        self.central_widget.setLayout(layout)
        self.update_title()
        self.statusBar().addPermanentWidget(StatusBarSystemMonitor(self))
        QApplication.instance().paletteChanged.connect(self.on_theme_changed)
        self._undo_manager.set_enabled_undo_action_requested.connect(
            self.menu_manager.set_enabled_undo_action)
        self._undo_manager.set_enabled_redo_action_requested.connect(
            self.menu_manager.set_enabled_redo_action)
        self.menu_manager.open_file_requested.connect(self.open_project)
        self.set_enabled_file_open_close_actions(False)
        self.show_status_message("Shine Stacker ready.", 4000)
        self.set_view(self.current_mode)
        self.action_dialog = None
        self.file_dialog = SessionFileDialog(AppConfig.get('input_folder_path'), self)

    def toggle_fullscreen(self, checked):
        if checked:
            self.window().showFullScreen()
        else:
            self.window().showNormal()

    def reset_project(self):
        self.set_project(Project())
        self.element_action.mark_as_not_modified()
        self.element_action.current_file_path = ''
        self._undo_manager.reset()

    def on_view_changed(self, index):
        current_widget = self.view_stack.widget(index)
        if current_widget == self.classic_view:
            self.classic_view.update_focus_styles()
        elif current_widget == self.modern_view:
            self.modern_view.update_focus_styles()

    def show_status_message(self, message, timeout=4000):
        self.statusBar().showMessage(message, timeout)

    def set_retouch_callback(self, callback):
        self.retouch_callback = callback

    def update_title(self):
        title = constants.APP_TITLE
        file_name = self.element_action.current_file_name()
        if file_name:
            title += f" - {file_name}"
            if self.element_action.modified:
                title += " *"
        self.window().setWindowTitle(title)

    def refresh_ui(self):
        self.update_title()
        if self.num_project_jobs() == 0:
            self.menu_manager.add_action_entry_action.setEnabled(False)
            self.menu_manager.action_selector.setEnabled(False)
            self.menu_manager.run_job_action.setEnabled(False)
        else:
            self.menu_manager.add_action_entry_action.setEnabled(True)
            self.menu_manager.action_selector.setEnabled(True)
            self.menu_manager.delete_element_action.setEnabled(True)
            self.menu_manager.run_job_action.setEnabled(True)
        self.menu_manager.set_enabled_run_all_jobs(self.num_project_jobs() > 1)

    def set_view(self, mode):
        base_mode = 'classic' if mode == 'classic' else 'modern'
        target_idx = self.view_idx[base_mode]
        if self.view_stack.currentIndex() != target_idx:
            if self.current_view.is_running():
                reply = QMessageBox.warning(
                    self,
                    "Stop Run Warning",
                    "Switching view will stop the current run. Are you sure?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    self.menu_manager.set_view(self.current_mode)
                    return
                self.current_view.stop()
            self.view_stack.setCurrentIndex(target_idx)
            self.current_view = self.view_stack.currentWidget()
        if base_mode == 'modern':
            horizontal = mode == 'modern_horizontal'
            self.modern_view.horizontal_actions_layout(horizontal)
        self.current_mode = mode
        self.menu_manager.set_view(mode)
        self.menu_manager.clear_run_info_action.setEnabled(self.current_view.has_run_metadata())
        self.current_view.select_current()
        AppConfig.set('project_view_strategy', mode)

    def horizontal_actions_layout(self):
        self.modern_view.horizontal_actions_layout(True)

    def vertical_actions_layout(self):
        self.modern_view.horizontal_actions_layout(False)

    def quit(self):
        self.close_project()
        q = True
        for _k, v in self.views.items():
            q = q and v.quit()
        return q

    def refresh_ui_and_select_first_job(self):
        for _k, v in self.views.items():
            v.refresh_ui()
            v.select_first_job()

    def check_unsaved_changes(self):
        if self.element_action.modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "The project has unsaved changes. Do you want to continue?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self.save_project()
                return True
            return reply == QMessageBox.Discard
        return True

    def open_project_core(self, file_path):
        abs_file_path = os.path.abspath(file_path)
        with open(abs_file_path, 'r', encoding="utf-8") as file:
            json_obj = json.load(file)
        project = Project.from_dict(json_obj['project'], json_obj['version'])
        if project is None:
            raise InvalidProjectError(file_path)
        self.set_project(project)
        self.element_action.set_current_file_path(file_path)
        self.element_action.mark_as_not_modified()
        self._undo_manager.reset()
        return abs_file_path

    def open_project_base(self, file_path):
        if not self.check_unsaved_changes():
            return False, '', ''
        if file_path is False:
            file_path, _ = self.file_dialog.open_file(
                "Open Project", "Project Files (*.fsp *.FSP);;All Files (*)")
        if file_path:
            try:
                self.open_project_core(file_path)
                return True, file_path, ''
            except InvalidProjectError as e:
                QMessageBox.critical(self, "Error", str(e))
                return False, file_path, str(e)
            except Exception as e:
                traceback.print_exc()
                msg = f"Cannot open file {file_path}:\n{str(e)}"
                QMessageBox.critical(self, "Error", msg)
                return False, file_path, msg
        return False, '', ''

    def open_project(self, file_path=False):
        opened, file_path, msg = self.open_project_base(file_path)
        if opened:
            for view in self.views.values():
                view.set_current_file_name(os.path.basename(file_path))
            self.refresh_ui_and_select_first_job()
            self.menu_manager.save_actions_set_enabled(True)
            self.show_status_message(f"Project file {os.path.basename(file_path)} loaded.")
            self.menu_manager.add_recent_file(os.path.abspath(file_path))
            self.set_enabled_file_open_close_actions(True)
            if self.num_project_jobs() > 0:
                self.current_view.select_first_job()
                self.activateWindow()
            for job in self.project_jobs():
                if 'working_path' in job.params.keys():
                    working_path = job.params['working_path']
                    if not os.path.isdir(working_path):
                        msg = "Working path not found"
                        QMessageBox.warning(
                            self, msg,
                            f'''The working path specified in the project file for the job:
                                "{job.params['name']}"
                                was not found.\n
                                Please, select a valid working path.''')
                        self.action_dialog = ActionConfigDialog(
                            job, self.element_action.current_file_directory(), self)
                        self.action_dialog.exec()
                for action in job.sub_actions:
                    if 'working_path' in job.params.keys():
                        working_path = job.params['working_path']
                        if working_path != '' and not os.path.isdir(working_path):
                            msg = "Working path not found"
                            QMessageBox.warning(
                                self, msg,
                                f'''The working path specified in the project file for the job:
                                "{job.params['name']}"
                                was not found.\n
                                Please, select a valid working path.''')
                            self.action_dialog = ActionConfigDialog(
                                action, self.element_action.current_file_directory(), self)
                            self.action_dialog.exec()
        elif msg != '':
            self.show_status_message(msg)

    def open_template(self):
        self.close_project()
        self.open_project()
        jobs = self.project_jobs()
        for job_index, job in enumerate(jobs):
            self.selection_state.set_indices(job_index)
            old_input_path = os.path.basename(job.params['input_path'])
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Select Input Folder")
            msg.setText(f"Please now select your input folder for job {job.params['name']}")
            msg.setStandardButtons(QMessageBox.Ok)
            if msg.exec_() != QMessageBox.Ok:
                self.close_project()
                return
            new_input_path = self.element_action.open_job_browse_folder_dialog()
            if not new_input_path:
                QMessageBox.warning(self, "Operation Aborted",
                                    "No folder selected. Template operation cancelled.")
                self.close_project()
                return
            working_path = job.params['working_path']
            par_strings = {'output_path': 'output path', 'exif_path': 'EXIF files path'}
            for action in job.sub_actions:
                name = action.params['name']
                if old_input_path and name.startswith(old_input_path):
                    name = new_input_path + name[len(old_input_path):]
                else:
                    name = f"{new_input_path}-{name}"
                action.params['name'] = name
                for param_name in ['output_path', 'exif_path']:
                    if param_name in action.params and action.params[param_name]:
                        msg = QMessageBox(self)
                        msg.setIcon(QMessageBox.Information)
                        msg.setWindowTitle(f"Select {par_strings[param_name]}")
                        msg.setText(f"Please now select your {par_strings[param_name]} "
                                    f"for action {action.params['name']}")
                        msg.setStandardButtons(QMessageBox.Ok)
                        if msg.exec_() != QMessageBox.Ok:
                            continue
                        selected_path = QFileDialog.getExistingDirectory(
                            self, f"Select {par_strings[param_name]} folder", working_path)
                        if selected_path:
                            if os.path.commonpath([working_path, selected_path]) == working_path:
                                rel_path = os.path.relpath(selected_path, working_path)
                                action.params[param_name] = rel_path
                            else:
                                QMessageBox.warning(self, "Invalid Selection",
                                                    f"Selected path must be within {working_path}")
            for view in self.views.values():
                view.update_widget_recursive(self.selection_state)
        self.selection_state.set_indices()
        self.show_status_message("New project from template.")

    def new_project(self, path=None):
        if self.check_unsaved_changes():
            os.chdir(get_app_base_path())
            self.reset_project()
            self.update_title()
            if fill_new_project(self.project(), self, initial_path=path):
                self.element_action.mark_as_modified()
                for view in self.views.values():
                    view.clear_project()
            self.refresh_ui_and_select_first_job()
            self.menu_manager.save_actions_set_enabled(True)
            self.set_enabled_file_open_close_actions(True)
            self.show_status_message("New project created.")

    def close_project(self):
        if self.check_unsaved_changes():
            self.clear_project_images()
            self.reset_project()
            self.update_title()
            for _k, v in self.views.items():
                v.clear_project()
            self.set_enabled_file_open_close_actions(False)
            self.menu_manager.run_retouch_selected_job_action.setEnabled(False)
            self.refresh_ui()
            self.show_status_message("Project closed.")

    def do_save_core(self, file_path):
        json_obj = jsonpickle.encode({
            'project': self.project().to_dict(),
            'version': CURRENT_PROJECT_FILE_VERSION
        })
        with open(file_path, 'w', encoding="utf-8") as f:
            f.write(json_obj)
        self.element_action.mark_as_not_modified()

    def do_save(self, file_path):
        try:
            self.do_save_core(file_path)
            self.update_title()
            self.show_status_message(f"Project file {os.path.basename(file_path)} saved.")
            self.menu_manager.add_recent_file(file_path)
        except Exception as e:
            msg = f"Cannot save file:\n{str(e)}"
            self.show_status_message(msg)
            QMessageBox.critical(self, "Error", msg)

    def save_project(self):
        path = self.element_action.current_file_path
        if path:
            self.do_save(path)
        else:
            self.save_project_as()

    def save_project_as(self):
        file_path, _ = self.file_dialog.save_file(
            "Save Project As", "Project Files (*.fsp *.FSP);;All Files (*)",
            self.element_action.current_file_path)
        if file_path:
            if not file_path.endswith('.fsp'):
                file_path += '.fsp'
            self.do_save(file_path)
            self.element_action.set_current_file_path(file_path)
            self.update_title()
            os.chdir(os.path.dirname(file_path))

    def handle_config(self):
        self.menu_manager.expert_options_action.setChecked(
            AppConfig.get('expert_options'))

    def toggle_expert_options(self):
        AppConfig.set('expert_options', self.menu_manager.expert_options_action.isChecked())

    def before_thread_begins(self):
        self.menu_manager.run_job_action.setEnabled(False)
        self.menu_manager.run_all_jobs_action.setEnabled(False)

    def on_job_count_changed(self):
        job_count = self.num_project_jobs()
        self.menu_manager.set_enabled_run_all_jobs(job_count > 1)
        self.menu_manager.run_job_action.setEnabled(job_count > 0)
        self.menu_manager.action_selector.setEnabled(job_count > 0)
        self.menu_manager.add_action_entry_action.setEnabled(job_count > 0)

    def perform_undo(self):
        if not self.current_view.enforce_stop_run():
            return
        old_selection = self.selection_state.copy()
        entry = self.element_action.perform_undo()
        if entry:
            for view in self.views.values():
                view.perform_undo(entry, old_selection)
            if entry.get('action_type') == 'clear_run_info':
                self.menu_manager.clear_run_info_action.setEnabled(True)
            self.update_title()
            self.show_status_message("Undo performed")

    def perform_redo(self):
        if not self.current_view.enforce_stop_run():
            return
        old_selection = self.selection_state.copy()
        entry = self.element_action.perform_redo()
        if entry:
            for view in self.views.values():
                view.perform_redo(entry, old_selection)
            if entry.get('action_type') == 'clear_run_info':
                self.menu_manager.clear_run_info_action.setEnabled(True)
            self.update_title()
            self.show_status_message("Redo performed")

    def add_job(self):
        if not self.current_view.enforce_stop_run():
            return
        if self.element_action.add_job():
            for view in self.views.values():
                view.update_added_element()

    def add_action(self, type_name):
        if not self.current_view.enforce_stop_run():
            return
        if self.element_action.add_action(type_name):
            for view in self.views.values():
                view.update_added_element()

    def add_subaction(self, type_name):
        if not self.current_view.enforce_stop_run():
            return
        if self.element_action.add_subaction(type_name):
            for view in self.views.values():
                view.update_added_element()

    def delete_element(self):
        if not self.current_view.enforce_stop_run():
            return
        old_selection = self.selection_state.copy()
        if self.element_action.delete_element(True):
            self.post_delete(old_selection)

    def cut_element(self):
        if not self.current_view.enforce_stop_run():
            return
        old_selection = self.selection_state.copy()
        if self.element_action.cut_element():
            self.post_delete(old_selection)

    def post_delete(self, old_selection):
        if old_selection and old_selection.is_valid():
            for view in self.views.values():
                view.delete_element(old_selection)
        if self.num_project_jobs() > 0:
            self.menu_manager.delete_element_action.setEnabled(True)

    def copy_element(self):
        self.element_action.copy_element()

    def paste_element(self):
        if not self.current_view.enforce_stop_run():
            return
        old_selection = self.selection_state.copy()
        if self.element_action.paste_element():
            for view in self.views.values():
                view.insert_element(old_selection)

    def clone_element(self):
        if not self.current_view.enforce_stop_run():
            return
        old_selection = self.selection_state.copy()
        if self.element_action.clone_element():
            for view in self.views.values():
                view.insert_element(old_selection)

    def shift_element(self, delta, direction):
        if not self.current_view.enforce_stop_run():
            return
        old_selection = self.selection_state.copy()
        if self.element_action.shift_element(delta, direction):
            for view in self.views.values():
                view.shift_element(old_selection)

    def move_element_up(self):
        self.shift_element(-1, "Up")

    def move_element_down(self):
        self.shift_element(+1, "Down")

    def set_enabled(self, enabled):
        if not self.current_view.enforce_stop_run():
            return
        selection = self.selection_state.copy()
        if self.element_action.set_enabled(selection, enabled):
            for view in self.views.values():
                view.set_enabled(selection)

    def enable(self):
        self.set_enabled(True)

    def disable(self):
        self.set_enabled(False)

    def set_enabled_all(self, enabled):
        if not self.current_view.enforce_stop_run():
            return
        self.element_action.set_enabled_all(enabled)
        for view in self.views.values():
            view.set_enabled_all()

    def enable_all(self):
        self.set_enabled_all(True)

    def disable_all(self):
        self.set_enabled_all(False)

    def edit_element(self):
        if self.element_action.edit_element(self.selection_state):
            for view in self.views.values():
                view.update_widget(self.selection_state)

    def rename(self):
        if self.element_action.rename(self.selection_state):
            for view in self.views.values():
                view.update_widget_recursive(self.selection_state)

    def run_job(self):
        if not self.current_view.enforce_stop_run():
            return
        if self.current_view.has_run_metadata():
            position = (
                self.selection_state.job_index if self.selection_state.is_job_selected() else -1,
                -1, -1)
            self.element_action.save_undo_state("Run Job", "run", position, position)
        self.menu_manager.clear_run_info_action.setEnabled(True)
        if self.current_view.run_job():
            self.menu_manager.run_job_action.setEnabled(False)
            self.menu_manager.run_all_jobs_action.setEnabled(False)
            self.menu_manager.stop_action.setEnabled(True)

    def run_all_jobs(self):
        if self.current_view.has_run_metadata():
            self.element_action.save_undo_state("Run All Jobs", "run_all")
        self.menu_manager.clear_run_info_action.setEnabled(True)
        if self.current_view.run_all_jobs():
            self.menu_manager.run_job_action.setEnabled(False)
            self.menu_manager.run_all_jobs_action.setEnabled(False)
            self.menu_manager.stop_action.setEnabled(True)

    def run_retouch_selected_job(self):
        self.current_view.run_retouch_selected_job()

    def on_run_job_requested(self, job_index):
        self.selection_state.set_indices(job_index)
        self.run_job()

    def on_run_retouch_job_requested(self, job_index):
        self.selection_state.set_indices(job_index)
        self.run_retouch_selected_job()

    def clear_run_metadata(self):
        self.element_action.clear_run_metadata()
        for view in self.views.values():
            view.clear_run_metadata()
        self.menu_manager.clear_run_info_action.setEnabled(False)

    def clear_project_images(self):
        _success, msg = clear_project_images(self.project(), self)
        self.show_status_message(msg)

    def stop(self):
        if self.current_view.stop():
            self.handle_run_finished()

    def handle_widget_updated(self, selection):
        for view in self.views.values():
            if view != self.sender():
                view.update_widget(selection=selection, update_project=False)

    def handle_run_finished(self):
        self.menu_manager.stop_action.setEnabled(False)
        self.menu_manager.run_job_action.setEnabled(True)
        if self.num_project_jobs() > 1:
            self.menu_manager.run_all_jobs_action.setEnabled(True)

    def update_gui_actions_enable(self):
        self.menu_manager.delete_element_action.setEnabled(
            self.selection_state.is_valid())
        self.menu_manager.set_enabled_subactions_gui(
            self.selection_state.is_subaction_selected())
        if self.selection_state.is_valid():
            job = self.project_job(self.selection_state.job_index)
            if job:
                retouch_path = get_retouch_path(job)
                total_files = sum(
                    len([f for f in os.listdir(p) if os.path.isfile(os.path.join(p, f))])
                    for p in retouch_path if os.path.exists(p))
                self.menu_manager.run_retouch_selected_job_action.setEnabled(total_files > 0)

    def set_enabled_file_open_close_actions(self, enabled):
        should_enable = enabled or self.num_project_jobs() > 0
        for action in self.findChildren(QAction):
            if action.property("requires_file"):
                action.setEnabled(should_enable)
        self.menu_manager.stop_action.setEnabled(False)
        self.on_job_count_changed()

    def is_dark_theme(self):
        palette = QApplication.palette()
        window_color = palette.color(QPalette.Window)
        brightness = (window_color.red() * 0.299 +
                      window_color.green() * 0.587 +
                      window_color.blue() * 0.114)
        return brightness < 128

    def on_theme_changed(self):
        dark_theme = self.is_dark_theme()
        for _k, v in self.views.items():
            v.set_dark_theme(dark_theme)
        self.menu_manager.set_dark_theme(dark_theme)
