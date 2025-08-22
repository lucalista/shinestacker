# pylint: disable=C0114, C0115, C0116, E0611, W0212, R0903
import logging
from PySide6.QtWidgets import QWidget, QTextEdit, QMessageBox, QStatusBar
from PySide6.QtGui import QTextCursor, QTextOption, QFont
from PySide6.QtCore import QThread, QObject, Signal, Slot, Qt
from .. config.constants import constants


class SimpleHtmlFormatter(logging.Formatter):
    COLOR_MAP = {
        'DEBUG': '#5c85d6',    # light blue
        'INFO': '#50c878',     # green
        'WARNING': '#ffcc00',  # yellow
        'ERROR': '#ff3333',    # red
        'CRITICAL': '#cc0066'  # dark red
    }
    FF = '80'
    OO = '00'
    MM = '40'
    GG = 'FF'
    ANSI_COLORS = {
        # Reset
        '\x1b[0m': '</span>',
        '\x1b[m': '</span>',
        # Colori base (30-37)
        '\x1b[30m': f'<span style="color:#{OO}{OO}{OO}">',  # black
        '\x1b[31m': f'<span style="color:#{FF}{OO}{OO}">',  # red
        '\x1b[32m': f'<span style="color:#{OO}{FF}{OO}">',  # green
        '\x1b[33m': f'<span style="color:#{FF}{FF}{OO}">',  # yellow
        '\x1b[34m': f'<span style="color:#{OO}{OO}{FF}">',  # blue
        '\x1b[35m': f'<span style="color:#{FF}{OO}{FF}">',  # magenta
        '\x1b[36m': f'<span style="color:#{OO}{FF}{FF}">',  # cyan
        '\x1b[37m': f'<span style="color:#{FF}{FF}{FF}">',  # white
        # Brilliant colors (90-97)
        '\x1b[90m': f'<span style="color:#{MM}{MM}{MM}">',
        '\x1b[91m': f'<span style="color:#{GG}{MM}{MM}">',
        '\x1b[92m': f'<span style="color:#{MM}{GG}{MM}">',
        '\x1b[93m': f'<span style="color:#{GG}{GG}{MM}">',
        '\x1b[94m': f'<span style="color:#{MM}{MM}{GG}">',
        '\x1b[95m': f'<span style="color:#{GG}{MM}{GG}">',
        '\x1b[96m': f'<span style="color:#{MM}{GG}{GG}">',
        '\x1b[97m': f'<span style="color:#{GG}{GG}{GG}">',
        # Background (40-47)
        '\x1b[40m': f'<span style="background-color:#{OO}{OO}{OO}">',
        '\x1b[41m': f'<span style="background-color:#{FF}{OO}{OO}">',
        '\x1b[42m': f'<span style="background-color:#{OO}{FF}{OO}">',
        '\x1b[43m': f'<span style="background-color:#{FF}{FF}{OO}">',
        '\x1b[44m': f'<span style="background-color:#{OO}{OO}{FF}">',
        '\x1b[45m': f'<span style="background-color:#{FF}{OO}{FF}">',
        '\x1b[46m': f'<span style="background-color:#{OO}{FF}{FF}">',
        '\x1b[47m': f'<span style="background-color:#{FF}{FF}{FF}">',
        # Styles
        '\x1b[1m': '<span style="font-weight:bold">',  # bold
        '\x1b[3m': '<span style="font-style:italic">',  # italis
        '\x1b[4m': '<span style="text-decoration:underline">',  # underline
    }

    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__()
        self.datefmt = datefmt or "%H:%M:%S"

    def format(self, record):
        levelname = record.levelname
        message = super().format(record)
        message = message.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        for ansi_code, html_tag in self.ANSI_COLORS.items():
            message = message.replace(ansi_code, html_tag)
        message = constants.ANSI_ESCAPE.sub('', message).replace("\r", "").rstrip()
        color = self.COLOR_MAP.get(levelname, '#000000')
        return f'''
        <div style="margin: 2px 0; font-family: {constants.LOG_FONTS_STR};">
            <span style="color: {color}; font-weight: bold;">[{levelname[:3]}] </span>
            <span>{message}</span>
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
            self.html_signal.emit(msg)
        except RuntimeError as e:
            logging.error(msg=f"Logging error: {e}")


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
        font = QFont(constants.LOG_FONTS, 12)
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

    def add_gui_logger(self, gui_logger: GuiLogger):
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
