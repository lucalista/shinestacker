import time
from termcolor import colored
from tqdm.notebook import tqdm_notebook

def elapsed_time_str(start):
    dt = time.time() - start
    mm = int(dt // 60)
    ss = dt - mm*60
    hh = mm // 60
    mm -= hh*60
    return ("{:02d}:{:02d}:{:05.2f}s".format(hh, mm, ss))

class JobBase:
    __t0 = None
    def __init__(self, name):
        self.name = name
        self.base_message = ''
    def run(self):
        self.__t0 = time.time()
        self.run_core()
        print(colored(self.name + ": ", "green", attrs=["bold"]), end='')
        print(colored("elapsed time: {}                    ".format(elapsed_time_str(self.__t0)), "green"))
        print(colored(self.name + " completed                    ", "green"))
    def print_message(self, msg='', end='\n'):
        self.base_message = colored("running " + self.name, "blue", attrs=["bold"])
        if msg != '': self.base_message += (': ' + msg)
        print(colored(self.base_message, 'blue', attrs=['bold']), end=end)
    def sub_message(self, msg, end='\n'):
        print(self.base_message + msg, end=end)
        
class Job(JobBase):
    __actions = None
    def __init__(self, name):
        JobBase.__init__(self, name)
        self.__actions = []
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
    counts = None
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
        self.print_message('', '\r')
        self.begin()
        bar = tqdm_notebook(desc=self.name, total=self.counts)
        for x in iter(self):
            bar.update(1)
        bar.close()
        self.end()