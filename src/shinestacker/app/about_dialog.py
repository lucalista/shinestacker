# pylint: disable=C0114, C0116, E0611, W0718
import json
from urllib.request import urlopen, Request
from urllib.error import URLError
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt
from .. import __version__
from .. config.constants import constants


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
        with urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data['tag_name']
    except (URLError, ValueError, KeyError, TimeoutError):
        return None


def show_about_dialog():
    version_clean = __version__.split("+", maxsplit=1)[0]
    latest_version = None
    try:
        latest_version = get_latest_version()
    except Exception:
        pass
    update_text = ""
    # pyling: disable=XXX
    if latest_version:
        latest_clean = latest_version.lstrip('v')
        if compare_versions(version_clean, latest_clean) < 0:
            update_text = f"""
            <p style="color: red; font-weight: bold;">
                Update available! Latest version: {latest_version}
                <br><a href="https://github.com/lucalista/shinestacker/releases/latest">Download here</a>
            </p>
            """ # noqa E501
        else:
            update_text = f"""
            <p style="color: green; font-weight: bold;">
                You are using the lastet version: {latest_version}.
            </p>
            """
    about_text = f"""
    <h3>{constants.APP_TITLE}</h3>
    <h4>version: v{version_clean}</h4>
    {update_text}
    <p style='font-weight: normal;'>App and framework to combine multiple images
    into a single focused image.</p>
    <p>Author: Luca Lista<br/>
    Email: <a href="mailto:luka.lista@gmail.com">luka.lista@gmail.com</a></p>
    <ul>
    <li><a href="https://shinestacker.wordpress.com/">Website on Wordpress</a></li>
    <li><a href="https://github.com/lucalista/shinestacker">GitHub project repository</a></li>
    </ul>
    """
    # pyling: enable=XXX
    msg = QMessageBox()
    msg.setWindowTitle(f"About {constants.APP_STRING}")
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setTextFormat(Qt.TextFormat.RichText)
    msg.setText(about_text)
    msg.setIcon(QMessageBox.Icon.NoIcon)
    msg.exec_()
