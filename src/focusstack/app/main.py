import sys
import os
import logging
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMenu
from PySide6.QtGui import QAction, QIcon, QGuiApplication
from PySide6.QtCore import Qt, QTimer
from focusstack.config.config import config
config.init(DISABLE_TQDM=True, COMBINED_APP=True)
from focusstack.core.logging import setup_logging
from focusstack.gui.main_window import MainWindow
from focusstack.retouch.image_editor_ui import ImageEditorUI
from focusstack.app.gui_utils import disable_macos_special_menu_items
from focusstack.app.help_menu import add_help_menu
from focusstack.app.about_dialog import show_about_dialog

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Focus stacking")
        self.resize(1400, 900)
        center = QGuiApplication.primaryScreen().geometry().center()
        self.move(center - self.rect().center())
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.project_window = MainWindow()
        self.retouch_window = ImageEditorUI()
        self.stacked_widget.addWidget(self.project_window)
        self.stacked_widget.addWidget(self.retouch_window)
        self.app_menu = self.create_menu()
        self.project_window.menuBar().insertMenu(self.project_window.menuBar().actions()[0], self.app_menu)
        self.retouch_window.menuBar().insertMenu(self.retouch_window.menuBar().actions()[0], self.app_menu)
        add_help_menu(self.project_window)
        add_help_menu(self.retouch_window)
        self.set_initial_app()

    def switch_to_project(self):
        self.switch_app(0)
        self.switch_to_project_action.setChecked(True)
        self.switch_to_retouch_action.setChecked(False)
        self.switch_to_project_action.setEnabled(False)
        self.switch_to_retouch_action.setEnabled(True)

    def switch_to_retouch(self):
        self.switch_app(1)
        self.switch_to_project_action.setChecked(False)
        self.switch_to_retouch_action.setChecked(True)
        self.switch_to_project_action.setEnabled(True)
        self.switch_to_retouch_action.setEnabled(False)

    def create_menu(self):
        app_menu = QMenu("FocusStack")
        self.switch_to_project_action = QAction("Project", self)
        self.switch_to_project_action.setCheckable(True)
        self.switch_to_project_action.triggered.connect(self.switch_to_project)
        self.switch_to_retouch_action = QAction("Retouch", self)
        self.switch_to_retouch_action.setCheckable(True)
        self.switch_to_retouch_action.triggered.connect(self.switch_to_retouch)
        app_menu.addAction(self.switch_to_project_action)
        app_menu.addAction(self.switch_to_retouch_action)
        app_menu.addSeparator()
        about_action = QAction("About", self)
        about_action.triggered.connect(show_about_dialog)
        app_menu.addAction(about_action)
        app_menu.addSeparator()
        if config.DONT_USE_NATIVE_MENU:
            quit_txt, quit_short = "&Quit", "Ctrl+Q"
        else:
            quit_txt, quit_short = "Shut dw&wn", "Ctrl+W"
        exit_action = QAction(quit_txt, self)
        exit_action.setShortcut(quit_short)
        exit_action.triggered.connect(self.quit)
        app_menu.addAction(exit_action)
        return app_menu

    def quit(self):
        if self.retouch_window._check_unsaved_changes() and self.project_window._check_unsaved_changes():
            self.close()

    def switch_app(self, index):
        self.stacked_widget.setCurrentIndex(index)

    def set_initial_app(self):
        import sys
        if "--retouch-window" in sys.argv:
            self.switch_to_retouch()
        else:
            self.switch_to_project()


def main():
    setup_logging(console_level=logging.DEBUG, file_level=logging.DEBUG,
                  log_file="logs/focusstack.log", disable_console=True)
    app = QApplication(sys.argv)
    if config.DONT_USE_NATIVE_MENU:
        app.setAttribute(Qt.AA_DontUseNativeMenuBar)
    else:
        disable_macos_special_menu_items()
    app.setWindowIcon(QIcon('ico/focus_stack.png'))
    main_app = MainApp()
    main_app.show()
    file_to_open = None
    if len(sys.argv) > 1:
        file_to_open = sys.argv[1]
        if not os.path.isfile(file_to_open):
            print(f"File not found: {file_to_open}")
            file_to_open = None
    if file_to_open:
        extension = file_to_open.split('.')[-1]
        if extension == 'fsp':
            main_app.switch_to_project()
            QTimer.singleShot(100, lambda: main_app.project_window.open_project(file_to_open))
        elif extension in ['tif', 'tiff']:
            main_app.switch_to_retouch()
            QTimer.singleShot(100, lambda: main_app.retouch_window.open_file(file_to_open))
        else:
            print(f"File extension: {extension} not supported.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

