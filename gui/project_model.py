from focus_stack import StackJob


class ActionConfig:
    def __init__(self, type_name: str, params: dict = None):
        self.type_name = type_name
        self.params = params or {}
        self.parent = None
        self.sub_actions: list[ActionConfig] = []

    def add_sub_action(self, action):
        self.sub_actions.append(action)
        action.parent = self

    def pop_sub_action(self, index):
        self.sub_actions.pop(index)

    def __getstate__(self):
        state = self.__dict__.copy()
        return state
    
    def __setstate__(self, state):
        self.__dict__.update(state)            

    def create_instance(self):
        pass
        # dummy implementation for now
'''
        from focus_stack import available_actions
        action_class = available_actions.get(self.type_name)
        if not action_class:
            raise ValueError(f"Unknown action type: {self.type_name}")
        return action_class(**self.params)
'''

class Project:
    def __init__(self):
        self.jobs: list[ActionConfig] = []

    def run_all(self):
        for job in self.jobs:
            stack_job = job.to_stack_job()
            stack_job.run()

    def __getstate__(self):
        state = self.__dict__.copy()
        return state
    
    def __setstate__(self, state):
        self.__dict__.update(state)            
