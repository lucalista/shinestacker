import re
import logging
from PySide6.QtWidgets import QWidget, QTextEdit, QMessageBox, QStatusBar
from PySide6.QtGui import QTextCursor, QTextOption, QFont
from PySide6.QtCore import QThread, QObject, Signal, Slot, Qt
from focusstack.config.constants import constants

LOG_FONTS = ['Monaco', 'Menlo', ' Lucida Console', 'Courier New', 'Courier', 'monospace']
LOG_FONTS_STR = ", ".join(LOG_FONTS)


class SimpleHtmlFormatter(logging.Formatter):
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    COLOR_MAP = {
        'DEBUG': '#5c85d6',    # light blue
        'INFO': '#50c878',     # green
        'WARNING': '#ffcc00',  # yellow
        'ERROR': '#ff3333',    # red
        'CRITICAL': '#cc0066'  # dark red
    }
    ANSI_COLORS = {
        # Reset
        '\x1b[0m': '</span>',
        '\x1b[m': '</span>',
        # Colori base (30-37)
        '\x1b[30m': '<span style="color:#000000">',  # black
        '\x1b[31m': '<span style="color:#ff0000">',  # red
        '\x1b[32m': '<span style="color:#00ff00">',  # green
        '\x1b[33m': '<span style="color:#ffff00">',  # yellow
        '\x1b[34m': '<span style="color:#0000ff">',  # blue
        '\x1b[35m': '<span style="color:#ff00ff">',  # magenta
        '\x1b[36m': '<span style="color:#00ffff">',  # cyan
        '\x1b[37m': '<span style="color:#ffffff">',  # white
        # Brilliant colors (90-97)
        '\x1b[90m': '<span style="color:#555555">',
        '\x1b[91m': '<span style="color:#ff5555">',
        '\x1b[92m': '<span style="color:#55ff55">',
        '\x1b[93m': '<span style="color:#ffff55">',
        '\x1b[94m': '<span style="color:#5555ff">',
        '\x1b[95m': '<span style="color:#ff55ff">',
        '\x1b[96m': '<span style="color:#55ffff">',
        '\x1b[97m': '<span style="color:#ffffff">',
        # Background (40-47)
        '\x1b[40m': '<span style="background-color:#000000">',
        '\x1b[41m': '<span style="background-color:#ff0000">',
        '\x1b[42m': '<span style="background-color:#00ff00">',
        '\x1b[43m': '<span style="background-color:#ffff00">',
        '\x1b[44m': '<span style="background-color:#0000ff">',
        '\x1b[45m': '<span style="background-color:#ff00ff">',
        '\x1b[46m': '<span style="background-color:#00ffff">',
        '\x1b[47m': '<span style="background-color:#ffffff">',
        # Styles
        '\x1b[1m': '<span style="font-weight:bold">',  # bold
        '\x1b[3m': '<span style="font-style:italic">',  # italis
        '\x1b[4m': '<span style="text-decoration:underline">',  # underline
    }

    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__()
        self._fmt = fmt or "[%(levelname).3s] %(message)s"
        self.datefmt = datefmt or "%H:%M:%S"

    def format(self, record):
        levelname = record.levelname
        message = super().format(record)
        message = message.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        for ansi_code, html_tag in self.ANSI_COLORS.items():
            message = message.replace(ansi_code, html_tag)
        message = self.ANSI_ESCAPE.sub('', message).replace("\r", "").rstrip()
        color = self.COLOR_MAP.get(levelname, '#000000')
        return f'''
        <div style="margin: 2px 0; font-family: {LOG_FONTS_STR};">
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


class GuiLogger(QWidget):
    __id_counter = 0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.id = self.__class__.__id_counter
        self.__class__.__id_counter += 1

    def id_str(self):
        return f"{self.__class__.__name__}_{self.id}"

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


class QTextEditLogger(GuiLogger):
    def __init__(self, parent=None):
        super().__init__(parent)
        text_edit = QTextEdit(self)
        text_edit.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        text_edit.setAcceptRichText(True)
        text_edit.setReadOnly(True)
        font = QFont(LOG_FONTS, 12)
        text_edit.setFont(font)
        self.text_edit = text_edit
        self.status_bar = QStatusBar()

    @Slot(str)
    def handle_html_message(self, html):
        self.append_html(html)

    @Slot(str)
    def append_html(self, html):
        self.text_edit.append(html)
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()

    @Slot(str, int, str, int)
    def handle_status_message(self, message, status, error_message, timeout):
        if status == constants.RUN_FAILED:
            QMessageBox.critical(self, "Error", f"Job failed.\n{error_message}")
        elif status == constants.RUN_STOPPED:
            QMessageBox.warning(self, "Warning", "Run stopped.")
        self.status_bar.showMessage(message, timeout)

    @Slot(str)
    def handle_exception(self, message):
        QMessageBox.warning(None, "Error", message)


class LogWorker(QThread):
    log_signal = Signal(str, str)
    html_signal = Signal(str)
    end_signal = Signal(int, str, str)
    status_signal = Signal(str, int, str, int)
    exception_signal = Signal(str)

    def run(self):
        pass


class LogManager:
    def __init__(self):
        self.gui_loggers = {}
        self.last_gui_logger = None
        self.handler = None
        self.log_worker = None
        self.id = -1

    def last_id(self):
        return self.last_gui_logger.id if self.last_gui_logger else -1

    def last_id_str(self):
        return self.last_gui_logger.id_str() if self.last_gui_logger else ""

    def add_gui_logger(self, gui_logger):
        if not isinstance(gui_logger, GuiLogger):
            raise ValueError("Only GuyLogger instances can be added")
        self.gui_loggers[gui_logger.id] = gui_logger
        self.last_gui_logger = gui_logger

    def start_thread(self, worker: LogWorker):
        if len(self.gui_loggers) == 0:
            raise RuntimeError("No text edit widgets registered")
        self.before_thread_begins()
        self.id = self.last_id()
        logger = logging.getLogger(self.last_id_str())
        logger.setLevel(logging.DEBUG)
        gui_logger = self.gui_loggers[self.id]
        self.handler = SimpleHtmlHandler()
        self.handler.setLevel(logging.DEBUG)
        logger.addHandler(self.handler)
        self.handler.log_signal.connect(gui_logger.append_html, Qt.QueuedConnection)
        self.handler.html_signal.connect(gui_logger.handle_html_message, Qt.QueuedConnection)
        self.log_worker = worker
        self.log_worker.log_signal.connect(gui_logger.handle_log_message, Qt.QueuedConnection)
        self.log_worker.html_signal.connect(gui_logger.handle_html_message, Qt.QueuedConnection)
        self.log_worker.status_signal.connect(gui_logger.handle_status_message, Qt.QueuedConnection)
        self.log_worker.exception_signal.connect(gui_logger.handle_exception, Qt.QueuedConnection)
        self.log_worker.end_signal.connect(self.handle_end_message, Qt.QueuedConnection)
        self.log_worker.start()

    def before_thread_begins(self):
        pass

    def do_handle_end_message(self, status, id_str, message):
        pass

    @Slot(int, str, str)
    def handle_end_message(self, status, id_str, message):
        self.do_handle_end_message(status, id_str, message)
