from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt
from focusstack import __version__


def show_about_dialog():
    version_clean = __version__.split("+")[0]
    about_text = f"""
    <h3>FocusStack</h3>
    <h4>version: v{version_clean}</h4>
    <p style='font-weight: normal;'>App and framework to combine multiple images
    into a single focused image.</p>
    <p>Author: Luca Lista<br/>
    Email: <a href="mailto:luka.lista@gmail.com">luka.lista@gmail.com</a></p>
    <p><a href="https://github.com/lucalista/focusstack">GitHub homepage</a></p>
    """
    msg = QMessageBox()
    msg.setWindowTitle("About FocusStack")
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setTextFormat(Qt.TextFormat.RichText)
    msg.setText(about_text)
    msg.setIcon(QMessageBox.Icon.NoIcon)
    msg.exec_()
