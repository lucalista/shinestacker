import sys
sys.path.append('../')
from PySide6.QtWidgets import QApplication, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, QTimer
from gui.gui_utils import disable_macos_special_menu_items
from retouch.image_editor_ui import ImageEditorUI
from config.config import config


class RetouchApp(ImageEditorUI):
    def __init__(self):
        super().__init__()
        self.app_menu = self.create_menu()
        self.menuBar().insertMenu(self.menuBar().actions()[0], self.app_menu)

    def create_menu(self):
        app_menu = QMenu("FocusStack")
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
        if self._check_unsaved_changes():
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    if config.DONT_USE_NATIVE_MENU:
        app.setAttribute(Qt.AA_DontUseNativeMenuBar)
    else:
        disable_macos_special_menu_items()
    app.setWindowIcon(QIcon('ico/focus_stack.png'))
    file_to_open = None
    if len(sys.argv) > 1:
        file_to_open = sys.argv[1]
    editor = RetouchApp()
    editor.show()
    if file_to_open:
        QTimer.singleShot(100, lambda: editor.open_file(file_to_open))
    sys.exit(app.exec())
