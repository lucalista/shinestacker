# pylint: disable=E0611, R0913, R0917
import os
import sys
import logging
from PySide6.QtCore import Qt, QCoreApplication, QProcess
from PySide6.QtGui import QAction, QIcon
from shinestacker.config.constants import constants
from shinestacker.config.config import config
from shinestacker.config.settings import StdPathFile
from shinestacker.app.about_dialog import show_about_dialog
from shinestacker.app.settings_dialog import show_settings_dialog
from shinestacker.core.logging import setup_logging


def disable_macos_special_menu_items():
    if not (sys.platform == "darwin" and QCoreApplication.instance().platformName() == "cocoa"):
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
        ("NSAllowCharacterPalette", "NO"),
        ("NSDisabledHelpSearch", "YES"),
        ("NSDisabledSpellingMenuItems", "YES"),
        ("NSDisabledTextSubstitutionMenuItems", "YES"),
        ("NSDisabledGrammarMenuItems", "YES"),
        ("NSAutomaticPeriodSubstitutionEnabled", "NO"),
        ("NSAutomaticQuoteSubstitutionEnabled", "NO"),
        ("NSAutomaticDashSubstitutionEnabled", "NO"),
        ("WebAutomaticFormCompletionEnabled", "NO"),
        ("WebAutomaticPasswordAutoFillEnabled", "NO")
    ]
    for key, value in prefs:
        QProcess.execute("defaults", ["write", "-g", key, "-bool", value])
    QProcess.execute("defaults", ["write", "-g", "NSAutomaticTextCompletionEnabled", "-bool", "NO"])
    user = os.getenv('USER') or os.getenv('LOGNAME')
    if user:
        QProcess.startDetached("pkill", ["-u", user, "-f", "cfprefsd"])
        QProcess.startDetached("pkill", ["-u", user, "-f", "SystemUIServer"])


def fill_app_menu(app, app_menu, handle_project_config, handle_retouch_config):
    about_action = QAction(f"About {constants.APP_STRING}", app)
    about_action.triggered.connect(lambda: show_about_dialog(app))
    app_menu.addAction(about_action)
    app_menu.addSeparator()
    settings_action = QAction("Settings", app)
    settings_action.triggered.connect(lambda: show_settings_dialog(
        app, handle_project_config, handle_retouch_config))
    app_menu.addAction(settings_action)
    app_menu.addSeparator()
    if config.DONT_USE_NATIVE_MENU:
        quit_txt, quit_short = "&Quit", "Ctrl+Q"
    else:
        quit_txt, quit_short = "Shut dw&wn", "Ctrl+Q"
    exit_action = QAction(quit_txt, app)
    exit_action.setShortcut(quit_short)
    exit_action.triggered.connect(app.quit)
    app_menu.addAction(exit_action)


def set_css_style(app):
    css_style = """
        QToolTip {
            color: black;
            border: 1px solid black;
        }
"""
    app.setStyleSheet(css_style)


def make_app(application_class):
    setup_logging(console_level=logging.DEBUG, file_level=logging.DEBUG, disable_console=True,
                  log_file=StdPathFile('shinestacker.log').get_file_path())
    app = application_class(sys.argv)
    if config.DONT_USE_NATIVE_MENU:
        app.setAttribute(Qt.AA_DontUseNativeMenuBar)
    else:
        disable_macos_special_menu_items()
    icon_path = f"{os.path.dirname(__file__)}/../gui/ico/shinestacker.png"
    app.setWindowIcon(QIcon(icon_path))
    set_css_style(app)
    return app
