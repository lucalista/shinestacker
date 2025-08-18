# pylint: disable=C0114, C0115, C0116, R0917, R0913, R0902
import time
import logging
from .. config.constants import constants
from .. config.config import config
from .colors import color_str
from .logging import setup_logging
from .core_utils import make_tqdm_bar
from .exceptions import RunStopException

LINE_UP = "\r\033[A"
TRAILING_SPACES = " " * 30


class TqdmCallbacks:
    _instance = None

    callbacks = {
        'step_counts': lambda id, name, counts: TqdmCallbacks.instance().step_counts(name, counts),
        'begin_steps': lambda id, name: TqdmCallbacks.instance().begin_steps(name),
        'end_steps': lambda id, name: TqdmCallbacks.instance().end_steps(),
        'after_step': lambda id, name, steps: TqdmCallbacks.instance().after_step()
    }

    def __init__(self):
        self.tbar = None
        self.counts = -1

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = TqdmCallbacks()
        return cls._instance

    def step_counts(self, name, counts):
        self.counts = counts
        self.tbar = make_tqdm_bar(name, self.counts)

    def begin_steps(self, name):
        pass

    def end_steps(self):
        if self.tbar is None:
            raise RuntimeError("tqdm bar not initialized")
        self.tbar.close()
        self.tbar = None

    def after_step(self):
        self.tbar.write("")
        self.tbar.update(1)


tqdm_callbacks = TqdmCallbacks()


def elapsed_time_str(start):
    dt = time.time() - start
    mm = int(dt // 60)
    ss = dt - mm * 60
    hh = mm // 60
    mm -= hh * 60
    return f"{hh:02d}:{mm:02d}:{ss:05.2f}s"


class JobBase:
    def __init__(self, name, enabled=True):
        self.id = -1
        self.name = name
        self.enabled = enabled
        self.base_message = ''
        self.logger = None
        self._t0 = None
        self.callbacks = None
        if config.JUPYTER_NOTEBOOK:
            self.begin_r, self.end_r = "", "\r"
        else:
            self.begin_r, self.end_r = LINE_UP, None

    def callback(self, key, *args):
        has_callbacks = hasattr(self, 'callbacks')
        if has_callbacks and self.callbacks is not None:
            callback = self.callbacks.get(key, None)
            if callback:
                return callback(*args)
        return None

    def run_core(self):
        pass

    def run(self):
        self._t0 = time.time()
        if not self.enabled:
            self.get_logger().warning(color_str(self.name + ": entire job disabled",
                                                constants.LOG_COLOR_ALERT))
        self.callback('before_action', self.id, self.name)
        self.run_core()
        self.callback('after_action', self.id, self.name)
        msg_name = color_str(self.name + ":", constants.LOG_COLOR_LEVEL_JOB, "bold")
        msg_time = color_str(f"elapsed time: {elapsed_time_str(self._t0)}",
                             constants.LOG_COLOR_LEVEL_JOB)
        msg_completed = color_str("completed", constants.LOG_COLOR_LEVEL_JOB)
        self.get_logger().info(msg=f"{msg_name} {msg_time}{TRAILING_SPACES}")
        self.get_logger().info(msg=f"{msg_name} {msg_completed}{TRAILING_SPACES}")

    def get_logger(self, tqdm=False):
        if config.DISABLE_TQDM:
            tqdm = False
        if self.logger is None:
            return logging.getLogger("tqdm" if tqdm else __name__)
        return self.logger

    def set_terminator(self, tqdm=False, end='\n'):
        if config.DISABLE_TQDM:
            tqdm = False
        if end is not None:
            logging.getLogger("tqdm" if tqdm else None).handlers[0].terminator = end

    def print_message(self, msg='', level=logging.INFO, end=None, begin='', tqdm=False):
        if config.DISABLE_TQDM:
            tqdm = False
        self.base_message = color_str(self.name, constants.LOG_COLOR_LEVEL_1, "bold")
        if msg != '':
            self.base_message += (': ' + msg)
        self.set_terminator(tqdm, end)
        col_str = color_str(self.base_message, constants.LOG_COLOR_LEVEL_1, "bold")
        self.get_logger(tqdm).log(
            level=level,
            msg=f"{begin}{col_str}{TRAILING_SPACES}"
        )
        self.set_terminator(tqdm)

    def sub_message(self, msg, level=logging.INFO, end=None, begin='', tqdm=False):
        if config.DISABLE_TQDM:
            tqdm = False
        self.set_terminator(tqdm, end)
        self.get_logger(tqdm).log(
            level=level,
            msg=f"{begin}{self.base_message}{msg}{TRAILING_SPACES}"
        )
        self.set_terminator(tqdm)

    def print_message_r(self, msg='', level=logging.INFO):
        self.print_message(msg, level, self.end_r, self.begin_r, False)

    def sub_message_r(self, msg='', level=logging.INFO):
        self.sub_message(msg, level, self.end_r, self.begin_r, False)


class Job(JobBase):
    def __init__(self, name, logger_name=None, log_file='', callbacks=None, **kwargs):
        JobBase.__init__(self, name, **kwargs)
        self.action_counter = 0
        self.__actions = []
        if logger_name is None:
            setup_logging(log_file=log_file)
        if logger_name is not None:
            self.logger = logging.getLogger(logger_name)
        self.callbacks = TqdmCallbacks.callbacks if callbacks == 'tqdm' else callbacks

    def time(self):
        return time.time() - self._t0

    def init(self, a):
        pass

    def add_action(self, a: JobBase):
        a.id = self.action_counter
        self.action_counter += 1
        a.logger = self.logger
        a.callbacks = self.callbacks
        self.init(a)
        self.__actions.append(a)

    def run_core(self):
        for a in self.__actions:
            if not (a.enabled and self.enabled):
                z = []
                if not a.enabled:
                    z.append("action")
                if not self.enabled:
                    z.append("job")
                msg = " and ".join(z)
                self.get_logger().warning(color_str(a.name + f": {msg} disabled",
                                                    constants.LOG_COLOR_ALERT))
            else:
                if self.callback('check_running', self.id, self.name) is False:
                    raise RunStopException(self.name)
                a.run()


class ActionList(JobBase):
    def __init__(self, name, enabled=True, **kwargs):
        JobBase.__init__(self, name, enabled, **kwargs)
        self.counts = None
        self.count = None

    def set_counts(self, counts):
        self.counts = counts
        self.callback('step_counts', self.id, self.name, self.counts)

    def begin(self):
        self.callback('begin_steps', self.id, self.name)

    def end(self):
        self.callback('end_steps', self.id, self.name)

    def __iter__(self):
        self.count = 0
        return self

    def run_step(self):
        pass

    def __next__(self):
        if self.count < self.counts:
            self.run_step()
            x = self.count
            self.count += 1
            return x
        raise StopIteration

    def run_core(self):
        self.print_message(color_str('begin run', constants.LOG_COLOR_LEVEL_2), end='\n')
        self.begin()
        for _ in iter(self):
            self.callback('after_step', self.id, self.name, self.count)
            if self.callback('check_running', self.id, self.name) is False:
                raise RunStopException(self.name)
        self.end()
