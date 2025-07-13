import pytest
import time
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import PySide6
PySide6.QtCore.QCoreApplication.setAttribute(PySide6.QtCore.Qt.AA_ShareOpenGLContexts)
from focusstack.config.constants import constants
from focusstack.gui.main_window import MainWindow


@pytest.fixture
def main_window(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    return w


def test_open_file_success(main_window, qtbot, mocker):
    file_name = "project.fsp"
    mocker.patch(
        "PySide6.QtWidgets.QFileDialog.getOpenFileName",
        return_value=(f"../examples/{file_name}", "")
    )

    main_window.open_project()
    time.sleep(0.5)

    assert main_window is not None
    assert main_window.windowTitle() == f"{constants.APP_TITLE} - {file_name}"
