import sys
sys.path.append('../')
from core.framework import Job, JobBase, ActionList
from termcolor import colored
import time


class Action1(JobBase):
    def __init__(self):
        JobBase.__init__(self, "action 1")

    def run(self):
        self.print_message(colored("run 1", "blue", attrs=["bold"]))
        time.sleep(0.5)


class Action2(JobBase):
    def __init__(self):
        JobBase.__init__(self, "action 2")

    def run(self):
        self.print_message(colored("run 2", "blue", attrs=["bold"]))
        time.sleep(0.7)


class MyActionList(ActionList):
    def __init__(self, name):
        ActionList.__init__(self, name)

    def begin(self):
        super().begin()
        self.set_counts(10)

    def run_step(self):
        self.print_message_r(colored("action: {}".format(self.count), "blue"))
        time.sleep(0.1)


def test_run():
    try:
        job = Job("job", callbacks='tqdm')
        job.add_action(Action1())
        job.add_action(Action2())
        job.add_action(MyActionList("my actions"))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_run()
