class ActionConfig:
    def __init__(self, type_name: str, params: dict=None, parent=None):
        self.type_name = type_name
        self.params = params or {}
        self.parent = parent
        self.sub_actions: list[ActionConfig] = []

    def add_sub_action(self, action):
        self.sub_actions.append(action)
        action.parent = self

    def pop_sub_action(self, index):
        if index < len(self.sub_actions):
            self.sub_actions.pop(index)
        else:
            raise Exception(f"can't pop sub-action {index}, lenght is {len(self.sub_actions)}")

    def create_instance(self):
        pass

    def to_dict(self):
        return {
            'type_name': self.type_name,
            'params': self.params,
            'sub_actions': [a.to_dict() for a in self.sub_actions]
        }

    @classmethod
    def from_dict(cls, data):
        a = ActionConfig(data['type_name'], data['params'])
        a.sub_actions = [ActionConfig.from_dict(s) for s in data['sub_actions']]
        for s in a.sub_actions:
            s.parent = a
        return a

class Project:
    def __init__(self):
        self.jobs: list[ActionConfig] = []

    def run_all(self):
        for job in self.jobs:
            stack_job = job.to_stack_job()
            stack_job.run()

    def to_dict(self):
        return [j.to_dict() for j in self.jobs]

    @classmethod
    def from_dict(cls, data):
        p = Project()
        p.jobs = [ActionConfig.from_dict(j) for j in data]
        for j in p.jobs:
            for s in j.sub_actions:
                s.parent = j
        return p

from focus_stack import StackJob
import logging


class ProjectConverter:
    def project(self, project: Project):
        return [self.job(j) for j in project.jobs]

    def job(self, job: ActionConfig):
        name = job.params.get('name', '')
        working_path = job.params.get('working_path', '')
        input_path = job.params.get('input_path', '')
        return StackJob(name, working_path, input_path)

    def run_project(self, project: Project):
        jobs = self.project(project)
        for job in jobs:
            logger = logging.getLogger(__name__)
            logger.info("run: " + job.name)
            job.run()
    
    def run_job(self, job: ActionConfig):
        job = self.job(job)
        logger = logging.getLogger(__name__)
        logger.info("run: " + job.name)
        job.run()

