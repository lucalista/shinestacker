from focus_stack import StackJob, Actions

class ActionConfig:
    def __init__(self, type_name: str, params: dict = None):
        self.type_name = type_name
        self.params = params or {}

    def create_instance(self):
        from focus_stack import available_actions
        action_class = available_actions.get(self.type_name)
        if not action_class:
            raise ValueError(f"Unknown action type: {self.type_name}")
        return action_class(**self.params)


class Job:
    def __init__(self, name: str, working_path: str, input_path: str):
        self.name = name
        self.working_path = working_path
        self.input_path = input_path
        self.actions: list[ActionConfig] = []

    def to_stack_job(self):
        job = StackJob(self.name, self.working_path, self.input_path)
        for action_cfg in self.actions:
            action = action_cfg.create_instance()
            job.add_action(action)
        return job


class Project:
    def __init__(self):
        self.jobs: list[Job] = []

    def run_all(self):
        for job in self.jobs:
            stack_job = job.to_stack_job()
            stack_job.run()