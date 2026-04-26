# pylint: disable=C0114, C0115, C0116, E0611, R0902
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QRadioButton, QButtonGroup, QLineEdit,
                               QPushButton, QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox)
from .. algorithms.utils import EXTENSIONS_GUI_STR_IN


class SessionFileDialog:
    def __init__(self, default_input_path='', parent=None):
        self.parent = parent
        self._default_input_path = default_input_path if default_input_path \
            else os.path.expanduser("~")
        self._last_path = self._default_input_path

    def update_last_path(self, path):
        if path:
            self._last_path = path

    def open_file(self, caption="", file_filter=""):
        file_name, selected_filter = QFileDialog.getOpenFileName(
            self.parent, caption, self._last_path, file_filter)
        self.update_last_path(os.path.dirname(file_name))
        return file_name, selected_filter

    def open_files(self, caption="", file_filter=""):
        file_paths, selected_filter = QFileDialog.getOpenFileNames(
            self.parent, caption, self._last_path, file_filter)
        if file_paths and len(file_paths) > 0:
            self.update_last_path(os.path.dirname(file_paths[0]))
        return file_paths, selected_filter

    def save_file(self, caption="", file_filter="", default_path=""):
        directory = default_path if default_path else self._last_path
        file_name, selected_filter = QFileDialog.getSaveFileName(
            self.parent, caption, directory, file_filter)
        self.update_last_path(os.path.dirname(file_name))
        return file_name, selected_filter


class FolderFileSelectionWidget(QWidget):
    def __init__(self, default_input_path='', parent=None):
        super().__init__(parent)
        self.selection_mode = 'folder'  # 'folder' or 'files'
        self.selected_files = []
        self._default_input_path = default_input_path if default_input_path \
            else os.path.expanduser("~")
        self.setup_ui()

    def setup_ui(self):
        self.mode_group = QButtonGroup(self)
        self.folder_mode_radio = QRadioButton("Select Folder")
        self.folder_mode_radio.setMaximumWidth(100)
        self.files_mode_radio = QRadioButton("Select Files")
        self.files_mode_radio.setMaximumWidth(100)
        self.folder_mode_radio.setChecked(True)
        self.mode_group.addButton(self.folder_mode_radio)
        self.mode_group.addButton(self.files_mode_radio)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("input files folder")
        self.browse_button = QPushButton("Browse Folder...")
        self.browse_button.setFixedWidth(120)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setAlignment(Qt.AlignLeft)
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(2, 2, 2, 2)
        mode_layout.setSpacing(20)
        mode_layout.addWidget(self.folder_mode_radio)
        mode_layout.addWidget(self.files_mode_radio)
        mode_layout.addStretch()
        main_layout.addLayout(mode_layout)
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(2, 2, 2, 2)
        input_layout.setSpacing(8)
        input_layout.setAlignment(Qt.AlignLeft)
        input_layout.addWidget(self.path_edit)
        input_layout.addWidget(self.browse_button)
        main_layout.addLayout(input_layout)
        self.setLayout(main_layout)
        self.folder_mode_radio.toggled.connect(self.update_selection_mode)
        self.files_mode_radio.toggled.connect(self.update_selection_mode)
        self.browse_button.clicked.connect(self.handle_browse)

    def update_selection_mode(self):
        if self.folder_mode_radio.isChecked():
            self.selection_mode = 'folder'
            self.browse_button.setText("Browse Folder...")
            # self.path_edit.setPlaceholderText("input files folder")
        else:
            self.selection_mode = 'files'
            self.browse_button.setText("Browse Files...")
            # self.path_edit.setPlaceholderText("input files")

    def handle_browse(self):
        self.path_edit.setText('')
        if self.selection_mode == 'folder':
            self.browse_folder()
        else:
            self.browse_files()

    def _get_input_folder_path(self):
        current_path = self.path_edit.text()
        if current_path != '' and os.path.isdir(current_path):
            return current_path
        return self._default_input_path

    def browse_folder(self):
        input_folder_path = self._get_input_folder_path()
        path = QFileDialog.getExistingDirectory(self, "Select Input Folder", input_folder_path)
        if path:
            self.selected_files = []
            self.path_edit.setText(path)

    def browse_files(self):
        input_folder_path = self._get_input_folder_path()
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Input Files", input_folder_path,
            f"Image files ({EXTENSIONS_GUI_STR_IN})"
        )
        if files:
            parent_dir = os.path.dirname(files[0])
            if all(os.path.dirname(f) == parent_dir for f in files):
                self.selected_files = files
                self.path_edit.setText(parent_dir)
            else:
                self.selected_files = []
                QMessageBox.warning(
                    self, "Invalid Selection",
                    "All files must be in the same directory."
                )

    def get_selection_mode(self):
        return self.selection_mode

    def get_selected_files(self):
        return self.selected_files

    def num_selected_files(self):
        return len(self.selected_files)

    def get_selected_filenames(self):
        return [os.path.basename(file_path) for file_path in self.selected_files]

    def get_path(self):
        return self.path_edit.text()

    def set_path(self, path):
        self.path_edit.setText(path)

    def text_changed_connect(self, callback):
        self.path_edit.textChanged.connect(callback)
