import pytest
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QMessageBox
from shinestacker.gui.project_editor import (
    ProjectEditor,
    ActionPosition,
    constants,
    new_row_after_delete,
    new_row_after_insert,
    new_row_after_paste,
    new_row_after_clone
)


@pytest.fixture
def project_editor(qtbot):
    editor = ProjectEditor()
    editor._project = Mock()
    editor._project.jobs = []
    editor._project.clone.return_value = Mock()
    editor._job_list = QListWidget()
    editor._action_list = QListWidget()
    editor.parent = Mock()
    return editor


@pytest.fixture
def mock_job():
    job = Mock()
    job.params = {"name": "Test Job"}
    job.type_name = constants.ACTION_JOB
    job.sub_actions = []
    job.enabled.return_value = True
    job.set_enabled = Mock()
    job.clone.return_value = job
    job.pop_sub_action = Mock()
    return job


@pytest.fixture
def mock_action():
    action = Mock()
    action.params = {"name": "Test Action"}
    action.type_name = constants.ACTION_COMBO
    action.sub_actions = []
    action.enabled.return_value = True
    action.set_enabled = Mock()
    action.clone.return_value = action
    action.pop_sub_action = Mock()
    action.add_sub_action = Mock()
    action.parent = None
    return action


@pytest.fixture
def mock_sub_action():
    sub_action = Mock()
    sub_action.params = {"name": "Test Sub Action"}
    sub_action.type_name = constants.ACTION_NOISEDETECTION
    sub_action.sub_actions = []
    sub_action.enabled.return_value = True
    sub_action.set_enabled = Mock()
    sub_action.clone.return_value = sub_action
    sub_action.parent = None
    return sub_action


def test_action_position_properties():
    actions = [Mock(), Mock()]
    sub_actions = [Mock(), Mock()]
    pos = ActionPosition(actions, sub_actions, 1, 0)
    assert pos.is_sub_action
    assert pos.action == actions[1]
    assert pos.sub_action == sub_actions[0]


def test_new_row_after_delete():
    actions = [Mock()]
    actions[0].sub_actions = [Mock()]
    pos = ActionPosition(actions, actions[0].sub_actions, 0, 0)
    assert new_row_after_delete(5, pos) == 5


def test_mark_as_modified(project_editor):
    project_editor.mark_as_modified(True)
    assert project_editor.modified()
    assert not project_editor.empty_undo()


def test_shift_job(project_editor, mock_job):
    job1, job2, job3 = Mock(), Mock(), Mock()
    job1.name, job2.name, job3.name = "job1", "job2", "job3"
    project_editor._project.jobs = [job1, job2, job3]
    for i in range(3):
        project_editor._job_list.addItem(QListWidgetItem(f"Job {i}"))
    project_editor.set_current_job(1)
    project_editor.shift_job(-1)
    assert project_editor._project.jobs[0].name == "job2"
    assert project_editor.modified()


def test_shift_action_fail(project_editor, mock_job, mock_action):
    mock_job.sub_actions = [mock_action]
    project_editor._project.jobs = [mock_job]
    project_editor._job_list.addItem(QListWidgetItem("Test Job"))
    project_editor.set_current_job(0)
    project_editor._action_list.addItem(QListWidgetItem("Test Action"))
    project_editor.set_current_action(0)
    pos = Mock()
    pos.actions = mock_job.sub_actions
    pos.is_sub_action = False
    pos.action_index = 0
    with patch.object(project_editor, 'get_current_action', return_value=(0, 0, pos)):
        project_editor.shift_action(-1)
        assert not project_editor.modified()


def test_delete_job(project_editor, mock_job):
    project_editor._project.jobs = [mock_job]
    project_editor._job_list.addItem(QListWidgetItem("Test Job"))
    project_editor.set_current_job(0)
    with patch('shinestacker.gui.project_editor.QMessageBox.question',
               return_value=QMessageBox.Yes):
        result = project_editor.delete_job()
        assert result == mock_job
        assert len(project_editor._project.jobs) == 0


def test_delete_action(project_editor, mock_job, mock_action):
    mock_job.sub_actions = [mock_action]
    project_editor._project.jobs = [mock_job]
    project_editor._job_list.addItem(QListWidgetItem("Test Job"))
    project_editor.set_current_job(0)
    project_editor._action_list.addItem(QListWidgetItem("Test Action"))
    project_editor.set_current_action(0)
    pos = Mock()
    pos.actions = mock_job.sub_actions
    pos.is_sub_action = False
    pos.action_index = 0
    pos.action = mock_action
    with patch.object(project_editor, 'get_current_action', return_value=(0, 0, pos)):
        with patch('shinestacker.gui.project_editor.QMessageBox.question',
                   return_value=QMessageBox.Yes):
            result = project_editor.delete_action()
            assert result == mock_action
            assert project_editor.modified()


def test_clone_job(project_editor, mock_job):
    project_editor._project.jobs = [mock_job]
    project_editor._job_list.addItem(QListWidgetItem("Test Job"))
    project_editor.set_current_job(0)
    project_editor.clone_job()
    assert len(project_editor._project.jobs) == 2
    assert project_editor.modified()


def test_clone_action(project_editor, mock_job, mock_action):
    mock_job.sub_actions = [mock_action]
    project_editor._project.jobs = [mock_job]
    project_editor._job_list.addItem(QListWidgetItem("Test Job"))
    project_editor.set_current_job(0)
    project_editor._action_list.addItem(QListWidgetItem("Test Action"))
    project_editor.set_current_action(0)
    pos = Mock()
    pos.actions = mock_job.sub_actions
    pos.is_sub_action = False
    pos.action_index = 0
    pos.action = mock_action
    with patch.object(project_editor, 'get_current_action', return_value=(0, 0, pos)):
        with patch('shinestacker.gui.project_editor.new_row_after_clone', return_value=1):
            project_editor.clone_action()
            assert len(mock_job.sub_actions) == 2
            assert project_editor.modified()


def test_copy_paste_job(project_editor, mock_job):
    project_editor._project.jobs = [mock_job]
    project_editor._job_list.addItem(QListWidgetItem("Test Job"))
    project_editor.set_current_job(0)
    project_editor.copy_job()
    assert project_editor.copy_buffer() is not None
    project_editor.paste_job()
    assert len(project_editor._project.jobs) == 2
    assert project_editor.modified()


def test_copy_paste_action(project_editor, mock_job, mock_action):
    mock_job.sub_actions = [mock_action]
    project_editor._project.jobs = [mock_job]
    project_editor._job_list.addItem(QListWidgetItem("Test Job"))
    project_editor.set_current_job(0)
    project_editor._action_list.addItem(QListWidgetItem("Test Action"))
    project_editor.set_current_action(0)
    pos = Mock()
    pos.actions = mock_job.sub_actions
    pos.is_sub_action = False
    pos.action_index = 0
    pos.action = mock_action
    with patch.object(project_editor, 'get_current_action', return_value=(0, 0, pos)):
        project_editor.copy_action()
        assert project_editor.copy_buffer() is not None
        project_editor.paste_action()
        assert len(mock_job.sub_actions) == 2
        assert project_editor.modified()


def test_set_enabled(project_editor, mock_job):
    project_editor._project.jobs = [mock_job]
    project_editor._job_list.addItem(QListWidgetItem("Test Job"))
    project_editor.set_current_job(0)
    with patch.object(project_editor, 'job_list_has_focus', return_value=True):
        project_editor.set_enabled(False)
        mock_job.set_enabled.assert_called_with(False)
        assert project_editor.modified()


def test_set_enabled_all(project_editor, mock_job, mock_action):
    mock_job.sub_actions = [mock_action]
    mock_job.set_enabled_all = Mock()
    project_editor._project.jobs = [mock_job]
    project_editor._job_list.addItem(QListWidgetItem("Test Job"))
    project_editor.set_current_job(0)
    project_editor.set_enabled_all(False)
    mock_job.set_enabled_all.assert_called_with(False)
    assert project_editor.modified()


def test_on_job_selected(project_editor, mock_job, mock_action, mock_sub_action):
    mock_action.sub_actions = [mock_sub_action]
    mock_job.sub_actions = [mock_action]
    project_editor._project.jobs = [mock_job]
    project_editor._job_list.addItem(QListWidgetItem("Test Job"))
    project_editor.on_job_selected(0)
    assert project_editor._action_list.count() == 2


def test_get_current_action_at(project_editor, mock_job, mock_action, mock_sub_action):
    mock_action.sub_actions = [mock_sub_action]
    mock_job.sub_actions = [mock_action]
    action, is_sub = project_editor.get_current_action_at(mock_job, 0)
    assert action == mock_action
    assert not is_sub
    action, is_sub = project_editor.get_current_action_at(mock_job, 1)
    assert action == mock_sub_action
    assert is_sub


def test_new_row_after_insert():
    actions = [Mock(), Mock()]
    actions[0].sub_actions = []
    actions[1].sub_actions = []
    pos = ActionPosition(actions, None, 0)  # Not a sub_action
    result = new_row_after_insert(0, pos, 1)
    assert isinstance(result, int)


def test_new_row_after_paste():
    actions = [Mock()]
    actions[0].sub_actions = [Mock()]
    pos = ActionPosition(actions, actions[0].sub_actions, 0, 0)
    result = new_row_after_paste(5, pos)
    assert result == new_row_after_insert(5, pos, 0)


def test_new_row_after_clone():
    job = Mock()
    action1 = Mock()
    action1.sub_actions = []
    action2 = Mock()
    action2.sub_actions = []
    job.sub_actions = [action1, action2]
    cloned = action2
    result = new_row_after_clone(job, 0, False, cloned)
    assert isinstance(result, int)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
