from gui.project_model import (Project, ActionConfig,
                               ACTION_COMBO, ACTION_NOISEDETECTION, ACTION_FOCUSSTACK,
                               ACTION_FOCUSSTACKBUNCH, ACTION_MULTILAYER,
                               ACTION_MASKNOISE, ACTION_VIGNETTING, ACTION_ALIGNFRAMES,
                               ACTION_BALANCEFRAMES)
from focus_stack.stack_framework import StackJob, CombinedActions
from focus_stack.noise_detection import NoiseDetection, MaskNoise
from focus_stack.vignetting import Vignetting
from focus_stack.align import AlignFrames
from focus_stack.balance import BalanceFrames
from focus_stack.stack import FocusStack, FocusStackBunch
from focus_stack.pyramid import PyramidStack
from focus_stack.depth_map import DepthMapStack
from focus_stack.multilayer import MultiLayer
from focus_stack.exceptions import InvalidOptionError, RunStopException
import logging


class ProjectConverter:
    def run(self, job, logger):
        if job.enabled:
            logger.info(f"=== run job: {job.name} ===")
        else:
            logger.warning(f"=== job: {job.name} disabled ===")
        try:
            job.run()
        except RunStopException:
            logger.warning(f"=== job: {job.name} stopped ===")
        except Exception as e:
            msg = str(e)
            logger.warning(f"=== job: {job.name} failed: {msg} ===")

    def run_project(self, project: Project, logger_name=None, callbacks=None):
        logger = logging.getLogger(__name__ if logger_name is None else logger_name)
        jobs = self.project(project, logger_name, callbacks)
        for job in jobs:
            self.run(job, logger)

    def run_job(self, job: ActionConfig, logger_name=None, callbacks=None):
        logger = logging.getLogger(__name__ if logger_name is None else logger_name)
        job = self.job(job, logger_name, callbacks)
        self.run(job, logger)

    def project(self, project: Project, logger_name=None, callbacks=None):
        return [self.job(j, logger_name, callbacks) for j in project.jobs]

    def filter_dict_keys(self, dict, prefix):
        dict_with = {k.replace(prefix, ''): v for (k, v) in dict.items() if k.startswith(prefix)}
        dict_without = {k: v for (k, v) in dict.items() if not k.startswith(prefix)}
        return dict_with, dict_without

    def action(self, action_config):
        if action_config.type_name == ACTION_NOISEDETECTION:
            return NoiseDetection(**action_config.params)
        elif action_config.type_name == ACTION_COMBO:
            sub_actions = []
            for sa in action_config.sub_actions:
                a = self.action(sa)
                if a is not None:
                    sub_actions.append(a)
            a = CombinedActions(**action_config.params, actions=sub_actions)
            return a
        elif action_config.type_name == ACTION_MASKNOISE:
            params = {k: v for k, v in action_config.params.items() if k != 'name'}
            return MaskNoise(**params)
        elif action_config.type_name == ACTION_VIGNETTING:
            params = {k: v for k, v in action_config.params.items() if k != 'name'}
            return Vignetting(**params)
        elif action_config.type_name == ACTION_ALIGNFRAMES:
            params = {k: v for k, v in action_config.params.items() if k != 'name'}
            return AlignFrames(**params)
        elif action_config.type_name == ACTION_BALANCEFRAMES:
            params = {k: v for k, v in action_config.params.items() if k != 'name'}
            if 'intensity_interval' in params.keys():
                i = params['intensity_interval']
                params['intensity_interval'] = {'min': i[0], 'max': i[1]}
            return BalanceFrames(**params)
        elif action_config.type_name == ACTION_FOCUSSTACK or action_config.type_name == ACTION_FOCUSSTACKBUNCH:
            stacker = action_config.params.get('stacker', 'Pyramid')
            if stacker == 'Pyramid':
                algo_dict, module_dict = self.filter_dict_keys(action_config.params, 'pyramid_')
                stack_algo = PyramidStack(**algo_dict)
            elif stacker == 'Depth map':
                algo_dict, module_dict = self.filter_dict_keys(action_config.params, 'depthmap_')
                stack_algo = DepthMapStack(**algo_dict)
            if action_config.type_name == ACTION_FOCUSSTACK:
                return FocusStack(**module_dict, stack_algo=stack_algo)
            elif action_config.type_name == ACTION_FOCUSSTACKBUNCH:
                return FocusStackBunch(**module_dict, stack_algo=stack_algo)
            else:
                raise InvalidOptionError("stracker", stacker, details="valid values are: Pyramid, Depth map.")
        elif action_config.type_name == ACTION_MULTILAYER:
            input_path = list(filter(lambda p: p != '', action_config.params.get('input_path', '').split(";")))
            params = {k: v for k, v in action_config.params.items() if k != 'imput_path'}
            params['input_path'] = [i.strip() for i in input_path]
            return MultiLayer(**params)
        else:
            raise Exception(f"Cannot convert action of type {action_config.type_name}.")

    def job(self, action_config: ActionConfig, logger_name=None, callbacks=None):
        name = action_config.params.get('name', '')
        enabled = action_config.params.get('enabled', True)
        working_path = action_config.params.get('working_path', '')
        input_path = action_config.params.get('input_path', '')
        stack_job = StackJob(name, working_path, enabled=enabled, input_path=input_path, logger_name=logger_name, callbacks=callbacks)
        for sub in action_config.sub_actions:
            action = self.action(sub)
            if action is not None:
                stack_job.add_action(action)
        return stack_job
