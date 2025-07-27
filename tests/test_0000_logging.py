import logging
import time
from tqdm import tqdm
from tqdm.notebook import tqdm_notebook
from shinestacker.config.config import config
from shinestacker.config.constants import constants
from shinestacker.core.logging import setup_logging, console_logging_overwrite, console_logging_newline


def test_log():
    try:
        setup_logging(
            console_level=logging.DEBUG,
            file_level=logging.DEBUG,
            log_file=f"logs/{constants.APP_STRING.lower()}.log"
        )
        logger = logging.getLogger(__name__)
        logger.info('Started')
        logger.debug('pi = 3.14')
        logger.warning('warning...!')
        logger.error('crash...!')
        logger.critical('stop...!')
        logger.info('\033[32mcolored message, b&w on log file\033[0m')
        console_logging_overwrite()
        logger.info('this message is in log file only')
        console_logging_newline()
        logger.info('this message is in log file and on console')
        logger.info('Finished')
    except Exception:
        assert False


def test_tqdm():
    if config.DISABLE_TQDM:
        return True
    try:
        setup_logging(
            console_level=logging.DEBUG,
            file_level=logging.DEBUG,
            log_file=f"logs/{constants.APP_STRING.lower()}.log"
        )
        logger = logging.getLogger("tqdm")
        counts = 50
        try:
            __IPYTHON__  # noqa
            bar = tqdm_notebook(desc="progress bar", total=counts, position=0)
            descr = tqdm_notebook(total=counts, position=1, bar_format='{desc}')
        except Exception:
            bar = tqdm(desc="progress bar", total=counts, position=0)
            descr = tqdm(total=counts, position=1, bar_format='{desc}')
        for i in range(counts):
            if i % 5 == 0:
                logger.log(logging.INFO, f"\033[AStep: {i}")
                descr.set_description_str(f"Step: {i}")
            bar.update(1)
            time.sleep(0.02)
        descr.set_description_str("")
        bar.close()
        logger.info('Finished')
    except Exception:
        assert False


if __name__ == '__main__':
    test_log()
    test_tqdm()
