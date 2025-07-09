import webbrowser
from PySide6.QtGui import QAction


def add_help_menu(app):
    menu = app.menuBar().addMenu("&Help")
    help_action = QAction("Online Help", app)
    help_action.triggered.connect(browse_website)
    menu.addAction(help_action)


def browse_website():
    webbrowser.open("https://github.com/lucalista/focusstack/blob/main/docs/main.md")
