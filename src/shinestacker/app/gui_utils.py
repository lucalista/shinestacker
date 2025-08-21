# pylint: disable=C0114, C0116, E0611
import os
import sys
from PySide6.QtCore import QCoreApplication, QProcess
from PySide6.QtGui import QAction
from shinestacker.config.constants import constants
from shinestacker.config.config import config
from shinestacker.app.about_dialog import show_about_dialog


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


def fill_app_menu(app, app_menu):
    about_action = QAction(f"About {constants.APP_STRING}", app)
    about_action.triggered.connect(lambda: show_about_dialog(app))
    app_menu.addAction(about_action)
    app_menu.addSeparator()
    if config.DONT_USE_NATIVE_MENU:
        quit_txt, quit_short = "&Quit", "Ctrl+Q"
    else:
        quit_txt, quit_short = "Shut dw&wn", "Ctrl+Q"
    exit_action = QAction(quit_txt, app)
    exit_action.setShortcut(quit_short)
    exit_action.triggered.connect(app.quit)
    app_menu.addAction(exit_action)
