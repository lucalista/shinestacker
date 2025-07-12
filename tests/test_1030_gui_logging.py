import pytest
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from focusstack.gui.gui_logging import (SimpleHtmlFormatter, SimpleHtmlHandler,
                                        GuiLogger, QTextEditLogger, LogManager, LogWorker)


@pytest.fixture
def app(qtbot):
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


@pytest.fixture
def text_edit_logger(qtbot):
    logger = QTextEditLogger()
    qtbot.addWidget(logger.text_edit)
    return logger


@pytest.fixture
def log_manager():
    return LogManager()


def test_simple_html_formatter():
    formatter = SimpleHtmlFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=None,
        exc_info=None
    )    
    formatted = formatter.format(record)
    assert "[INF]" in formatted
    assert "Test message" in formatted
    assert "color: #50c878" in formatted  # Colore per INFO
    assert "font-family" in formatted


def test_simple_html_handler(qtbot, text_edit_logger):
    handler = SimpleHtmlHandler()
    handler.html_signal.connect(text_edit_logger.handle_html_message)
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg="Warning message",
        args=None,
        exc_info=None
    )
    with qtbot.waitSignal(handler.html_signal, timeout=1000):
        handler.emit(record)
    assert "[WAR]" in text_edit_logger.text_edit.toPlainText()
    assert "Warning message" in text_edit_logger.text_edit.toPlainText()


def test_gui_logger_handle_log_message(caplog):
    gui_logger = GuiLogger()
    logger_name = gui_logger.id_str()
    with caplog.at_level(logging.INFO):
        gui_logger.handle_log_message("INFO", "Test info message")
    assert len(caplog.records) == 1
    assert caplog.records[0].name == logger_name
    assert caplog.records[0].message == "Test info message"
    assert caplog.records[0].levelname == "INFO"


def test_text_edit_logger_append_html(qtbot, text_edit_logger):
    html_content = "<div>Test HTML content</div>"
    with qtbot.waitSignal(text_edit_logger.text_edit.textChanged, timeout=1000):
        text_edit_logger.append_html(html_content)
    assert "Test HTML content" in text_edit_logger.text_edit.toHtml()


def test_log_manager_add_gui_logger(log_manager):
    gui_logger = GuiLogger()
    log_manager.add_gui_logger(gui_logger)    
    assert len(log_manager.gui_loggers) == 1
    assert log_manager.last_gui_logger == gui_logger


def test_log_manager_start_thread(qtbot, log_manager, text_edit_logger):
    log_manager.add_gui_logger(text_edit_logger)
    worker = LogWorker()
    def mock_run():
        worker.html_signal.emit("<div>Test message from worker</div>")
        worker.log_signal.emit("INFO", "Test log message")
    worker.run = mock_run
    log_manager.start_thread(worker)
    qtbot.waitUntil(lambda: "Test message from worker" in text_edit_logger.text_edit.toHtml(), timeout=1000)
    logger = logging.getLogger(text_edit_logger.id_str())
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], SimpleHtmlHandler)


def test_log_manager_handle_end_message(log_manager):
    class TestLogManager(LogManager):
        def do_handle_end_message(self, status, id_str, message):
            self.end_status = status
            self.end_id_str = id_str
            self.end_message = message    
    test_manager = TestLogManager()
    gui_logger = GuiLogger()
    test_manager.add_gui_logger(gui_logger)
    test_manager.handle_end_message(1, "test_id", "Test end message")
    assert hasattr(test_manager, 'end_status')
    assert test_manager.end_status == 1
    assert test_manager.end_id_str == "test_id"
    assert test_manager.end_message == "Test end message"
