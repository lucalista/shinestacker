import sys
sys.path.append('../')
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui.main_window import MainWindow
import sys
from focus_stack.logging import setup_logging
import logging


def main():
    setup_logging(
        console_level=logging.DEBUG,
        file_level=logging.DEBUG,
        log_file="logs/focusstack.log"
    )
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('ico/focus_stack.ico'))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
