import time
from termcolor import colored
from tqdm.notebook import tqdm_notebook
from focus_stack.logging import setup_logging, console_logging_overwrite, console_logging_newline
import logging

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
        self.name = name
        self.base_message = ''
        self.logger = logging.getLogger(__name__)

    def run(self):
        self.__t0 = time.time()
        self.run_core()
        self.logger.info(
            colored(self.name + ": ", "green",
                    attrs=["bold"]) + colored(
                "elapsed time: {}".format(elapsed_time_str(self.__t0)), "green") + trailing_spaces)
        self.logger.info(
            colored(self.name + ": ", "green", attrs=["bold"]) + colored("completed", "green") + trailing_spaces)

    def print_message(self, msg='', level=logging.INFO, end='\n'):
        self.base_message = colored(self.name, "blue", attrs=["bold"])
        if msg != '':
            self.base_message += (': ' + msg)
        if end == '\r':
            console_logging_overwrite()
        self.logger.log(level, colored(self.base_message, 'blue', attrs=['bold']) + trailing_spaces)
        if end == '\r':
            console_logging_newline()

    def sub_message(self, msg, level=logging.INFO, end='\n'):
        if end == '\r':
            console_logging_overwrite()
        self.logger.log(level, self.base_message + msg + trailing_spaces)
        if end == '\r':
            console_logging_newline()


class Job(JobBase):
    def __init__(self, name, log_file="logs/focusstack.log"):
        JobBase.__init__(self, name)
        self.__actions = []
        setup_logging(log_file=log_file)

    def time(self):
        return time.time() - self.__t0

    def init(self, a):
        pass

    def add_action(self, a):
        self.init(a)
        self.__actions.append(a)

    def run_core(self):
        for a in self.__actions:
            a.run()


class ActionList(JobBase):
    def __init__(self, name):
        JobBase.__init__(self, name)

    def begin(self):
        pass

    def end(self):
        pass

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
        self.print_message('', end='\r')
        self.begin()
        bar = tqdm_notebook(desc=self.name, total=self.counts)
        for x in iter(self):
            bar.update(1)
        bar.close()
        self.end()
