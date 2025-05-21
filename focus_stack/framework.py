import time
from termcolor import colored
from tqdm.notebook import tqdm_notebook
from tqdm import tqdm
from focus_stack.logging import setup_logging
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
        self.name = name
        self.base_message = ''
        try:
            __IPYTHON__ # noqa
            self.begin_r, self.end_r = "", "\r",
        except Exception:
            self.begin_r, self.end_r = LINE_UP, None

    def run(self):
        self.__t0 = time.time()
        self.run_core()
        self.get_logger().info(
            colored(self.name + ": ", "green",
                    attrs=["bold"]) + colored(
                "elapsed time: {}".format(elapsed_time_str(self.__t0)), "green") + trailing_spaces)
        self.get_logger().info(
            colored(self.name + ": ", "green", attrs=["bold"]) + colored("completed", "green") + trailing_spaces)

    def get_logger(self, tqdm=False):
        return logging.getLogger("tqdm" if tqdm else __name__)

    def set_terminator(self, tqdm=None, end='\n'):
        if end is not None:
            logging.getLogger("tqdm" if tqdm else None).handlers[0].terminator = end

    def print_message(self, msg='', level=logging.INFO, end=None, begin='', tqdm=False):
        self.base_message = colored(self.name, "blue", attrs=["bold"])
        if msg != '':
            self.base_message += (': ' + msg)
        self.set_terminator(tqdm, end)
        self.get_logger(tqdm).log(level, begin + colored(self.base_message, 'blue', attrs=['bold']) + trailing_spaces)
        self.set_terminator(tqdm)

    def sub_message(self, msg, level=logging.INFO, end=None, begin='', tqdm=False):
        self.set_terminator(tqdm, end)
        self.get_logger(tqdm).log(level, begin + self.base_message + msg + trailing_spaces)
        self.set_terminator(tqdm)

    def print_message_r(self, msg='', level=logging.INFO):
        self.print_message(msg, level, self.end_r, self.begin_r, False)

    def sub_message_r(self, msg='', level=logging.INFO):
        self.sub_message(msg, level, self.end_r, self.begin_r, False)


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
        self.print_message('begin run', end='\n')
        self.begin()
        try:
            __IPYTHON__  # noqa
            bar = tqdm_notebook(desc=self.name, total=self.counts)
        except Exception:
            bar = tqdm(desc=self.name, total=self.counts, ncols=80)
        for x in iter(self):
            bar.update(1)
        bar.close()
        self.end()
