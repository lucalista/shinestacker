import logging
import sys
from pathlib import Path

class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',     # CYAN
        'INFO': '\033[32m',      # GREEN
        'WARNING': '\033[33m',   # YELLOW
        'ERROR': '\033[31m',     # RED
        'CRITICAL': '\033[31;1m' # BOLD RED
    }
    RESET = '\033[0m'
    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        fmt = f"{color}[%(levelname).3s %(asctime)s]{self.RESET} %(message)s"
        return logging.Formatter(fmt).format(record)

def setup_logging(
    console_level=logging.INFO,
    file_level=logging.DEBUG,
    log_file=None
):
    if hasattr(setup_logging, '_called'):
        return
    setup_logging._called = True
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(ColorFormatter())
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(file_level)
        file_handler.setFormatter(
            logging.Formatter("[%(levelname).3s %(asctime)s] %(name)s: %(message)s")
        )
        root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.INFO)