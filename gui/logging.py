import os
import re
import logging
from rich.logging import RichHandler
from rich.console import Console
from PySide6.QtWidgets import (QTextEdit, QApplication, QVBoxLayout, QMessageBox)
from PySide6.QtGui import (QTextCursor, QTextOption, QFont)
from PySide6.QtCore import (QThread, Signal)


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


class HtmlRichHandler(RichHandler):
    def __init__(self, text_edit):
        self.console = Console(file=open(os.devnull, "wt"), record=True, width=256, height=20, highlight=False,
                               soft_wrap=False, color_system="truecolor", tab_size=4)
        RichHandler.__init__(self, show_time=False, show_path=False, show_level=False, markup=True,
                             console=self.console)
        self.setFormatter(QtLogFormatter())
        self.text_edit = text_edit

    def emit(self, record) -> None:
        RichHandler.emit(self, record)
        indent_width = 11 * self.text_edit.fontMetrics().averageCharWidth()
        html_template = f'<p style="background-color: {{background}}; color: {{foreground}}; margin: 0; margin-left:{indent_width}px; text-indent:-{indent_width}px; white-space: pre-wrap"><code>{{code}}</code></p>' # noqa
        html = self.console.export_html(clear=True, code_format=html_template, inline_styles=True)
        self.text_edit.emit_html(html)


class QTextEditLogger(QTextEdit):
    __id_counter = 0

    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.setAcceptRichText(True)
        self.setReadOnly(True)
        font = QFont(['Menlo', 'DejaVu Sans Mono', 'consolas', 'Courier New', 'monospace'], 12, self.font().weight())
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.setFont(font)
        self.id = __class__.__id_counter
        __class__.__id_counter += 1

    def id_str(self):
        return __class__.__name__ + "_" + str(self.id)

    def emit_html(self, html):
        pattern = r'<span style="color: #00ff00; text-decoration-color: #00ff00; font-weight: bold">(\d{2}:\d{2}:\d{2})</span>'
        replacement = r'<span style="color: #008080; text-decoration-color: #008080; font-weight: bold">\1</span>'
        html = re.sub(pattern, replacement, re.sub(r'\s+[\n]', '\n', html))
        self.insertHtml(html)
        self.verticalScrollBar().setSliderPosition(self.verticalScrollBar().maximum())
        c = self.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(c)
        QApplication.processEvents()

    def handle_log_message(self, level, message):
        logger = logging.getLogger(self.id_str())
        {
            "INFO": logger.info,
            "WARNING": logger.warning,
            "DEBUG": logger.debug,
            "ERROR": logger.error,
            "CRITICAL": logger.critical,
        }[level](message)

    def handle_html_message(self, html):
        self.insertHtml(html)

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

    def last_id(self):
        return self.text_edit[-1].id

    def last_id_str(self):
        return self.text_edit[-1].id_str()

    def add_tex_edit(self, text_edit):
        self.text_edit.append(text_edit)

    def start_thread(self, worker: LogWorker):
        self.before_thread_begins()
        logger = logging.getLogger(self.last_id_str())
        logger.setLevel(logging.DEBUG)
        text_edit = self.text_edit[self.last_id()]
        self.handler = HtmlRichHandler(text_edit)
        self.handler.setLevel(logging.DEBUG)
        logger.addHandler(self.handler)
        self.log_worker = worker
        self.log_worker.log_signal.connect(text_edit.handle_log_message)
        self.log_worker.html_signal.connect(text_edit.handle_html_message)
        self.log_worker.exception_signal.connect(text_edit.handle_exception)
        self.log_worker.end_signal.connect(self.handle_end_message)
        self.log_worker.start()

    def before_thread_begins(self):
        pass

    def _do_handle_end_message(self, int):
        pass

    def handle_end_message(self, int):
        self._do_handle_end_message(int)
