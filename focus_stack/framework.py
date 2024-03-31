import time
from termcolor import colored, cprint
from tqdm.notebook import tqdm_notebook

def elapsed_time_str(start):
    dt = time.time() - start
    mm = int(dt // 60)
    ss = dt - mm*60
    hh = mm // 60
    mm -= hh*60
    return ("{:02d}:{:02d}:{:05.2f}s".format(hh, mm, ss))

class Timer:
    __t0 = None
    __name = None
    def __init__(self, name):
        self.name = name
    def run(self):
        self.__t0 = time.time()
        self.run_core()
        cprint(self.name + ":", "green", attrs=["bold"], end='')
        cprint(" elapsed time: " + elapsed_time_str(self.__t0), "green")
        
class Job(Timer):
    __actions = None
    def __init__(self, name):
        Timer.__init__(self, name)
        self.__actions = []
    def time(self):
        return time.time() - self.__t0
    def add_action(self, a):
        self.__actions.append(a)
    def run_core(self):
        for a in self.__actions:
            a.run()

class ActionList(Timer):
    def __init__(self, name, counts):
        Timer.__init__(self, name)
        self.counts = counts
    def __iter__(self):
        self.count = 1
        return self
    def __next__(self):
        if self.count <= self.counts:
            x = self.count
            self.run_step()
            self.count += 1
            return x
        else:
            raise StopIteration
    def run_core(self):
        cprint("run " + self.name, "blue", attrs=["bold"])
        bar = tqdm_notebook(desc=self.name, total=self.counts)
        for x in iter(self):
            bar.update(1)
        bar.close()