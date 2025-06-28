import sys
sys.path.append('../')
import sys
import logging
import os
import matplotlib
matplotlib.use('agg')
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from PySide6.QtCore import QCoreApplication, QProcess
from config.config import config
config.init(DISABLE_TQDM=True)
from core.logging import setup_logging
from gui.main_window import MainWindow
from gui.menu import DONT_USE_NATIVE_MENU


def disable_macos_special_menu_items():
    if QCoreApplication.instance().platformName() != "cocoa":
        return
    prefs = [
        ("NSDisabledCharacterPaletteMenuItem", "YES"),
        ("NSDisabledDictationMenuItem", "YES"),
        ("NSDisabledInputMenu", "YES"),
        ("NSDisabledServicesMenu", "YES"),
        ("WebAutomaticTextReplacementEnabled", "NO"),
        ("WebAutomaticSpellingCorrectionEnabled", "NO"),
        ("WebContinuousSpellCheckingEnabled", "NO"),
        ("NSTextReplacementEnabled", "NO"),
        ("NSAllowCharacterPalette", "NO")
    ]
    for key, value in prefs:
        QProcess.execute("defaults", ["write", "-g", key, "-bool", value])
    QProcess.execute("defaults", ["write", "-g", "NSAutomaticTextCompletionEnabled", "-bool", "NO"])
    user = os.getenv('USER')
    if user:
        QProcess.startDetached("pkill", ["-u", user, "-f", "cfprefsd"])
        QProcess.startDetached("pkill", ["-u", user, "-f", "SystemUIServer"])


def main():
    setup_logging(console_level=logging.DEBUG, file_level=logging.DEBUG,
                  log_file="logs/focusstack.log", disable_console=True)
    app = QApplication(sys.argv)
    if DONT_USE_NATIVE_MENU:
        app.setAttribute(Qt.AA_DontUseNativeMenuBar)
    else:
        disable_macos_special_menu_items()
    app.setWindowIcon(QIcon('ico/focus_stack.png'))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
