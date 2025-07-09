from PySide6.QtWidgets import QMessageBox
from focusstack import __version__


def show_about_dialog():
    version_clean = __version__.split("+")[0]
    about_text = f"FocusStack v{version_clean}"
    msg = QMessageBox()
    msg.setWindowTitle("About")
    msg.setText(about_text)
    msg.exec_()
