# pylint: disable=C0114, C0115, C0116, C0413, E0611, R0903, E1121, W0201
import os
import sys
import logging
import argparse
import matplotlib
import matplotlib.backends.backend_pdf
matplotlib.use('agg')
from PySide6.QtWidgets import QApplication, QMenu
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer, QEvent
from shinestacker.config.config import config
config.init(DISABLE_TQDM=True, DONT_USE_NATIVE_MENU=True)
from shinestacker.config.constants import constants
from shinestacker.core.logging import setup_logging
from shinestacker.gui.main_window import MainWindow
from shinestacker.app.gui_utils import disable_macos_special_menu_items, fill_app_menu
from shinestacker.app.help_menu import add_help_action


class ProjectApp(MainWindow):
    def __init__(self):
        super().__init__()
        self.app_menu = self.create_menu()
        self.menuBar().insertMenu(self.menuBar().actions()[0], self.app_menu)
        add_help_action(self)
        self.set_retouch_callback(self._retouch_callback)

    def create_menu(self):
        app_menu = QMenu(constants.APP_STRING)
        fill_app_menu(self, app_menu)
        return app_menu

    def _retouch_callback(self, filename):
        p = ";".join(filename)
        os.system(f'{constants.RETOUCH_APP} -p "{p}" &')


class Application(QApplication):
    def event(self, event):
        if event.type() == QEvent.Quit and event.spontaneous():
            self.window.quit()
        return super().event(event)


def main():
    parser = argparse.ArgumentParser(
        prog=f'{constants.APP_STRING.lower()}-project',
        description='Manage and run focus stack jobs.',
        epilog=f'This app is part of the {constants.APP_STRING} package.')
    parser.add_argument('-f', '--filename', nargs='?', help='''
project filename.
''')
    parser.add_argument('-x', '--expert', action='store_true', help='''
expert options are visible by default.
''')
    args = vars(parser.parse_args(sys.argv[1:]))
    setup_logging(console_level=logging.DEBUG, file_level=logging.DEBUG, disable_console=True)
    app = Application(sys.argv)
    if config.DONT_USE_NATIVE_MENU:
        app.setAttribute(Qt.AA_DontUseNativeMenuBar)
    else:
        disable_macos_special_menu_items()
    icon_path = f"{os.path.dirname(__file__)}/../gui/ico/shinestacker.png"
    app.setWindowIcon(QIcon(icon_path))
    window = ProjectApp()
    if args['expert']:
        window.set_expert_options()
    app.window = window
    window.show()
    filename = args['filename']
    if filename:
        QTimer.singleShot(100, lambda: window.project_controller.open_project(filename))
    else:
        QTimer.singleShot(100, window.project_controller.new_project)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
