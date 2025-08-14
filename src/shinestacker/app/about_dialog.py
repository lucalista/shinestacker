# pylint: disable=C0114, C0116, E0611
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt
from .. import __version__
from .. config.constants import constants


def show_about_dialog():
    version_clean = __version__.split("+", maxsplit=1)[0]
    about_text = f"""
    <h3>{constants.APP_TITLE}</h3>
    <h4>version: v{version_clean}</h4>
    <p style='font-weight: normal;'>App and framework to combine multiple images
    into a single focused image.</p>
    <p>Author: Luca Lista<br/>
    Email: <a href="mailto:luka.lista@gmail.com">luka.lista@gmail.com</a></p>
    <ul>
    <li><a href="https://shinestacker.wordpress.com/">Website on Wordpress</a></li>
    <li><a href="https://github.com/lucalista/shinestacker">GitHub project repository</a></li>
    </ul>
    """
    msg = QMessageBox()
    msg.setWindowTitle(f"About {constants.APP_STRING}")
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setTextFormat(Qt.TextFormat.RichText)
    msg.setText(about_text)
    msg.setIcon(QMessageBox.Icon.NoIcon)
    msg.exec_()
