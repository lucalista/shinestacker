import sys
sys.path.append('../')
from config.config import config
import time
from termcolor import colored
from focus_stack.logging import setup_logging
from focus_stack.utils import make_tqdm_bar
import logging

LINE_UP = "\r\033[A"
trailing_spaces = " " * 30


def elapsed_time_str(start):
    dt = time.time() - start
    mm = int(dt // 60)
    ss = dt - mm * 60
    hh = mm // 60
    mm -= hh * 60
    return ("{:02d}:{:02d}:{:05.2f}s".format(hh, mm, ss))


class JobBase:
    def __init__(self, name):
        self.id = -1
        self.name = name
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
                callback(*args)

    def run(self):
        self.__t0 = time.time()
        self.callback('before_run', self.id)
        self.run_core()
        self.callback('after_run', self.id)
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
    def __init__(self, name, logger_name=None, log_file="logs/focusstack.log", callbacks=None):
        JobBase.__init__(self, name)
        self.action_counter = 0
        self.__actions = []
        if logger_name is None:
            setup_logging(log_file=log_file)
        self.logger = None if logger_name is None else logging.getLogger(logger_name)
        self.callbacks = callbacks

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
            a.run()


class ActionList(JobBase):
    def __init__(self, name):
        JobBase.__init__(self, name)

    def set_counts(self, counts):
        self.counts = counts
        self.callback('step_counts', self.id, self.counts)

    def begin(self):
        self.callback('begin_steps', self.id)

    def end(self):
        self.callback('end_steps', self.id)

    def __iter__(self):
        self.count = 1
        return self

    def __next__(self):
        if self.count <= self.counts:
            self.run_step()
            x = self.count
            self.count += 1
            self.callback('after_step', self.id, self.count)            
            return x
        else:
            raise StopIteration

    def run_core(self):
        self.print_message('begin run', end='\n')
        self.begin()
        if not config.DISABLE_TQDM:
            bar = make_tqdm_bar(self.name, self.counts)
        for x in iter(self):
            if not config.DISABLE_TQDM:
                bar.update(1)
        if not config.DISABLE_TQDM:
            bar.close()
        self.end()
