# pylint: disable=C0114, C0116, E0611
import webbrowser
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction


def add_help_action(app):
    help_menu = app.menuBar().findChild(QMenu, "Help")
    if help_menu:
        help_action = QAction("Online Help", app)
        help_action.triggered.connect(browse_website)
        help_menu.addSeparator()
        help_menu.addAction(help_action)


def browse_website():
    webbrowser.open("https://shinestacker.readthedocs.io/en/latest/")
