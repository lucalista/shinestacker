import pytest
import time
from unittest.mock import MagicMock, patch, Mock
from PySide6.QtWidgets import QApplication
from shinestacker.config.constants import constants
from shinestacker.gui.colors import ColorEntry
from shinestacker.common_project.run_worker import RunWorker, JobLogWorker
from shinestacker.classic_project.gui_run import (
    ColorPalette, ColorButton, TimerProgressBar, RunWindow)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestColorEntry:
    def test_color_entry(self):
        color = ColorEntry(10, 20, 30)
        assert color.tuple() == (10, 20, 30)
        assert color.hex() == "0a141e"


class TestColorPalette:
    def test_color_palette(self):
        assert ColorPalette.LIGHT_BLUE.tuple() == (210, 210, 240)


class TestColorButton:
    def test_color_button_creation(self, qapp):
        button = ColorButton("Test", True)
        assert button.text() == "Test"
        assert "background-color" in button.styleSheet()

    def test_color_button_disabled(self, qapp):
        button = ColorButton("Test", False)
        assert button.text() == "Test"
        assert "background-color" in button.styleSheet()


class TestTimerProgressBar:
    @pytest.fixture
    def progress_bar(self, qapp):
        return TimerProgressBar()

    def test_initial_state(self, progress_bar):
        assert progress_bar.value() == 0
        assert progress_bar.maximum() == 10
        assert progress_bar._status == 'pending'
        assert progress_bar._start_time == -1
        assert progress_bar._current_time == -1
        assert progress_bar.elapsed_str == ''

    def test_time_formatting(self, progress_bar):
        assert progress_bar.time_str(0.0) == "0.0s"
        assert progress_bar.time_str(0.5) == "0.5s"
        assert progress_bar.time_str(5.5) == "5.5s"
        assert progress_bar.time_str(65.5) == "1:05.5s"
        assert progress_bar.time_str(3665.5) == "1:01:05.5s"
        assert progress_bar.time_str(5.0) == "5.0s"
        assert progress_bar.time_str(60.0) == "1:00.0s"

    def test_progress_flow(self, progress_bar, monkeypatch):
        time_values = [100.0, 101.0, 101.5]
        mock_time = MagicMock()
        mock_time.side_effect = time_values
        monkeypatch.setattr(time, 'time', mock_time)
        progress_bar.start(10)
        assert progress_bar.maximum() == 10
        assert progress_bar._start_time == 100.0
        assert progress_bar._status == 'running'
        progress_bar.setValue(5)
        assert progress_bar.value() == 5
        assert progress_bar._current_time == 101.5
        assert progress_bar.elapsed_str == "1.5s"
        assert "elapsed:" in progress_bar.format()
        assert "remaining:" in progress_bar.format()
        progress_bar.stop()
        assert progress_bar._status == 'stopped'
        assert mock_time.call_count == 3

    def test_setvalue_without_start_raises_error(self, progress_bar):
        with pytest.raises(RuntimeError, match="Start and must be called before setValue and stop"):
            progress_bar.setValue(5)

    def test_done_method(self, progress_bar, monkeypatch):
        time_values = [100.0, 101.0, 105.0, 105.5]
        mock_time = MagicMock()
        mock_time.side_effect = time_values
        monkeypatch.setattr(time, 'time', mock_time)
        progress_bar.start(5)
        progress_bar.done()
        assert progress_bar.value() == 5
        assert progress_bar._status == 'done'
        assert progress_bar.elapsed_str == "5.0s"
        assert mock_time.call_count == 3

    def test_fail_method(self, progress_bar):
        progress_bar.fail()
        assert progress_bar._status == 'failed'

    def test_clear_method(self, progress_bar, monkeypatch):
        time_values = [100.0, 101.0, 101.5]
        mock_time = MagicMock()
        mock_time.side_effect = time_values
        monkeypatch.setattr(time, 'time', mock_time)
        progress_bar.start(10)
        progress_bar.setValue(5)
        progress_bar.clear()
        assert progress_bar.value() == 0
        assert progress_bar.maximum() == 10
        assert progress_bar._start_time == -1
        assert progress_bar._current_time == -1
        assert progress_bar.elapsed_str == ''
        assert progress_bar._status == 'running'
        assert mock_time.call_count == 3

    def test_check_time_logic(self, progress_bar, monkeypatch):
        time_values = [100.0, 101.0, 110.0]
        mock_time = MagicMock()
        mock_time.side_effect = time_values
        monkeypatch.setattr(time, 'time', mock_time)
        progress_bar.start(20)
        progress_bar.setValue(10)
        fmt = progress_bar.format()
        assert "elapsed: 10.0s" in fmt
        assert "remaining: 10.0s" in fmt
        assert mock_time.call_count == 3

    def test_style_methods(self, progress_bar):
        progress_bar.set_running_style()
        assert progress_bar._status == 'running'
        progress_bar.set_done_style()
        assert progress_bar._status == 'done'
        progress_bar.set_stopped_style()
        assert progress_bar._status == 'stopped'
        progress_bar.set_failed_style()
        assert progress_bar._status == 'failed'

    def test_widget_state_capture_restore(self, progress_bar, monkeypatch):
        time_values = [100.0, 101.0, 101.5, 102.0]
        mock_time = MagicMock()
        mock_time.side_effect = time_values
        monkeypatch.setattr(time, 'time', mock_time)
        progress_bar.start(20)
        progress_bar.setValue(10)
        progress_bar.setVisible(True)
        state = progress_bar.capture_widget_state()
        assert state['value'] == 10
        assert state['maximum'] == 20
        assert state['status'] == 'running'
        assert state['visible'] is True
        progress_bar.setValue(15)
        progress_bar.setVisible(False)
        progress_bar.restore_widget_state(state)
        assert progress_bar.value() == 10
        assert progress_bar.maximum() == 20
        assert progress_bar._status == 'running'
        assert progress_bar.isVisible() is True
        assert mock_time.call_count == 4


class TestRunWindow:
    @pytest.fixture
    def run_window(self, qapp):
        labels = [[("Action1", True), ("Action2", False)]]
        return RunWindow(labels, lambda x: None, None, None)

    def test_initialization(self, run_window):
        assert len(run_window.color_widgets) == 1
        assert len(run_window.color_widgets[0]) == 2
        assert run_window.color_widgets[0][0].text() == "Action1"
        assert run_window.color_widgets[0][1].text() == "Action2"

    def test_handle_signals(self, run_window):
        run_window.handle_before_action(0, "Test")
        run_window.handle_after_action(0, "Test")
        run_window.handle_step_counts(0, "Test", 10)
        run_window.handle_begin_steps(0, "Test")
        run_window.handle_after_step(0, "Test", 5)
        run_window.handle_end_steps(0, "Test")


class TestRunWorker:
    @pytest.fixture
    def run_worker(self):
        mock_job = Mock()
        worker = JobLogWorker(mock_job, "test_123")
        worker.do_run = MagicMock(return_value=(constants.RUN_COMPLETED, ""))
        return worker

    def test_signal_emission(self, run_worker):
        with patch.object(run_worker, 'before_action_signal') as mock_signal:
            run_worker.before_action(0, "Test")
            mock_signal.emit.assert_called_once_with(0, "Test")

    def test_run_process(self, run_worker):
        run_worker.run()
        assert run_worker.do_run.called

    def test_stop_behavior(self, run_worker):
        run_worker.stop()
        assert run_worker.status == constants.STATUS_STOPPED


class TestIntegration:
    @pytest.fixture
    def integrated_system(self, qapp):
        labels = [[("Action1", True)]]
        window = RunWindow(labels, lambda x: None, None, None)
        worker = RunWorker("test_id")
        worker.do_run = MagicMock(return_value=(constants.RUN_COMPLETED, ""))
        worker.before_action_signal.connect(window.handle_before_action)
        worker.after_action_signal.connect(window.handle_after_action)
        worker.step_counts_signal.connect(window.handle_step_counts)
        worker.begin_steps_signal.connect(window.handle_begin_steps)
        worker.after_step_signal.connect(window.handle_after_step)
        worker.end_steps_signal.connect(window.handle_end_steps)
        return window, worker

    def test_integrated_flow(self, integrated_system):
        window, worker = integrated_system
        worker.before_action(0, "Test")
        worker.after_action(0, "Test")
