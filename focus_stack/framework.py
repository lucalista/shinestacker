import sys
sys.path.append('../')
from config.config import config
import time
from termcolor import colored
from focus_stack.logging import setup_logging
from focus_stack.utils import make_tqdm_bar
import logging
from focus_stack.exceptions import RunStopException

LINE_UP = "\r\033[A"
trailing_spaces = " " * 30


class TqdmCallbacks:
    _instance = None

    callbacks = {
        'step_counts': lambda id, name, counts: TqdmCallbacks.instance().step_counts(name, counts),
        'begin_steps': lambda id, name: TqdmCallbacks.instance().begin_steps(name),
        'end_steps': lambda id, name: TqdmCallbacks.instance().end_steps(name),
        'after_step': lambda id, name, steps: TqdmCallbacks.instance().after_step(name)
    }

    def __init__(self):
        self.bar = None
        self.counts = -1

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = TqdmCallbacks()
        return cls._instance

    def step_counts(self, name, counts):
        self.counts = counts
        self.bar = make_tqdm_bar(name, self.counts)

    def begin_steps(self, name):
        pass

    def end_steps(self, name):
        if self.bar is None:
            raise RuntimeError("tqdm bar not initialized")
        self.bar.close()
        self.bar = None

    def after_step(self, name):
        self.bar.write("")
        self.bar.update(1)


tqdm_callbacks = TqdmCallbacks()


def elapsed_time_str(start):
    dt = time.time() - start
    mm = int(dt // 60)
    ss = dt - mm * 60
    hh = mm // 60
    mm -= hh * 60
    return ("{:02d}:{:02d}:{:05.2f}s".format(hh, mm, ss))


class JobBase:
    def __init__(self, name, enabled=True):
        self.id = -1
        self.name = name
        self.enabled = enabled
        self.base_message = ''
        if config.JUPYTER_NOTEBOOK:
            self.begin_r, self.end_r = "", "\r",
        else:
            self.begin_r, self.end_r = LINE_UP, None

    def callback(self, key, *args):
        has_callbacks = hasattr(self, 'callbacks')
        if has_callbacks and self.callbacks is not None:
            callback = self.callbacks.get(key, None)
            if callback:
                return callback(*args)
        return None

    def run(self):
        self.__t0 = time.time()
        if not self.enabled:
            self.get_logger().warning(colored(self.name + ": entire job disabled", 'red'))
        self.callback('before_action', self.id, self.name)
        self.run_core()
        self.callback('after_action', self.id, self.name)
        self.get_logger().info(
            colored(self.name + ": ", "green",
                    attrs=["bold"]) + colored(
                "elapsed time: {}".format(elapsed_time_str(self.__t0)), "green") + trailing_spaces)
        self.get_logger().info(
            colored(self.name + ": ", "green", attrs=["bold"]) + colored("completed", "green") + trailing_spaces)

    def get_logger(self, tqdm=False):
        if config.DISABLE_TQDM:
            tqdm = False
        if self.logger is None:
            return logging.getLogger("tqdm" if tqdm else __name__)
        else:
            return self.logger

    def set_terminator(self, tqdm=False, end='\n'):
        if config.DISABLE_TQDM:
            tqdm = False
        if end is not None:
            logging.getLogger("tqdm" if tqdm else None).handlers[0].terminator = end

    def print_message(self, msg='', level=logging.INFO, end=None, begin='', tqdm=False):
        if config.DISABLE_TQDM:
            tqdm = False
        self.base_message = colored(self.name, "blue", attrs=["bold"])
        if msg != '':
            self.base_message += (': ' + msg)
        self.set_terminator(tqdm, end)
        self.get_logger(tqdm).log(level, begin + colored(self.base_message, 'blue', attrs=['bold']) + trailing_spaces)
        self.set_terminator(tqdm)

    def sub_message(self, msg, level=logging.INFO, end=None, begin='', tqdm=False):
        if config.DISABLE_TQDM:
            tqdm = False
        self.set_terminator(tqdm, end)
        self.get_logger(tqdm).log(level, begin + self.base_message + msg + trailing_spaces)
        self.set_terminator(tqdm)

    def print_message_r(self, msg='', level=logging.INFO):
        self.print_message(msg, level, self.end_r, self.begin_r, False)

    def sub_message_r(self, msg='', level=logging.INFO):
        self.sub_message(msg, level, self.end_r, self.begin_r, False)


class Job(JobBase):
    def __init__(self, name, logger_name=None, log_file="logs/focusstack.log", callbacks=None, **kwargs):
        JobBase.__init__(self, name, **kwargs)
        self.action_counter = 0
        self.__actions = []
        if logger_name is None:
            setup_logging(log_file=log_file)
        self.logger = None if logger_name is None else logging.getLogger(logger_name)
        self.callbacks = TqdmCallbacks.callbacks if callbacks == 'tqdm' else callbacks

    def time(self):
        return time.time() - self.__t0

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
                # a.callback('before_action', a.id, a.name)
                z = []
                if not a.enabled:
                    z.append("action")
                if not self.enabled:
                    z.append("job")
                msg = " and ".join(z)
                self.get_logger().warning(colored(a.name + f": {msg} disabled", 'red'))
                # a.callback('after_action', a.id, a.name)
            else:
                if self.callback('check_running', self.id, self.name) is False:
                    raise RunStopException(self.name)
                a.run()


class ActionList(JobBase):
    def __init__(self, name, enabled=True, **kwargs):
        JobBase.__init__(self, name, enabled, **kwargs)

    def set_counts(self, counts):
        self.counts = counts
        self.callback('step_counts', self.id, self.name, self.counts)

    def begin(self):
        self.callback('begin_steps', self.id, self.name)

    def end(self):
        self.callback('end_steps', self.id, self.name)

    def __iter__(self):
        self.count = 1
        return self

    def __next__(self):
        if self.count <= self.counts:
            self.run_step()
            x = self.count
            self.count += 1
            return x
        else:
            raise StopIteration

    def run_core(self):
        self.print_message('begin run', end='\n')
        self.begin()
        for x in iter(self):
            self.callback('after_step', self.id, self.name, self.count)
        self.end()
