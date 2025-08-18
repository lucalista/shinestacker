# pylint: disable=C0114, C0115, C0116, R0912, R0911, E1101, W0718
import logging
import traceback
from .. config.constants import constants
from .. core.exceptions import InvalidOptionError, RunStopException
from .. algorithms.stack_framework import StackJob, CombinedActions
from .. algorithms.noise_detection import NoiseDetection, MaskNoise
from .. algorithms.vignetting import Vignetting
from .. algorithms.align import AlignFrames
from .. algorithms.balance import BalanceFrames
from .. algorithms.stack import FocusStack, FocusStackBunch
from .. algorithms.pyramid import PyramidStack
from .. algorithms.depth_map import DepthMapStack
from .. algorithms.multilayer import MultiLayer
from .project_model import Project, ActionConfig


class ProjectConverter:
    def get_logger(self, logger_name=None):
        return logging.getLogger(__name__ if logger_name is None else logger_name)

    def run(self, job, logger):
        if job.enabled:
            logger.info(f"=== run job: {job.name} ===")
        else:
            logger.warning(f"=== job: {job.name} disabled ===")
        try:
            job.run()
            return constants.RUN_COMPLETED, ''
        except RunStopException:
            logger.warning(f"=== job: {job.name} stopped ===")
            return constants.RUN_STOPPED, ''
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            msg = str(e)
            logger.error(f"=== job: {job.name} failed: {msg} ===")
            return constants.RUN_FAILED, msg

    def run_project(self, project: Project, logger_name=None, callbacks=None):
        logger = self.get_logger(logger_name)
        try:
            jobs = self.project(project, logger_name, callbacks)
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            return constants.RUN_FAILED, str(e)
        status = constants.RUN_COMPLETED, ''
        for job in jobs:
            job_status, message = self.run(job, logger)
            if job_status in [constants.RUN_STOPPED, constants.RUN_FAILED]:
                return job_status, message
        return status

    def run_job(self, job: ActionConfig, logger_name=None, callbacks=None):
        logger = self.get_logger(logger_name)
        try:
            job = self.job(job, logger_name, callbacks)
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            return constants.RUN_FAILED, str(e)
        status = self.run(job, logger)
        return status

    def project(self, project: Project, logger_name=None, callbacks=None):
        jobs = []
        for j in project.jobs:
            job = self.job(j, logger_name, callbacks)
            if job is None:
                raise RuntimeError("Job instantiation failed.")
            jobs.append(job)
        return jobs

    def filter_dict_keys(self, k_dict, prefix):
        dict_with = {k.replace(prefix, ''): v for (k, v) in k_dict.items() if k.startswith(prefix)}
        dict_without = {k: v for (k, v) in k_dict.items() if not k.startswith(prefix)}
        return dict_with, dict_without

    def action(self, action_config):
        if action_config.type_name == constants.ACTION_NOISEDETECTION:
            return NoiseDetection(**action_config.params)
        if action_config.type_name == constants.ACTION_COMBO:
            sub_actions = []
            for sa in action_config.sub_actions:
                a = self.action(sa)
                if a is not None:
                    sub_actions.append(a)
            a = CombinedActions(**action_config.params, actions=sub_actions)
            return a
        if action_config.type_name == constants.ACTION_MASKNOISE:
            params = {k: v for k, v in action_config.params.items() if k != 'name'}
            return MaskNoise(**params)
        if action_config.type_name == constants.ACTION_VIGNETTING:
            params = {k: v for k, v in action_config.params.items() if k != 'name'}
            return Vignetting(**params)
        if action_config.type_name == constants.ACTION_ALIGNFRAMES:
            params = {k: v for k, v in action_config.params.items() if k != 'name'}
            return AlignFrames(**params)
        if action_config.type_name == constants.ACTION_BALANCEFRAMES:
            params = {k: v for k, v in action_config.params.items() if k != 'name'}
            if 'intensity_interval' in params.keys():
                i = params['intensity_interval']
                params['intensity_interval'] = {'min': i[0], 'max': i[1]}
            return BalanceFrames(**params)
        if action_config.type_name in (constants.ACTION_FOCUSSTACK,
                                       constants.ACTION_FOCUSSTACKBUNCH):
            stacker = action_config.params.get('stacker', constants.STACK_ALGO_DEFAULT)
            if stacker == constants.STACK_ALGO_PYRAMID:
                algo_dict, module_dict = self.filter_dict_keys(action_config.params, 'pyramid_')
                stack_algo = PyramidStack(**algo_dict)
            elif stacker == constants.STACK_ALGO_DEPTH_MAP:
                algo_dict, module_dict = self.filter_dict_keys(action_config.params, 'depthmap_')
                stack_algo = DepthMapStack(**algo_dict)
            else:
                raise InvalidOptionError('stacker', stacker, f"valid options are: "
                                         f"{constants.STACK_ALGO_PYRAMID}, "
                                         f"{constants.STACK_ALGO_DEPTH_MAP}")
            if action_config.type_name == constants.ACTION_FOCUSSTACK:
                return FocusStack(**module_dict, stack_algo=stack_algo)
            if action_config.type_name == constants.ACTION_FOCUSSTACKBUNCH:
                return FocusStackBunch(**module_dict, stack_algo=stack_algo)
            raise InvalidOptionError(
                "stracker", stacker, details="valid values are: Pyramid, Depth map.")
        if action_config.type_name == constants.ACTION_MULTILAYER:
            input_path = list(filter(lambda p: p != '',
                              action_config.params.get('input_path', '').split(";")))
            params = {k: v for k, v in action_config.params.items() if k != 'imput_path'}
            params['input_path'] = [i.strip() for i in input_path]
            return MultiLayer(**params)
        raise RuntimeError(f"Cannot convert action of type {action_config.type_name}.")

    def job(self, action_config: ActionConfig, logger_name=None, callbacks=None):
        try:
            name = action_config.params.get('name', '')
            enabled = action_config.params.get('enabled', True)
            working_path = action_config.params.get('working_path', '')
            input_path = action_config.params.get('input_path', '')
            stack_job = StackJob(name, working_path, enabled=enabled, input_path=input_path,
                                 logger_name=logger_name, callbacks=callbacks)
            for sub in action_config.sub_actions:
                action = self.action(sub)
                if action is not None:
                    stack_job.add_action(action)
            return stack_job
        except Exception as e:
            msg = str(e)
            logger = self.get_logger(logger_name)
            logger.error(msg=f"=== can't instantiate job: {name}: {msg} ===")
            traceback.print_tb(e.__traceback__)
            raise e
