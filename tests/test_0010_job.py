import sys
sys.path.append('../')
from focus_stack.framework import Job, JobBase, ActionList, LINE_UP
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
        self.counts = 10

    def run_step(self):
        self.print_message(colored("action: {} ".format(self.count), "blue"), begin=LINE_UP, tqdm=True)
        time.sleep(0.1)


def test_run():
    try:
        job = Job("job")
        job.add_action(Action1())
        job.add_action(Action2())
        job.add_action(MyActionList("my actions"))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_run()
