# pylint: disable=C0114, C0115, C0116, C0413, E0611, R0903, E1121, W0201
import os
import sys
import argparse
from PySide6.QtWidgets import QApplication, QMenu
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QEvent
from shinestacker.config.config import config
config.init(DISABLE_TQDM=True, DONT_USE_NATIVE_MENU=True)
from shinestacker.config.constants import constants
from shinestacker.retouch.image_editor_ui import ImageEditorUI
from shinestacker.app.gui_utils import disable_macos_special_menu_items, fill_app_menu
from shinestacker.app.help_menu import add_help_action
from shinestacker.app.open_frames import open_frames


class RetouchApp(ImageEditorUI):
    def __init__(self):
        super().__init__()
        self.app_menu = self.create_menu()
        self.menuBar().insertMenu(self.menuBar().actions()[0], self.app_menu)
        add_help_action(self)

    def create_menu(self):
        app_menu = QMenu(constants.APP_STRING)
        fill_app_menu(self, app_menu)
        return app_menu


class Application(QApplication):
    def event(self, event):
        if event.type() == QEvent.Quit and event.spontaneous():
            self.editor.quit()
        return super().event(event)


def main():
    parser = argparse.ArgumentParser(
        prog=f'{constants.APP_STRING.lower()}-retouch',
        description='Final retouch focus stack image from individual frames.',
        epilog=f'This app is part of the {constants.APP_STRING} package.')
    parser.add_argument('-f', '--filename', nargs='?', help='''
import frames from files.
Multiple files can be specified separated by ';'.
''')
    parser.add_argument('-p', '--path', nargs='?', help='''
import frames from one or more directories.
Multiple directories can be specified separated by ';'.
''')
    args = vars(parser.parse_args(sys.argv[1:]))
    filename = args['filename']
    path = args['path']
    if filename and path:
        print("can't specify both arguments --filename and --path", file=sys.stderr)
        sys.exit(1)
    app = Application(sys.argv)
    if config.DONT_USE_NATIVE_MENU:
        app.setAttribute(Qt.AA_DontUseNativeMenuBar)
    else:
        disable_macos_special_menu_items()
    icon_path = f"{os.path.dirname(__file__)}/../gui/ico/shinestacker.png"
    app.setWindowIcon(QIcon(icon_path))
    editor = RetouchApp()
    app.editor = editor
    editor.show()
    open_frames(editor, filename, path)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
