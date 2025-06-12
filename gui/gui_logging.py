import re
import logging
from PySide6.QtWidgets import QTextEdit, QMessageBox
from PySide6.QtGui import QTextCursor, QTextOption, QFont
from PySide6.QtCore import QThread, QObject, Signal, Slot, Qt
from ansi2html import Ansi2HTMLConverter


class SimpleHtmlFormatter(logging.Formatter):
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    COLOR_MAP = {
        'DEBUG': '#5c85d6',    # Blu chiaro
        'INFO': '#50c878',     # Verde
        'WARNING': '#ffcc00',  # Giallo
        'ERROR': '#ff3333',    # Rosso
        'CRITICAL': '#cc0066'  # Rosso scuro
    }

    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__()
        self._fmt = fmt or "[%(levelname).3s] %(message)s"
        self.datefmt = datefmt or "%H:%M:%S"

    def format(self, record):
        levelname = record.levelname
        message = super().format(record)
        converter = Ansi2HTMLConverter(inline=True, scheme="solarized")
        message = message.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        message = converter.convert(message, full=False)
        message = self.ANSI_ESCAPE.sub('', message).replace("\r", "").rstrip()
        color = self.COLOR_MAP.get(levelname, '#000000')
        return f'''
        <div style="margin: 2px 0; font-family: monospace;">
            <span style="color: {color}; font-weight: bold;">[{levelname[:3]}]</span>
            <span> {message}</span>
        </div>
        '''


class SimpleHtmlHandler(QObject, logging.Handler):
    log_signal = Signal(str)
    html_signal = Signal(str)

    def __init__(self):
        QObject.__init__(self)
        logging.Handler.__init__(self)
        self.setFormatter(SimpleHtmlFormatter())

    def emit(self, record):
        try:
            msg = self.format(record)
            # self.log_signal.emit(msg)
            self.html_signal.emit(msg)
        except Exception as e:
            logging.error(f"Logging error: {e}")


class QTextEditLogger(QTextEdit):
    __id_counter = 0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.id = self.__class__.__id_counter
        self.__class__.__id_counter += 1

    def setup_ui(self):
        self.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.setAcceptRichText(True)
        self.setReadOnly(True)
        font = QFont(['Courier New', 'monospace'], 14)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

    def id_str(self):
        return f"{self.__class__.__name__}_{self.id}"

    @Slot(str)
    def handle_html_message(self, html):
        self.append_html(html)

    @Slot(str)
    def append_html(self, html):
        self.append(html)
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    @Slot(str, str)
    def handle_log_message(self, level, message):
        logger = logging.getLogger(self.id_str())
        log_func = {
            "INFO": logger.info,
            "WARNING": logger.warning,
            "DEBUG": logger.debug,
            "ERROR": logger.error,
            "CRITICAL": logger.critical,
        }.get(level, logger.info)
        log_func(message)

    @Slot(str)
    def handle_exception(self, message):
        QMessageBox.warning(None, "Error", message)


class LogWorker(QThread):
    log_signal = Signal(str, str)
    html_signal = Signal(str)
    end_signal = Signal(int)
    exception_signal = Signal(str)

    def run(self):
        pass  # Implement your thread logic here


class LogManager:
    def __init__(self):
        self.text_edit = []
        self.handler = None
        self.log_worker = None

    def last_id(self):
        return self.text_edit[-1].id if self.text_edit else -1

    def last_id_str(self):
        return self.text_edit[-1].id_str() if self.text_edit else ""

    def add_text_edit(self, text_edit):
        if not isinstance(text_edit, QTextEditLogger):
            raise ValueError("Only QTextEditLogger instances can be added")
        self.text_edit.append(text_edit)

    def start_thread(self, worker: LogWorker):
        if not self.text_edit:
            raise RuntimeError("No text edit widgets registered")
        self.before_thread_begins()
        logger = logging.getLogger(self.last_id_str())
        logger.setLevel(logging.DEBUG)
        text_edit = self.text_edit[self.last_id()]
        self.handler = SimpleHtmlHandler()
        self.handler.setLevel(logging.DEBUG)
        logger.addHandler(self.handler)
        self.handler.log_signal.connect(text_edit.append_html, Qt.QueuedConnection)
        self.handler.html_signal.connect(text_edit.handle_html_message, Qt.QueuedConnection)
        self.log_worker = worker
        self.log_worker.log_signal.connect(text_edit.handle_log_message, Qt.QueuedConnection)
        self.log_worker.html_signal.connect(text_edit.handle_html_message, Qt.QueuedConnection)
        self.log_worker.exception_signal.connect(text_edit.handle_exception, Qt.QueuedConnection)
        self.log_worker.end_signal.connect(self.handle_end_message, Qt.QueuedConnection)
        self.log_worker.start()

    def before_thread_begins(self):
        pass

    def _do_handle_end_message(self, status):
        pass

    @Slot(int)
    def handle_end_message(self, status):
        self._do_handle_end_message(status)
