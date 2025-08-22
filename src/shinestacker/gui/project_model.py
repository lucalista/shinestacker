# pylint: disable=C0114, C0115, C0116, R0911
from copy import deepcopy
from .. config.constants import constants


class ActionConfig:
    def __init__(self, type_name: str, params=None, parent=None):
        self.type_name = type_name
        self.params = params or {}
        self.parent = parent
        self.sub_actions: list[ActionConfig] = []

    def enabled(self):
        return self.params.get('enabled', True)

    def set_enabled(self, enabled):
        self.params['enabled'] = enabled

    def set_enabled_all(self, enabled):
        self.params['enabled'] = enabled
        for a in self.sub_actions:
            a.set_enabled_all(enabled)

    def add_sub_action(self, action):
        self.sub_actions.append(action)
        action.parent = self

    def pop_sub_action(self, index):
        if index < len(self.sub_actions):
            self.sub_actions.pop(index)
        else:
            raise RuntimeError(f"can't pop sub-action {index}, lenght is {len(self.sub_actions)}")

    def clone(self, name_postfix=''):
        c = ActionConfig(self.type_name, deepcopy(self.params))
        c.sub_actions = [s.clone() for s in self.sub_actions]
        for s in c.sub_actions:
            s.parent = c
        if name_postfix != '':
            c.params['name'] = c.params.get('name', '') + name_postfix
        return c

    def to_dict(self):
        project_dict = {'type_name': self.type_name, 'params': self.params}
        if len(self.sub_actions) > 0:
            project_dict['sub_actions'] = [a.to_dict() for a in self.sub_actions]
        return project_dict

    @classmethod
    def from_dict(cls, data):
        a = ActionConfig(data['type_name'], data['params'])
        if 'sub_actions' in data.keys():
            a.sub_actions = [ActionConfig.from_dict(s) for s in data['sub_actions']]
            for s in a.sub_actions:
                s.parent = a
        return a


class Project:
    def __init__(self):
        self.jobs = []

    def clone(self):
        c = Project()
        c.jobs = [j.clone() for j in self.jobs]
        return c

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


def get_action_working_path(action, get_name=False):
    if action is None:
        return '', ''
    if action in constants.SUB_ACTION_TYPES:
        return get_action_working_path(action.parent, True)
    wp = action.params.get('working_path', '')
    if wp != '':
        return wp, (f" {action.params.get('name', '')} [{action.type_name}]" if get_name else '')
    return get_action_working_path(action.parent, True)


def get_action_output_path(action, get_name=False):
    if action is None:
        return '', ''
    if action.type_name in constants.SUB_ACTION_TYPES:
        return get_action_output_path(action.parent, True)
    name = action.params.get('name', '')
    path = action.params.get('output_path', '')
    if path == '':
        path = name
    return path, (f" {action.params.get('name', '')} [{action.type_name}]" if get_name else '')


def get_action_input_path(action, get_name=False):
    if action is None:
        return '', ''
    type_name = action.type_name
    if type_name in constants.SUB_ACTION_TYPES:
        return get_action_input_path(action.parent, True)
    path = action.params.get('input_path', '')
    if path == '':
        if action.parent is None:
            if type_name == constants.ACTION_JOB and len(action.sub_actions) > 0:
                action = action.sub_actions[0]
                path = action.params.get('input_path', '')
                return path, f" {action.params.get('name', '')} [{action.type_name}]"
            return '', ''
        actions = action.parent.sub_actions
        if action in actions:
            i = actions.index(action)
            if i == 0:
                return get_action_input_path(action.parent, True)
            return get_action_output_path(actions[i - 1], True)
        return '', ''
    return path, (f" {action.params.get('name', '')} [{action.type_name}]" if get_name else '')
