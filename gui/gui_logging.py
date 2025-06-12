import os
import re
import logging
from rich.logging import RichHandler
from rich.console import Console
from PySide6.QtWidgets import QTextEdit, QMessageBox
from PySide6.QtGui import QTextCursor, QTextOption, QFont
from PySide6.QtCore import QThread, QObject, Signal, Slot, Qt


class QtLogFormatter(logging.Formatter):
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    COLORS = {
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red bold'
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        fmt = f"[blue3][[{color}]%(levelname).3s[/] %(asctime)s] %(message)s[/]"  # noqa
        return self.ANSI_ESCAPE.sub('', logging.Formatter(fmt).format(record).replace("\r", "").rstrip())


class HtmlRichHandler(RichHandler, QObject):
    html_ready = Signal(str)

    def __init__(self, text_edit):
        QObject.__init__(self)
        RichHandler.__init__(self, show_time=False, show_path=False, show_level=False,
                             markup=True, console=self._create_console())
        self.text_edit = text_edit
        self.setFormatter(QtLogFormatter())
        print(type(self.html_ready))
        self.html_ready.connect(self.text_edit.handle_html_message, Qt.ConnectionType.QueuedConnection)

    def _create_console(self):
        return Console(file=open(os.devnull, "wt"), record=True,
                       width=256, height=20, highlight=False, soft_wrap=False,
                       color_system="truecolor", tab_size=4)

    def emit(self, record):
        try:
            super().emit(record)
            indent_width = 11 * self.text_edit.fontMetrics().averageCharWidth()
            html_template = f'<p style="background-color: {{background}}; color: {{foreground}}; margin: 0; margin-left:{indent_width}px; text-indent:-{indent_width}px; white-space: pre-wrap"><code>{{code}}</code></p>' # noqa
            html = self.console.export_html(clear=True, code_format=html_template, inline_styles=True)
            processed_html = self._process_html(html)
            # Emette il segnale dall'istanza
            self.html_ready.emit(processed_html)
        except Exception as e:
            logging.error(f"Error in HTML log handler: {str(e)}")

    def _process_html(self, html):
        pattern = r'<span style="color: #00ff00; text-decoration-color: #00ff00; font-weight: bold">(\d{2}:\d{2}:\d{2})</span>'
        replacement = r'<span style="color: #008080; text-decoration-color: #008080; font-weight: bold">\1</span>'
        return re.sub(pattern, replacement, re.sub(r'\s+[\n]', '\n', html))


class QTextEditLogger(QTextEdit):
    __id_counter = 0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.setAcceptRichText(True)
        self.setReadOnly(True)
        font = QFont(['Menlo', 'DejaVu Sans Mono', 'consolas', 'Courier New', 'monospace'], 12)
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.setFont(font)
        self.id = self.__class__.__id_counter
        self.__class__.__id_counter += 1

    def id_str(self):
        return f"{self.__class__.__name__}_{self.id}"

    @Slot(str)
    def handle_html_message(self, html):
        self.insertHtml(html)
        self.ensureCursorVisible()

    def ensureCursorVisible(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

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
        pass


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
        self.handler = HtmlRichHandler(text_edit)
        self.handler.setLevel(logging.DEBUG)
        logger.addHandler(self.handler)
        self.log_worker = worker
        self.log_worker.log_signal.connect(
            text_edit.handle_log_message,
            Qt.QueuedConnection
        )
        self.log_worker.html_signal.connect(
            text_edit.handle_html_message,
            Qt.QueuedConnection
        )
        self.log_worker.exception_signal.connect(
            text_edit.handle_exception,
            Qt.QueuedConnection
        )
        self.log_worker.end_signal.connect(
            self.handle_end_message,
            Qt.QueuedConnection
        )
        self.log_worker.start()

    def before_thread_begins(self):
        pass

    def _do_handle_end_message(self, status):
        pass

    @Slot(int)
    def handle_end_message(self, status):
        self._do_handle_end_message(status)
