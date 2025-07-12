import sys
from PySide6.QtWidgets import QApplication, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, QTimer, QEvent
from focusstack.retouch.image_editor_ui import ImageEditorUI
from focusstack.core.core_utils import get_app_base_path
from focusstack.config.config import config
from focusstack.app.gui_utils import disable_macos_special_menu_items
from focusstack.app.help_menu import add_help_menu
from focusstack.app.about_dialog import show_about_dialog


class RetouchApp(ImageEditorUI):
    def __init__(self):
        super().__init__()
        self.app_menu = self.create_menu()
        self.menuBar().insertMenu(self.menuBar().actions()[0], self.app_menu)
        add_help_menu(self)

    def create_menu(self):
        app_menu = QMenu("FocusStack")
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


class Application(QApplication):
    def event(self, event):
        if event.type() == QEvent.Quit and event.spontaneous():
            self.editor.quit()
        return super().event(event)


def main():
    app = Application(sys.argv)
    if config.DONT_USE_NATIVE_MENU:
        app.setAttribute(Qt.AA_DontUseNativeMenuBar)
    else:
        disable_macos_special_menu_items()
    app.setWindowIcon(QIcon(f'{get_app_base_path()}/ico/focus_stack.png'))
    file_to_open = None
    if len(sys.argv) > 1:
        file_to_open = sys.argv[1]
    editor = RetouchApp()
    app.editor = editor
    editor.show()
    if file_to_open:
        QTimer.singleShot(100, lambda: editor.open_file(file_to_open))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
