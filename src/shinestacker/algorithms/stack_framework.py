# pylint: disable=C0114, C0115, C0116, W0102, R0902, R0903, E1128, W0718
# pylint: disable=R0917, R0913, R1702, R0912, E1111, E1121, W0613
import logging
import os
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. core.colors import color_str
from .. core.framework import Job, SequentialTask
from .. core.core_utils import check_path_exists
from .. core.exceptions import RunStopException
from .utils import (
    read_img, write_img, extension_supported_input, get_img_metadata, validate_image,
    get_output_filename)
from .plot_manager import DirectPlotManager


class StackJob(Job):
    def __init__(
            self, name, working_path, input_path='', input_filepaths=[], plot_manager=None,
            **kwargs):
        check_path_exists(working_path)
        self.working_path = working_path
        self._action_paths = [] if input_path == '' else [input_path]
        self._input_full_path = None
        self._input_filepaths = input_filepaths
        if self._input_filepaths:
            self._input_filepaths.sort()
        self.plot_manager = plot_manager if plot_manager is not None else DirectPlotManager()
        Job.__init__(self, name, **kwargs)

    def init(self, action):
        action.init(self)

    def input_filepaths(self):
        return self._input_filepaths

    def num_input_filepaths(self):
        return len(self._input_filepaths)

    def add_action_path(self, path):
        self._action_paths.append(path)

    def num_action_paths(self):
        return len(self._action_paths)

    def action_path(self, i):
        return self._action_paths[i]


class ImageSequenceManager:
    def __init__(self, name, input_path='', output_path='', working_path='',
                 plot_path=DEFAULTS['image_sequence_manager']['plots_path'],
                 scratch_output_dir=True, delete_output_at_end=False,
                 resample=1, reverse_order=DEFAULTS['image_sequence_manager']['reverse_order'],
                 **_kwargs):
        self.name = name
        self.working_path = working_path
        self.plot_path = plot_path
        self.input_path = input_path
        self.output_path = self.name if output_path == '' else output_path
        self._resample = resample
        self.reverse_order = reverse_order
        self.scratch_output_dir = scratch_output_dir
        self.delete_output_at_end = delete_output_at_end
        self.enabled = None
        self.base_message = ''
        self.plot_manager = None
        self._input_full_path = None
        self._output_full_path = None
        self._input_filepaths = None

    def output_full_path(self):
        if self._output_full_path is None:
            self._output_full_path = os.path.join(self.working_path, self.output_path)
        return self._output_full_path

    def input_full_path(self):
        if self._input_full_path is None:
            if isinstance(self.input_path, str):
                self._input_full_path = os.path.join(self.working_path, self.input_path)
                check_path_exists(self._input_full_path)
            elif hasattr(self.input_path, "__len__"):
                self._input_full_path = [os.path.join(self.working_path, path)
                                         for path in self.input_path]
                for path in self._input_full_path:
                    check_path_exists(path)
        return self._input_full_path

    def input_filepaths(self):
        if self._input_filepaths is None:
            input_full_path = self.input_full_path()
            if isinstance(input_full_path, str):
                dirs = [input_full_path]
            elif hasattr(input_full_path, "__len__"):
                dirs = input_full_path
            else:
                raise RuntimeError("input_full_path option must contain "
                                   "a path or an array of paths")
            files = []
            for d in dirs:
                filelist = []
                for _dirpath, _, filenames in os.walk(d):
                    filelist = [os.path.join(_dirpath, name)
                                for name in filenames
                                if extension_supported_input(name) and not name.startswith('.')]
                    filelist.sort()
                    if self.reverse_order:
                        filelist.reverse()
                    if self._resample > 1:
                        filelist = filelist[0::self._resample]
                    files += filelist
                if len(files) == 0:
                    self.print_message(color_str(f"input folder {d} does not contain any image",
                                                 constants.LOG_COLOR_WARNING),
                                       level=logging.WARNING)
            self._input_filepaths = files
        return self._input_filepaths

    def input_filepath(self, index):
        return self.input_filepaths()[index]

    def num_input_filepaths(self):
        return len(self.input_filepaths())

    def print_message(self, msg='', level=logging.INFO, end=None, begin='', tqdm=False):
        assert False, "this method should be overwritten"

    def set_filelist(self):
        file_folder = os.path.relpath(self.input_full_path(), self.working_path)
        num_str = "no" if self.num_input_filepaths() == 0 else f"{self.num_input_filepaths()}"
        self.print_message(color_str(f"{num_str} image files in folder: {file_folder}",
                                     constants.LOG_COLOR_LEVEL_2))
        self.base_message = color_str(self.name, constants.LOG_COLOR_LEVEL_1, "bold")

    def scratch_outout_folder(self):
        if self.enabled:
            output_dir = self.output_full_path()
            list_dir = os.listdir(output_dir)
            n_files = len(list_dir)
            if n_files > 0:
                for filename in list_dir:
                    file_path = os.path.join(output_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            self.print_message(
                color_str(f"output directory {self.output_path} content erased",
                          'yellow'))
        else:
            self.print_message(
                color_str(f"module disabled, output directory {self.output_path}"
                          " not scratched", 'yellow'))

    def init(self, job):
        if self.working_path == '':
            self.working_path = job.working_path
        check_path_exists(self.working_path)
        output_dir = self.output_full_path()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        else:
            if len(os.listdir(output_dir)):
                if self.scratch_output_dir:
                    self.scratch_outout_folder()
                elif self.enabled:
                    self.print_message(
                        color_str(
                            f": output directory {self.output_path} not empty, "
                            "files may be overwritten or merged with existing ones.", 'yellow'
                        ), level=logging.WARNING)
        if self.plot_path == '':
            self.plot_path = os.path.join(self.working_path, self.plot_path)
            if not os.path.exists(self.plot_path):
                os.makedirs(self.plot_path)
        if self.input_path in ['', []]:
            if job.num_action_paths() == 0:
                raise RuntimeError(f"Job {job.name} does not have any configured path")
            self.input_path = job.action_path(-1)
            if job.num_action_paths() == 1 and job.num_input_filepaths() > 0:
                self._input_filepaths = []
                for filepath in job.input_filepaths():
                    if not os.path.isabs(filepath):
                        filepath = os.path.join(self.input_full_path(), filepath)
                    self._input_filepaths.append(filepath)
        job.add_action_path(self.output_path)
        self.plot_manager = job.plot_manager

    def end_job(self):
        if self.delete_output_at_end:
            self.scratch_outout_folder()
            os.rmdir(self.output_full_path())

    def folder_list_str(self):
        if isinstance(self.input_full_path(), list):
            file_list = ", ".join(
                [path.replace(self.working_path, '').lstrip('/')
                 for path in self.input_full_path()])
            return "folder" + ('s' if len(self.input_full_path()) > 1 else '') + f": {file_list}"
        return "folder: " + self.input_full_path().replace(self.working_path, '').lstrip('/')


class ReferenceFrameTask(SequentialTask, ImageSequenceManager):
    def __init__(self, name, enabled=True, reference_index=0,
                 step_process=DEFAULTS['reference_frame_task']['step_process'], **kwargs):
        ImageSequenceManager.__init__(self, name, **kwargs)
        SequentialTask.__init__(self, name, enabled)
        self.ref_idx = reference_index
        self.step_process = step_process
        self.current_idx = None
        self.current_ref_idx = None
        self.current_idx_step = None

    def begin(self):
        SequentialTask.begin(self)
        self.set_filelist()
        n = self.num_input_filepaths()
        self.set_counts(n)
        if self.ref_idx == 0:
            self.ref_idx = n // 2
        elif self.ref_idx == -1:
            self.ref_idx = n - 1
        else:
            self.ref_idx -= 1
            if not 0 <= self.ref_idx < n:
                msg = f"reference index {self.ref_idx} out of range [1, {n}]"
                self.print_message_r(color_str(msg, constants.LOG_COLOR_LEVEL_2))
                raise IndexError(msg)

    def end(self):
        SequentialTask.end(self)

    def end_job(self):
        ImageSequenceManager.end_job(self)

    def run_frame(self, _idx, _ref_idx):
        return None

    def run_step(self, action_count=-1):
        num_files = self.num_input_filepaths()
        if self.run_sequential():
            if action_count == 0:
                self.current_idx = self.ref_idx if self.step_process else 0
                self.current_ref_idx = self.ref_idx
                self.current_idx_step = +1
            idx, ref_idx = self.current_idx, self.current_ref_idx
            self.print_message_r(
                color_str(f"step {action_count + 1}/{num_files}: process file: "
                          f"{os.path.basename(self.input_filepath(idx))}, "
                          f"reference: "
                          f"{os.path.basename(self.input_filepath(self.current_ref_idx))}",
                          constants.LOG_COLOR_LEVEL_2))
        else:
            idx, ref_idx = action_count, -1
            self.print_message_r(
                color_str(f"step {idx + 1}/{num_files}: process file: "
                          f"{os.path.basename(self.input_filepath(idx))}, "
                          "parallel thread", constants.LOG_COLOR_LEVEL_2))
        self.base_message = color_str(self.name, constants.LOG_COLOR_LEVEL_1, "bold")
        img = self.run_frame(idx, ref_idx)
        if self.run_sequential():
            if self.current_idx < num_files:
                if self.step_process and img is not None:
                    self.current_ref_idx = self.current_idx
                self.current_idx += self.current_idx_step
            if self.current_idx == num_files:
                self.current_idx = self.ref_idx - 1
                if self.step_process:
                    self.current_ref_idx = self.ref_idx
                self.current_idx_step = -1
        return img is not None


class SubAction:
    def __init__(self, name='', enabled=True):
        self.name = name
        self.enabled = enabled

    def begin(self, process):
        pass

    def end(self):
        pass

    def sequential_processing(self):
        return False


class CombinedActions(ReferenceFrameTask):
    def __init__(self, name, actions=[], enabled=True, **kwargs):
        step_process = kwargs.pop('step_process', DEFAULTS['reference_frame_task']['step_process'])
        ReferenceFrameTask.__init__(self, name, enabled, step_process=step_process, **kwargs)
        self._actions = actions
        self._metadata = (None, None)

    def begin(self):
        self.callback(constants.CALLBACK_ADD_STATUS_BOX, self.output_path)
        n_actions = len(self._actions)
        filenames = self.input_filepaths()
        if len(filenames) == 0:
            raise ValueError("No image files found in the selected path")
        for input_filename in filenames:
            output_path = os.path.join(
                self.output_full_path(), os.path.basename(get_output_filename(input_filename)))
            self.callback(
                constants.CALLBACK_ADD_FRAME, self.output_path, output_path, n_actions)
        ReferenceFrameTask.begin(self)
        for a in self._actions:
            if a.enabled:
                a.begin(self)

    def img_ref(self, idx):
        input_path = self.input_filepath(idx)
        try:
            img = read_img(input_path)
            if img is None:
                self.print_message(
                    color_str(f"file {input_path} does not contain a valid image",
                              constants.LOG_COLOR_ALERT),
                    level=logging.ERROR)
            else:
                self._metadata = get_img_metadata(img)
        except Exception as e:
            img = None
            self.print_message(
                color_str(f"can't read file {input_path}: {str(e)}", constants.LOG_COLOR_ALERT),
                level=logging.ERROR)
        return img

    def saved_img_ref(self, idx):
        input_filename = os.path.basename(get_output_filename(self.input_filepath(idx)))
        saved_filename = os.path.join(self.output_full_path(), input_filename)
        try:
            img = read_img(saved_filename)
            if img is None:
                self.print_message(
                    color_str(f"file {input_filename} does not contain a valid image",
                              constants.LOG_COLOR_ALERT),
                    level=logging.ERROR)
            else:
                self._metadata = get_img_metadata(img)
        except Exception as e:
            img = None
            self.print_message(
                color_str(f"can't read file {input_filename}: {str(e)}", constants.LOG_COLOR_ALERT),
                level=logging.ERROR)
        return img

    def frame_str(self, idx=-1):
        if self.run_sequential():
            idx = self.current_action_count
        return f"frame {idx + 1}/{self.total_action_counts}"

    def run_frame(self, idx, ref_idx):
        input_path = self.input_filepath(idx)
        input_filename = os.path.basename(input_path)
        output_path = os.path.join(
            self.output_full_path(), os.path.basename(get_output_filename(input_filename)))
        self.print_message(
            color_str(color_str(f'read input {self.frame_str(idx)}, '
                      f'{os.path.basename(input_path)}'), constants.LOG_COLOR_LEVEL_3))
        try:
            img = read_img(input_path)
            if img is None:
                self.print_message(color_str(f"Invalid file: {os.path.basename(input_path)}",
                                             constants.LOG_COLOR_ALERT),
                                   level=logging.ERROR)
            else:
                validate_image(img, *(self._metadata))
        except Exception as e:
            img = None
            self.print_message(color_str(f"can't read file {input_path}: {str(e)}",
                                         constants.LOG_COLOR_ALERT),
                               level=logging.ERROR)
        if len(self._actions) == 0:
            self.sub_message(color_str(": no actions specified", constants.LOG_COLOR_ALERT),
                             level=logging.WARNING)
        for a_idx, a in enumerate(self._actions):
            if not a.enabled:
                self.get_logger().warning(color_str(f"{self.base_message}: sub-action disabled",
                                                    constants.LOG_COLOR_ALERT))
            else:
                if self.callback(constants.CALLBACK_CHECK_RUNNING, self.id, self.name) is False:
                    raise RunStopException(self.name)
                self.callback(constants.CALLBACK_UPDATE_FRAME_STATUS, self.output_path,
                              output_path, a_idx + 1)
                if img is not None:
                    img = a.run_frame(idx, ref_idx, img)
                else:
                    self.print_message(
                        color_str("null input received, action skipped",
                                  constants.LOG_COLOR_ALERT),
                        level=logging.ERROR)
        if img is not None:
            self.print_message(
                color_str(f'write output {self.frame_str(idx)}, '
                          f'{os.path.basename(output_path)}', constants.LOG_COLOR_LEVEL_3))
            write_img(output_path, img)
            self.callback(
                constants.CALLBACK_UPDATE_FRAME_STATUS, self.output_path, output_path, 1000)
            return img
        self.print_message(color_str(
            f"no output resulted from processing input file: {os.path.basename(input_path)}",
            constants.LOG_COLOR_ALERT), level=logging.ERROR)
        self.callback(
            constants.CALLBACK_UPDATE_FRAME_STATUS, self.output_path, output_path, 1001)
        return None

    def end(self):
        for a in self._actions:
            if a.enabled:
                a.end()

    def end_job(self):
        ReferenceFrameTask.end_job(self)

    def sequential_processing(self):
        for a in self._actions:
            if a.sequential_processing():
                return True
        return False
