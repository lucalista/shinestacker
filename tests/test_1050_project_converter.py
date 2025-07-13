import pytest
import os
from unittest.mock import MagicMock, patch
from focusstack.gui.project_model import Project, ActionConfig
from focusstack.algorithms.stack_framework import StackJob
from focusstack.gui.project_converter import ProjectConverter
from focusstack.config.constants import constants
from focusstack.core.exceptions import RunStopException
import logging


@pytest.fixture
def converter():
    return ProjectConverter()


@pytest.fixture
def logger():
    return logging.getLogger("test_logger")


@pytest.fixture
def real_job():
    job = MagicMock(spec=StackJob)
    job.name = "real_job"
    job.enabled = True
    job.working_path = "/tmp/test"
    job.paths = ["/tmp/test/input1.jpg", "/tmp/test/input2.jpg"]  # Simula paths configurati
    return job


def test_get_logger(converter):
    logger = converter.get_logger()
    assert isinstance(logger, logging.Logger)
    assert logger.name == "focusstack.gui.project_converter"
    custom_logger = converter.get_logger("custom_logger")
    assert custom_logger.name == "custom_logger"


def test_run_enabled_job(converter, logger):
    mock_job = MagicMock()
    mock_job.enabled = True
    mock_job.name = "test_job"
    mock_job.run.return_value = None
    status, msg = converter.run(mock_job, logger)
    assert status == constants.RUN_COMPLETED
    assert msg == ""
    mock_job.run.assert_called_once()


def test_run_disabled_job(converter, logger):
    mock_job = MagicMock()
    mock_job.enabled = False
    mock_job.name = "test_job"
    mock_job.run.return_value = None
    status, msg = converter.run(mock_job, logger)
    assert status == constants.RUN_COMPLETED
    assert msg == ""
    mock_job.run.assert_called_once()


def test_run_stopped_job(converter, logger):
    mock_job = MagicMock()
    mock_job.enabled = True
    mock_job.name = "test_job"
    mock_job.run.side_effect = RunStopException("test_job")
    status, msg = converter.run(mock_job, logger)
    assert status == constants.RUN_STOPPED
    assert msg == ""


def test_filter_dict_keys(converter):
    test_dict = {
        "prefix_key1": "value1",
        "prefix_key2": "value2",
        "other_key": "value3"
    }
    with_prefix, without_prefix = converter.filter_dict_keys(test_dict, "prefix_")
    assert with_prefix == {"key1": "value1", "key2": "value2"}
    assert without_prefix == {"other_key": "value3"}


def test_action_unsupported_type(converter):
    config = ActionConfig("UNKNOWN_TYPE", {})
    with pytest.raises(Exception, match="Cannot convert action of type UNKNOWN_TYPE."):
        converter.action(config)


def test_job_with_valid_config(converter, tmp_path):
    # Creiamo una directory temporanea valida
    working_path = str(tmp_path / "test_working")
    os.makedirs(working_path)
    config = ActionConfig(
        "JOB_TYPE",
        {
            "name": "test_job",
            "enabled": True,
            "working_path": working_path,
            "input_path": "input/path"
        }
    )
    config.sub_actions = []
    job = converter.job(config)
    assert isinstance(job, StackJob)
    assert job.name == "test_job"
    assert job.enabled is True
    assert job.working_path == working_path


def test_project_with_multiple_jobs(converter, tmp_path):
    # Creiamo directory temporanee valide
    working_path1 = str(tmp_path / "job1")
    working_path2 = str(tmp_path / "job2")
    os.makedirs(working_path1)
    os.makedirs(working_path2)
    project = Project()
    job1 = ActionConfig("JOB_TYPE", {"name": "job1", "enabled": True, "working_path": working_path1})
    job1.sub_actions = []
    job2 = ActionConfig("JOB_TYPE", {"name": "job2", "enabled": True, "working_path": working_path2})
    job2.sub_actions = []
    project.jobs = [job1, job2]
    jobs = converter.project(project)
    assert len(jobs) == 2
    assert all(isinstance(job, StackJob) for job in jobs)
    assert jobs[0].name == "job1"
    assert jobs[1].name == "job2"


def test_run_job_with_mock_job(converter, real_job):
    config = ActionConfig(
        "FOCUS_STACK_BUNCH",
        {
            "name": real_job.name,
            "enabled": real_job.enabled,
            "working_path": real_job.working_path,
        }
    )
    with patch.object(converter, 'job', return_value=real_job):
        with patch.object(converter, 'run', return_value=(constants.RUN_COMPLETED, "")):
            status, msg = converter.run_job(config)
    assert status == constants.RUN_COMPLETED
    assert msg == ""


def test_run_project(converter):
    project = Project()
    job1 = ActionConfig("JOB_TYPE", {"name": "job1", "enabled": True, "working_path": "/tmp/job1"})
    job1.sub_actions = []
    job2 = ActionConfig("JOB_TYPE", {"name": "job2", "enabled": True, "working_path": "/tmp/job2"})
    job2.sub_actions = []
    project.jobs = [job1, job2]
    with patch.object(converter, 'project', return_value=[MagicMock(), MagicMock()]) as mock_project:
        with patch.object(converter, 'run', side_effect=[(constants.RUN_COMPLETED, ""), (constants.RUN_COMPLETED, "")]):
            status, msg = converter.run_project(project)
    assert status == constants.RUN_COMPLETED
    assert msg == ""
    assert mock_project.call_count == 1
