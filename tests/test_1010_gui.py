import pytest
import time
from focusstack.gui.main_window import MainWindow


@pytest.fixture
def main_window(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    return w


def test_open_file_success(main_window, qtbot, mocker):
    mocker.patch(
        "PySide6.QtWidgets.QFileDialog.getOpenFileName",
        return_value=("../examples/project.fsp", "")
    )

    main_window.open_project("../examples/project.fsp")
    time.sleep(1)

    assert main_window is not None
    assert main_window.windowTitle() == "Focus Stacking GUI - project.fsp"
