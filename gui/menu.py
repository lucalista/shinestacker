from PySide6.QtGui import QAction
from gui.project_model import Project, ActionConfig
from gui.action_config import *
from abc import ABC, abstractmethod
from typing import Dict, Any
import os.path
import os
import json, jsonpickle

class WindowMenu(QMainWindow):
    def __init__(self):
        super().__init__()
        self._current_file = None
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        new_action = QAction("&New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)
        open_action = QAction("&Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)
        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self._save_project_as)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        exit_action = QAction("&Shut down ", self)
        exit_action.setShortcut("Ctrl+Q")        
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _new_project(self):
        if self._check_unsaved_changes():
            self.project = Project()
            self._current_file = None
            self._update_title()
            self.job_list.clear()
            self.action_list.clear()
    
    def _open_project(self):
        if not self._check_unsaved_changes():
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "",
            "Project Files (*.fsp);;All Files (*)")
        if file_path:
            try:
                file = open(file_path, 'r')
                json_obj = json.load(file)
                self.project = Project.from_dict(json_obj['project'])
                self._current_file = file_path
                self._update_title()
                self._refresh_ui()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot open file:\n{str(e)}")
    
    def _save_project(self):
        if self._current_file:
            self._do_save(self._current_file)
        else:
            self._save_project_as()
    
    def _save_project_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Project As", "",
            "Project Files (*.fsp);;All Files (*)")
        if file_path:
            if not file_path.endswith('.fsp'):
                file_path += '.fsp'
            self._do_save(file_path)
            self._current_file = file_path
            self._update_title()

    def _do_save(self, file_path):
        try:
            json_obj = jsonpickle.encode({
                'project': self.project.to_dict(),
                'version': 1
            })
            f = open(file_path, 'w')
            f.write(json_obj)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot save file:\n{str(e)}")
            
    def _check_unsaved_changes(self) -> bool:
        return True
        # ignore the following code
        reply = QMessageBox.question(
            self, "Unsaved Changes",
            "The project has unsaved changes. Do you want to continue?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )
        if reply == QMessageBox.Save:
            self._save_project()
            return True
        elif reply == QMessageBox.Discard:
            return True
        else:  # Cancel
            return False
    
    def _update_title(self):
        title = "Focus Stacking GUI"
        if self._current_file:
            title += f" - {os.path.basename(self._current_file)}"
        self.setWindowTitle(title)
    
    def _refresh_ui(self):
        self.job_list.clear()
        for job in self.project.jobs:
            self.job_list.addItem(job.params['name'])
        
        if self.project.jobs:
            self.job_list.setCurrentRow(0)        
