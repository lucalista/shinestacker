# pylint: disable=C0114, C0116, E0611
import os
import sys
from PySide6.QtCore import QCoreApplication, QProcess


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
