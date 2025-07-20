import pytest
import time
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
from focusstack.gui.colors import ColorEntry
from focusstack.gui.gui_run import (ColorPalette, ColorButton,
                                    TimerProgressBar, RunWindow, RunWorker, constants)


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
        qcolor = color.q_color()
        assert qcolor.red() == 10
        assert qcolor.green() == 20
        assert qcolor.blue() == 30


class TestColorPalette:
    def test_color_palette(self):
        assert ColorPalette.BLACK.tuple() == (0, 0, 0)
        assert ColorPalette.WHITE.tuple() == (255, 255, 255)
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

    def test_time_formatting(self, progress_bar):
        assert progress_bar.time_str(0.5) == "0.5s"
        assert progress_bar.time_str(5.5) == "5.5s"
        assert progress_bar.time_str(65.5) == "1:05.5s"
        assert progress_bar.time_str(3665.5) == "1:01:05.5s"

    def test_progress_flow(self, progress_bar, monkeypatch):
        time_values = [100.0, 101.5, 103.0, 104.0, 105.0]
        mock_time = MagicMock()
        mock_time.side_effect = time_values
        monkeypatch.setattr(time, 'time', mock_time)
        progress_bar.start(10)
        progress_bar.setValue(5)
        progress_bar.stop()
        # Verifica che siano stati usati tutti i valori mockati
        assert mock_time.call_count == len(time_values)
        assert "elapsed:" in progress_bar.format()


class TestRunWindow:
    @pytest.fixture
    def run_window(self, qapp):
        labels = [[("Action1", True), ("Action2", False)]]
        return RunWindow(labels, lambda x: None, lambda x: None, None, None)

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
        worker = RunWorker("test_id")
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
        window = RunWindow(labels, lambda x: None, lambda x: None, None, None)
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
