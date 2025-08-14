import os
import json
import tempfile
import pytest
import jsonpickle
from unittest.mock import patch
from PySide6.QtWidgets import QMessageBox
from shinestacker.gui.actions_window import ActionsWindow
from shinestacker.gui.project_model import Project
from shinestacker.gui.project_model import get_action_working_path, get_action_input_path, get_action_output_path

project_data = {"project": [{"type_name": "Job", "params": {"name": "test", "working_path": ".", "input_path": ""}}], "version": 1}


@pytest.fixture
def actions_window(qtbot):
    window = ActionsWindow()
    qtbot.addWidget(window)
    return window


@pytest.fixture(autouse=True)
def mock_dialogs():
    with patch('PySide6.QtWidgets.QMessageBox.question', return_value=QMessageBox.Discard):
        yield


@pytest.fixture
def sample_project():
    project = Project.from_dict(project_data["project"])
    assert project.jobs and len(project.jobs) == 1
    return project


@pytest.fixture
def mock_project_file():
    with tempfile.NamedTemporaryFile(suffix=".fsp", mode='w', delete=False) as f:
        json_obj = jsonpickle.encode(project_data)
        f.write(json_obj)
        return f.name


def test_close_project(actions_window, qtbot):
    actions_window._modified_project = True
    actions_window._current_file = "test.fsp"
    actions_window.close_project()
    assert actions_window._current_file is None
    assert actions_window._modified_project is False
    assert actions_window.job_list.count() == 0
    assert isinstance(actions_window.project, Project)


def test_current_file_name(actions_window):
    assert actions_window.current_file_name() == ''
    actions_window._current_file = "/path/to/test.fsp"
    assert actions_window.current_file_name() == "test.fsp"


def test_check_unsaved_changes(actions_window, qtbot):
    with patch.object(actions_window, '_check_unsaved_changes',
                      new=ActionsWindow._check_unsaved_changes):
        actions_window._modified_project = False
        assert actions_window._check_unsaved_changes(actions_window)
        actions_window._modified_project = True
        with patch('PySide6.QtWidgets.QMessageBox.question') as mock_question:
            mock_question.return_value = QMessageBox.Discard
            assert actions_window._check_unsaved_changes(actions_window)
            mock_question.assert_called_once()


def test_save_project(actions_window, qtbot, sample_project, tmp_path):
    save_path = os.path.join(tmp_path, "test_save.fsp")
    actions_window.set_project(sample_project)
    actions_window._current_file = save_path
    actions_window.save_project()
    assert os.path.exists(save_path)
    assert not actions_window._modified_project
    with open(save_path, 'r') as f:
        content = json.load(f)
        assert 'project' in content
        assert 'version' in content


def test_save_project_as(actions_window, qtbot, sample_project, tmp_path):
    save_path = os.path.join(tmp_path, "test_save_as.fsp")
    actions_window.set_project(sample_project)
    with patch('PySide6.QtWidgets.QFileDialog.getSaveFileName',
               return_value=(save_path, "*.fsp")):
        actions_window.save_project_as()
    assert os.path.exists(save_path)
    assert actions_window._current_file == save_path
    assert not actions_window._modified_project


def test_open_mock_project_file(actions_window, qtbot, mock_project_file):
    with patch('PySide6.QtWidgets.QMessageBox.critical') as mock_critical:
        with patch.object(actions_window, '_check_unsaved_changes', return_value=True):
            actions_window.open_project(mock_project_file)
            mock_critical.assert_not_called()
    assert actions_window._current_file == os.path.basename(mock_project_file)
    assert not actions_window._modified_project
    assert actions_window.job_list.count() == 0
    os.unlink(mock_project_file)


def test_open_project_with_missing_paths(actions_window, qtbot, mock_project_file):
    with open(mock_project_file, 'r') as f:
        data = jsonpickle.decode(f.read())
    data['project'][0]['params'].pop('working_path', None)
    data['project'][0]['params'].pop('input_path', None)
    with open(mock_project_file, 'w') as f:
        f.write(jsonpickle.encode(data))
    with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
        with patch.object(actions_window, '_check_unsaved_changes', return_value=True):
            actions_window.open_project(mock_project_file)
            mock_warning.assert_not_called()
    os.unlink(mock_project_file)


def test_edit_action(actions_window, qtbot, sample_project):
    actions_window.set_project(sample_project)
    job = sample_project.jobs[0]
    with patch('shinestacker.gui.actions_window.ActionConfigDialog') as mock_dialog:
        mock_dialog.return_value.exec.return_value = True
        actions_window.edit_action(job)
        mock_dialog.assert_called_once()
    assert actions_window._modified_project


def test_path_methods(actions_window, sample_project):
    actions_window.set_project(sample_project)
    job = sample_project.jobs[0]
    path, name = get_action_working_path(job)
    assert path == "."
    path, name = get_action_input_path(job)
    assert path == ""
    path, name = get_action_output_path(job)
    assert path == "test"
