import pytest
import json
import tempfile
from pathlib import Path
from shinestacker.config.constants import constants
from shinestacker.gui.main_window import MainWindow


@pytest.fixture
def main_window(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    return w


def test_open_file_success(main_window, qtbot, mocker):
    project_data = {
        "project": [{
            "type_name": "Job",
            "params": {
                "name": "test",
                "working_path": ".",
                "input_path": "."
            },
            "sub_actions": []
        }],
        "version": 1
    }
    with tempfile.NamedTemporaryFile(suffix='.fsp', delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)
        tmp_file.write(json.dumps(project_data).encode('utf-8'))
    try:
        mocker.patch(
            "PySide6.QtWidgets.QFileDialog.getOpenFileName",
            return_value=(str(tmp_path), "")
        )
        main_window.open_project()
        qtbot.wait(100)
        assert main_window is not None
        assert main_window.windowTitle() == f"{constants.APP_TITLE} - {tmp_path.name}"
    finally:
        tmp_path.unlink(missing_ok=True)
