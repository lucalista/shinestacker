# pylint: disable=E0611, W0718, R0903, W0212
import traceback
import json
import ssl
from urllib.request import urlopen, Request
from urllib.error import URLError
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, QCheckBox)
from PySide6.QtCore import Qt
from .. import __version__
from .. retouch.icon_container import icon_container
from .. config.constants import constants
from .. config.settings import Settings


class AboutDialog(QDialog):
    def __init__(self, parent=None, about_text=""):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.resize(400, 300)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        icon_widget = icon_container()
        icon_layout = QHBoxLayout()
        icon_layout.addStretch()
        icon_layout.addWidget(icon_widget)
        icon_layout.addStretch()
        layout.addLayout(icon_layout)
        about_label = QLabel(about_text)
        about_label.setOpenExternalLinks(True)
        about_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        about_label.setWordWrap(True)
        about_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(about_label)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button = QPushButton("OK")
        button.setFixedWidth(100)
        button.clicked.connect(self.accept)
        button_layout.addWidget(button)
        button_layout.addStretch()
        layout.addLayout(button_layout)


def check_version():
    version_clean = __version__.split("+", maxsplit=1)[0]
    latest_version = get_latest_version()
    if not latest_version:
        return None
    latest_clean = latest_version.lstrip('v')
    return compare_versions(version_clean, latest_clean) < 0, latest_version


def show_update_dialog(parent):
    result = check_version()
    if not result:
        return
    update_available, latest_version = result
    if not update_available:
        return
    version_clean = __version__.split("+", maxsplit=1)[0]
    settings = Settings.instance()
    check_for_updates = settings.get('check_for_updates')
    dialog = QMessageBox(parent)
    dialog.setWindowTitle("Update Available")
    dialog.setIcon(QMessageBox.Information)
    message = f"""
    <html>
    <p><b>A new version of {constants.APP_TITLE} is available!</b></p>
    <ul>
    <li><b>Your version:</b> v{version_clean}</li>
    <li><b>Latest version:</b> {latest_version}</li>
    </ul>
    <p>Download the latest version from:</p>
    <p><a href="https://github.com/lucalista/shinestacker/releases/latest">https://github.com/lucalista/shinestacker/releases/latest</a></p>
    </html>
    """  # noqa E501
    dialog.setText(message)
    dialog.setInformativeText('You can always check for updates in the About dialog.')
    checkbox = QCheckBox("Don't show this message again")
    checkbox.setChecked(not check_for_updates)
    dialog.setCheckBox(checkbox)
    dialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    dialog.setDefaultButton(QMessageBox.Ok)
    result = dialog.exec()
    if result == QMessageBox.Ok:
        new_setting = not checkbox.isChecked()
        settings.set('check_for_updates', new_setting)
        settings.update()


def compare_versions(current, latest):
    def parse_version(v):
        v = v.lstrip('v')
        parts = v.split('.')
        result = []
        for part in parts:
            try:
                result.append(int(part))
            except ValueError:
                result.append(part)
        return result
    current_parts = parse_version(current)
    latest_parts = parse_version(latest)
    for i in range(max(len(current_parts), len(latest_parts))):
        c = current_parts[i] if i < len(current_parts) else 0
        l = latest_parts[i] if i < len(latest_parts) else 0  # noqa: E741
        if isinstance(c, int) and isinstance(l, int):
            if c < l:
                return -1
            if c > l:
                return 1
        else:
            if str(c) < str(l):
                return -1
            if str(c) > str(l):
                return 1
    return 0


def get_latest_version():
    try:
        url = "https://api.github.com/repos/lucalista/shinestacker/releases/latest"
        headers = {'User-Agent': 'ShineStacker'}
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                return data['tag_name']
        except URLError as ssl_error:
            if "CERTIFICATE_VERIFY_FAILED" in str(ssl_error):
                print("SSL verification failed, using unverified context", RuntimeWarning)
                context = ssl._create_unverified_context()
                with urlopen(req, timeout=5, context=context) as response:
                    data = json.loads(response.read().decode())
                    return data['tag_name']
            else:
                raise
    except (URLError, ValueError, KeyError, TimeoutError) as e:
        print(f"URL open error: {str(e)}")
        traceback.print_exc()
        return None


def show_about_dialog(parent):
    version_clean = __version__.split("+", maxsplit=1)[0]
    update_available, latest_version = False, None
    try:
        result = check_version()
        if result:
            update_available, latest_version = result
    except Exception:
        traceback.print_exc()
    update_text = ""
    if latest_version:
        if update_available:
            update_text = f"""
            <p style="color: red; font-weight: bold;">
                Update available! Latest version: {latest_version}
                <br><a href="https://github.com/lucalista/shinestacker/releases/latest">Download here</a>
            </p>
            """ # noqa E501
        else:
            update_text = """
            <p style="color: green; font-weight: bold;">
                You are using the lastet version.
            </p>
            """
    about_text = f"""
    <h3>{constants.APP_TITLE}</h3>
    <h4>version: v{version_clean}</h4>
    {update_text}
    <p style='font-weight: normal;'>Focus stackign applications and framework.<br>
    Combine multiple frames into a single focused image.</p>
    <p>Author: Luca Lista<br/>
    Email: <a href="mailto:luka.lista@gmail.com">luka.lista@gmail.com</a></p>
    <ul>
    <li><a href="https://shinestacker.wordpress.com/">Website on Wordpress</a></li>
    <li><a href="https://github.com/lucalista/shinestacker">GitHub project repository</a></li>
    </ul>
    """
    dialog = AboutDialog(parent, about_text)
    dialog.exec()
