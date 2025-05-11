import logging
import sys
sys.path.append('../')
from focus_stack import setup_logging, console_logging_overwrite, console_logging_newline

def test_run():
    try:
        setup_logging(
            console_level=logging.DEBUG,
            file_level=logging.DEBUG,
            log_file="logs/focusstack.log"
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
        assert True
    except:
        assert False

if __name__ == '__main__':
    test_run()