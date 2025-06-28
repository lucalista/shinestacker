from config.config import config
import logging
import sys
from pathlib import Path
import re
if not config.DISABLE_TQDM:
    from tqdm import tqdm


class ConsoleFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',      # CYAN
        'INFO': '\033[32m',       # GREEN
        'WARNING': '\033[33m',    # YELLOW
        'ERROR': '\033[31m',      # RED
        'CRITICAL': '\033[31;1m'  # BOLD RED
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        return logging.Formatter(f"{color}[%(levelname).3s]{self.RESET} %(message)s").format(record)


class FileFormatter(logging.Formatter):
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def format(self, record):
        fmt = f"[%(levelname).3s %(asctime)s] %(message)s"  # noqa
        return self.ANSI_ESCAPE.sub('', logging.Formatter(fmt).format(record).replace("\r", "").rstrip())


class TqdmLoggingHandler(logging.StreamHandler):
    def emit(self, record):
        if not config.DISABLE_TQDM:
            try:
                tqdm.write(self.format(record), end=self.terminator)
            except RecursionError:
                raise
            except Exception:
                self.handleError(record)
        else:
            logging.StreamHandler.emit(self, record)


def setup_logging(console_level=logging.INFO, file_level=logging.DEBUG, log_file=None,
                  disable_console=False):
    if hasattr(setup_logging, '_called'):
        return
    setup_logging._called = True
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    if not disable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(ConsoleFormatter())
        root_logger.addHandler(console_handler)
    tqdm_logger = logging.getLogger("tqdm")
    tqdm_handler = TqdmLoggingHandler()
    tqdm_handler.setFormatter(ConsoleFormatter())
    tqdm_logger.handlers.clear()
    tqdm_logger.addHandler(tqdm_handler)
    tqdm_logger.propagate = False
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(file_level)
        file_handler.setFormatter(FileFormatter())
        root_logger.addHandler(file_handler)
        tqdm_logger.addHandler(file_handler)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.INFO)


def set_console_logging_terminator(terminator, name=None):
    logging.getLogger(name).handlers[0].terminator = terminator


def console_logging_overwrite(name=None):
    set_console_logging_terminator('\r', name)


def console_logging_newline(name=None):
    set_console_logging_terminator('\n', name)
