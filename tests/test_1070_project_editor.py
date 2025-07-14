import pytest
from PySide6.QtWidgets import QMessageBox, QListWidget, QListWidgetItem
from focusstack.config.constants import constants
from focusstack.gui.project_editor import ProjectEditor, ActionPosition
from unittest.mock import MagicMock, patch


@pytest.fixture
def editor(qtbot):
    with patch('focusstack.gui.project_editor.QMainWindow.__init__'):
        editor = ProjectEditor()
        editor.job_list = MagicMock(spec=QListWidget)
        editor.action_list = MagicMock(spec=QListWidget)
        editor.job_list.currentRow.return_value = 0
        editor.job_list.hasFocus.return_value = True
        editor.list_item = MagicMock(return_value=MagicMock(spec=QListWidgetItem))
        editor.mark_as_modified = MagicMock()
        editor.add_action_entry_action = MagicMock()
        editor.action_selector = MagicMock()
        editor.run_job_action = MagicMock()
        editor.run_all_jobs_action = MagicMock()
        editor.delete_element_action = MagicMock()
        return editor


@pytest.fixture
def mock_project():
    project = MagicMock()
    job1 = MagicMock()
    job1.enabled.return_value = True
    job1.params = {'name': 'Job 1'}
    job1.sub_actions = []
    job2 = MagicMock()
    job2.enabled.return_value = False
    job2.params = {'name': 'Job 2'}
    job2.sub_actions = []
    project.jobs = [job1, job2]
    return project


def test_initial_state(editor):
    assert editor.project is None
    assert editor._copy_buffer is None
    assert editor._project_buffer == []


def test_set_project(editor, mock_project):
    editor.set_project(mock_project)
    assert editor.project == mock_project

#
# move to main_window.py test, when available
#
# def test_refresh_ui_with_jobs(editor, mock_project):
#     editor.set_project(mock_project)

#     def job_text(job):
#         txt = job.params.get('name', '(job)')
#         if not job.enabled():
#             txt += " <disabled>"
#         return txt
#     editor.job_text = job_text
#     editor.refresh_ui()
#     editor.job_list.clear.assert_called_once()
#     assert editor.list_item.call_count == 2
#     editor.list_item.assert_has_calls([
#         call("Job 1", True),
#         call("Job 2 <disabled>", False)
#     ])


@patch('focusstack.gui.project_editor.QMessageBox.question', return_value=QMessageBox.Yes)
def test_delete_job(mock_msg, editor, mock_project):
    editor.set_project(mock_project)
    editor.job_list.currentRow.return_value = 0
    original_jobs = mock_project.jobs.copy()
    mock_project.jobs = original_jobs.copy()
    editor.delete_job()
    assert len(mock_project.jobs) == 1
    mock_msg.assert_called_once()
    editor.mark_as_modified.assert_called_once()


def test_move_job_up(editor, mock_project):
    editor.set_project(mock_project)
    editor.job_list.currentRow.return_value = 1
    job1, job2 = mock_project.jobs
    mock_project.jobs = [job1, job2]
    editor.move_element_up()
    assert mock_project.jobs[0] == job2
    assert mock_project.jobs[1] == job1
    editor.mark_as_modified.assert_called_once()


def test_clone_job(editor, mock_project):
    editor.set_project(mock_project)
    editor.job_list.currentRow.return_value = 0
    cloned_job = MagicMock()
    mock_project.jobs[0].clone.return_value = cloned_job
    editor.clone_job()
    mock_project.jobs[0].clone.assert_called_once_with(" (clone)")
    assert len(mock_project.jobs) == 3
    assert mock_project.jobs[1] == cloned_job
    editor.mark_as_modified.assert_called_once()


def test_action_position_dataclass():
    actions = ['action1', 'action2']
    sub_actions = ['sub1', 'sub2']
    pos = ActionPosition(actions, None, 0)
    assert pos.action == 'action1'
    assert not pos.is_sub_action
    pos = ActionPosition(actions, sub_actions, 0, 1)
    assert pos.sub_action == 'sub2'
    assert pos.is_sub_action


@patch('focusstack.gui.project_editor.ActionConfigDialog')
def test_add_job(mock_dialog, editor):
    mock_dialog.return_value.exec.return_value = QMessageBox.Accepted
    project = MagicMock()
    project.jobs = []
    editor.set_project(project)
    editor.add_job()
    mock_dialog.assert_called_once()
    assert len(project.jobs) == 1
    editor.mark_as_modified.assert_called_once()


def test_enable_disable_job(editor, mock_project):
    editor.set_project(mock_project)
    editor.job_list.currentRow.return_value = 0
    job_mock = MagicMock()
    job_mock.enabled.return_value = True
    job_mock.params = {'name': 'Test Job'}
    job_mock.sub_actions = []
    job_mock.set_enabled = MagicMock()
    mock_project.jobs[0] = job_mock
    editor.disable()
    job_mock.set_enabled.assert_called_once_with(False)
    editor.mark_as_modified.assert_called_once()
    job_mock.set_enabled.reset_mock()
    job_mock.enabled.return_value = False
    editor.mark_as_modified.reset_mock()
    editor.enable()
    job_mock.set_enabled.assert_called_once_with(True)
    editor.mark_as_modified.assert_called_once()


def test_copy_paste_job(editor, mock_project):
    editor.set_project(mock_project)
    editor.job_list.currentRow.return_value = 0
    cloned_job = MagicMock()
    cloned_job.type_name = constants.ACTION_JOB
    mock_project.jobs[0].clone.return_value = cloned_job
    editor.copy_job()
    assert editor._copy_buffer == cloned_job
    editor.mark_as_modified.reset_mock()
    original_jobs = list(mock_project.jobs)
    mock_project.jobs = original_jobs.copy()
    editor.paste_job()
    assert len(mock_project.jobs) == 3
    assert mock_project.jobs[0] == cloned_job
    editor.mark_as_modified.assert_called_once()


def test_undo_functionality(editor):
    initial_state = MagicMock()
    initial_state.jobs = [MagicMock()]
    modified_state = MagicMock()
    modified_state.jobs = [MagicMock(), MagicMock()]
    editor.job_list = MagicMock()
    editor.action_list = MagicMock()
    editor.job_list.currentRow.return_value = 0
    editor.action_list.currentRow.return_value = 0
    editor.action_list.count.return_value = 0
    editor.set_project(modified_state)
    editor._project_buffer = [initial_state]
    editor.undo()
    assert editor.project == initial_state
