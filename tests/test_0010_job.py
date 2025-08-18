import time
from shinestacker.core.colors import color_str
from shinestacker.core.framework import Job, JobBase, ActionList


class Action1(JobBase):
    def __init__(self):
        JobBase.__init__(self, "action 1")

    def run(self):
        self.print_message(color_str("run 1", "blue", "bold"))
        time.sleep(0.5)


class Action2(JobBase):
    def __init__(self):
        JobBase.__init__(self, "action 2")

    def run(self):
        self.print_message(color_str("run 2", "blue", "bold"))
        time.sleep(0.7)


class MyActionList(ActionList):
    def __init__(self, name):
        ActionList.__init__(self, name)

    def begin(self):
        super().begin()
        self.set_counts(10)

    def run_step(self):
        self.print_message_r(color_str("action: {}".format(self.count + 1), "blue"))
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
