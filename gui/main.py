import sys
sys.path.append('../')
import logging
import os
import matplotlib
matplotlib.use('agg')
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer
from config.config import config
config.init(DISABLE_TQDM=True)
from core.logging import setup_logging
from gui.main_window import MainWindow
from gui.menu import DONT_USE_NATIVE_MENU
from gui.gui_utils import disable_macos_special_menu_items


def main():
    setup_logging(console_level=logging.DEBUG, file_level=logging.DEBUG,
                  log_file="logs/focusstack.log", disable_console=True)
    app = QApplication(sys.argv)
    if DONT_USE_NATIVE_MENU:
        app.setAttribute(Qt.AA_DontUseNativeMenuBar)
    else:
        disable_macos_special_menu_items()
    app.setWindowIcon(QIcon('ico/focus_stack.png'))
    file_to_open = None
    if len(sys.argv) > 1:
        file_to_open = sys.argv[1]
        if not os.path.isfile(file_to_open):
            print(f"File not found: {file_to_open}")
            file_to_open = None
    window = MainWindow()
    window.show()
    if file_to_open:
        QTimer.singleShot(100, lambda: window.open_project(file_to_open))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
