# pylint: disable=R0911
from copy import deepcopy
from .. config.constants import constants
from .. config.app_config import AppConfig


TYPE_NAME_APP_CONFIG_MAP = {
    constants.ACTION_COMBO: 'combined_actions_params',
    constants.ACTION_ALIGNFRAMES: 'align_frames_params',
    constants.ACTION_FOCUSSTACK: 'focus_stack_params',
    constants.ACTION_FOCUSSTACKBUNCH: 'focus_stack_bunch_params'
}


class ActionConfig:
    def __init__(self, type_name: str, params=None, parent=None):
        self.type_name = type_name
        app_config_params_key = TYPE_NAME_APP_CONFIG_MAP.get(type_name, '')
        if app_config_params_key != '':
            self.params = AppConfig.get(app_config_params_key, {})
        else:
            self.params = {}
        if params:
            self.params = {**self.params, **params}
        self.metadata = {}
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

    def clone(self, name_postfix=''):
        c = ActionConfig(self.type_name, deepcopy(self.params), self.parent)
        if len(self.metadata) > 0:
            c.metadata = deepcopy(self.metadata)
        c.sub_actions = [s.clone() for s in self.sub_actions]
        for s in c.sub_actions:
            s.parent = c
        if name_postfix != '':
            c.params['name'] = c.params.get('name', '') + name_postfix
        return c

    def to_dict(self):
        project_dict = {
            'type_name': self.type_name, 'params': self.params, 'metadata': self.metadata}
        if len(self.sub_actions) > 0:
            project_dict['sub_actions'] = [a.to_dict() for a in self.sub_actions]
        return project_dict

    @classmethod
    def from_dict(cls, data, version):
        a = ActionConfig(data['type_name'], data['params'])
        if 'metadata' in data.keys():
            a.metadata = data['metadata']
        if 'sub_actions' in data.keys():
            a.sub_actions = [ActionConfig.from_dict(s, version) for s in data['sub_actions']]
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

    def copy_from(self, other_project):
        self.jobs = [job.clone() for job in other_project.jobs]

    def to_dict(self):
        return [j.to_dict() for j in self.jobs]

    @classmethod
    def from_dict(cls, data, version):
        p = Project()
        p.jobs = [ActionConfig.from_dict(j, version) for j in data]
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


def get_retouch_path(job):
    frames_path = [get_action_output_path(action)[0]
                   for action in job.sub_actions
                   if action.type_name == constants.ACTION_COMBO]
    bunches_path = [get_action_output_path(action)[0]
                    for action in job.sub_actions
                    if action.type_name == constants.ACTION_FOCUSSTACKBUNCH]
    stack_path = [get_action_output_path(action)[0]
                  for action in job.sub_actions
                  if action.type_name == constants.ACTION_FOCUSSTACK]
    if len(bunches_path) > 0:
        stack_path += [bunches_path[0]]
    elif len(frames_path) > 0:
        stack_path += [frames_path[0]]
    wp = get_action_working_path(job)[0]
    if wp == '':
        raise ValueError("Job has no working path specified.")
    stack_path = [f"{wp}/{s}" for s in stack_path]
    return stack_path


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
