# pylint: disable=C0114, C0115, C0116, W0102, R0902, R0903
# pylint: disable=R0917, R0913, R1702, R0912, E1111, E1121, W0613
import logging
import os
from .. config.constants import constants
from .. core.colors import color_str
from .. core.framework import Job, ActionList
from .. core.core_utils import check_path_exists
from .. core.exceptions import ShapeError, BitDepthError, RunStopException
from .utils import read_img, write_img


class StackJob(Job):
    def __init__(self, name, working_path, input_path='', **kwargs):
        check_path_exists(working_path)
        self.working_path = working_path
        if input_path == '':
            self.paths = []
        else:
            self.paths = [input_path]
        Job.__init__(self, name, **kwargs)

    def init(self, a):
        a.init(self)


class FramePaths:
    def __init__(self, name, input_path='', output_path='', working_path='',
                 plot_path=constants.DEFAULT_PLOTS_PATH,
                 scratch_output_dir=True, resample=1,
                 reverse_order=constants.DEFAULT_FILE_REVERSE_ORDER, **_kwargs):
        self.name = name
        self.working_path = working_path
        self.plot_path = plot_path
        self.input_path = input_path
        self.output_path = output_path
        self.output_dir = None
        self.resample = resample
        self.reverse_order = reverse_order
        self.scratch_output_dir = scratch_output_dir
        self.input_full_path = None
        self.enabled = None
        self.filenames = None

    def folder_filelist(self):
        assert False, "this method should be overwritten"

    def print_message(self, msg='', level=logging.INFO, end=None, begin='', tqdm=False):
        assert False, "this method should be overwritten"

    def set_filelist(self):
        self.filenames = self.folder_filelist()
        file_list = self.input_full_path.replace(self.working_path, '').lstrip('/')
        self.print_message(color_str(f": {len(self.filenames)} files in folder: {file_list}",
                                     constants.LOG_COLOR_LEVEL_2))

    def init(self, job):
        if self.working_path == '':
            self.working_path = job.working_path
        check_path_exists(self.working_path)
        if self.output_path == '':
            self.output_path = self.name
        self.output_dir = self.working_path + \
            ('' if self.working_path[-1] == '/' else '/') + \
            self.output_path
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        else:
            list_dir = os.listdir(self.output_dir)
            if len(list_dir) > 0:
                if self.scratch_output_dir:
                    if self.enabled:
                        for filename in list_dir:
                            file_path = os.path.join(self.output_dir, filename)
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                        self.print_message(
                            color_str(f": output directory {self.output_path} content erased",
                                      'yellow'))
                    else:
                        self.print_message(
                            color_str(f": module disabled, output directory {self.output_path}"
                                      " not scratched", 'yellow'))
                else:
                    self.print_message(
                        color_str(
                            f": output directory {self.output_path} not empty, "
                            "files may be overwritten or merged with existing ones.", 'yellow'
                        ), level=logging.WARNING)
        if self.plot_path == '':
            self.plot_path = self.working_path + \
                ('' if self.working_path[-1] == '/' else '/') + self.plot_path
            if not os.path.exists(self.plot_path):
                os.makedirs(self.plot_path)
        if self.input_path == '':
            if len(job.paths) == 0:
                raise RuntimeError(f"Job {job.name} does not have any configured path")
            self.input_path = job.paths[-1]
        job.paths.append(self.output_path)


class FrameDirectory(FramePaths):
    def __init__(self, name, **kwargs):
        FramePaths.__init__(self, name, **kwargs)

    def folder_list_str(self):
        if isinstance(self.input_full_path, list):
            file_list = ", ".join(
                list(self.input_full_path.replace(self.working_path, '').lstrip('/')))
            return "folder" + ('s' if len(self.input_full_path) > 1 else '') + f": {file_list}"
        return "folder: " + self.input_full_path.replace(self.working_path, '').lstrip('/')

    def folder_filelist(self):
        src_contents = os.walk(self.input_full_path)
        _dirpath, _, filenames = next(src_contents)
        filelist = [name for name in filenames
                    if os.path.splitext(name)[-1][1:].lower() in constants.EXTENSIONS]
        filelist.sort()
        if self.reverse_order:
            filelist.reverse()
        if self.resample > 1:
            filelist = filelist[0::self.resample]
        return filelist

    def init(self, job, _working_path=''):
        FramePaths.init(self, job)
        self.input_full_path = self.working_path + \
            ('' if self.working_path[-1] == '/' else '/') + self.input_path
        check_path_exists(self.input_full_path)
        job.paths.append(self.output_path)


class FrameMultiDirectory(FramePaths):
    def __init__(self, name, input_path='', output_path='', working_path='',
                 plot_path=constants.DEFAULT_PLOTS_PATH,
                 scratch_output_dir=True, resample=1,
                 reverse_order=constants.DEFAULT_FILE_REVERSE_ORDER, **_kwargs):
        FramePaths.__init__(self, name, input_path, output_path, working_path, plot_path,
                            scratch_output_dir, resample, reverse_order)
        self.input_full_path = None

    def folder_list_str(self):
        if isinstance(self.input_full_path, list):
            file_list = ", ".join([d.replace(self.working_path, '').lstrip('/')
                                   for d in self.input_full_path])
            return "folder" + ('s' if len(self.input_full_path) > 1 else '') + f": {file_list}"
        return "folder: " + self.input_full_path.replace(self.working_path, '').lstrip('/')

    def folder_filelist(self):
        if isinstance(self.input_full_path, str):
            dirs = [self.input_full_path]
            paths = [self.input_path]
        elif hasattr(self.input_full_path, "__len__"):
            dirs = self.input_full_path
            paths = self.input_path
        else:
            raise RuntimeError("input_full_path option must contain a path or an array of paths")
        files = []
        for d, p in zip(dirs, paths):
            filelist = []
            for _dirpath, _, filenames in os.walk(d):
                filelist = [p + "/" + name
                            for name in filenames
                            if os.path.splitext(name)[-1][1:].lower() in constants.EXTENSIONS]
                if self.reverse_order:
                    filelist.reverse()
                if self.resample > 1:
                    filelist = filelist[0::self.resample]
                files += filelist
            if len(files) == 0:
                self.print_message(color_str(f"input folder {p} does not contain any image", "red"),
                                   level=logging.WARNING)
        return files

    def init(self, job):
        FramePaths.init(self, job)
        if isinstance(self.input_path, str):
            self.input_full_path = self.working_path + \
                ('' if self.working_path[-1] == '/' else '/') + \
                self.input_path
            check_path_exists(self.input_full_path)
        elif hasattr(self.input_path, "__len__"):
            self.input_full_path = []
            for path in self.input_path:
                self.input_full_path.append(self.working_path +
                                            ('' if self.working_path[-1] == '/' else '/') +
                                            path)
        job.paths.append(self.output_path)


class FramesRefActions(ActionList, FrameDirectory):
    def __init__(self, name, enabled=True, ref_idx=-1, step_process=False, **kwargs):
        FrameDirectory.__init__(self, name, **kwargs)
        ActionList.__init__(self, name, enabled)
        self.ref_idx = ref_idx
        self.step_process = step_process
        self._idx = None
        self._ref_idx = None
        self._idx_step = None

    def begin(self):
        ActionList.begin(self)
        self.set_filelist()
        self.set_counts(len(self.filenames))
        if self.ref_idx == -1:
            self.ref_idx = len(self.filenames) // 2

    def end(self):
        ActionList.end(self)

    def run_frame(self, _idx, _ref_idx):
        pass

    def run_step(self):
        if self.count == 0:
            self._idx = self.ref_idx if self.step_process else 0
            self._ref_idx = self.ref_idx
            self._idx_step = +1
        ll = len(self.filenames)
        self.print_message_r(
            color_str(f"step {self.count + 1}/{ll}: process file: {self.filenames[self._idx]}, "
                      f"reference: {self.filenames[self._ref_idx]}", constants.LOG_COLOR_LEVEL_2))
        self.run_frame(self._idx, self._ref_idx)
        if self._idx < ll:
            if self.step_process:
                self._ref_idx = self._idx
            self._idx += self._idx_step
        if self._idx == ll:
            self._idx = self.ref_idx - 1
            if self.step_process:
                self._ref_idx = self.ref_idx
            self._idx_step = -1


class SubAction:
    def __init__(self, enabled=True):
        self.enabled = enabled

    def begin(self, process):
        pass

    def end(self):
        pass


class CombinedActions(FramesRefActions):
    def __init__(self, name, actions=[], enabled=True, **kwargs):
        FramesRefActions.__init__(self, name, enabled, **kwargs)
        self._actions = actions
        self.dtype = None
        self.shape = None

    def begin(self):
        FramesRefActions.begin(self)
        for a in self._actions:
            if a.enabled:
                a.begin(self)

    def img_ref(self, idx):
        filename = self.filenames[idx]
        img = read_img((self.output_dir
                        if self.step_process else self.input_full_path) + f"/{filename}")
        if img is None:
            raise RuntimeError(f"Invalid file: {self.input_full_path}/{filename}")
        self.dtype = img.dtype
        self.shape = img.shape
        return img

    def run_frame(self, idx, ref_idx):
        filename = self.filenames[idx]
        self.sub_message_r(color_str(': read input image', constants.LOG_COLOR_LEVEL_3))
        img = read_img(f"{self.input_full_path}/{filename}")
        if self.dtype is not None and img.dtype != self.dtype:
            raise BitDepthError(self.dtype, img.dtype, )
        if self.shape is not None and img.shape != self.shape:
            raise ShapeError(self.shape, img.shape)
        if img is None:
            raise RuntimeError(f"Invalid file: {self.input_full_path}/{filename}")
        if len(self._actions) == 0:
            self.sub_message(color_str(": no actions specified.", constants.LOG_COLOR_ALERT),
                             level=logging.WARNING)
        for a in self._actions:
            if not a.enabled:
                self.get_logger().warning(color_str(f"{self.base_message}: sub-action disabled",
                                                    'red'))
            else:
                if self.callback('check_running', self.id, self.name) is False:
                    raise RunStopException(self.name)
                img = a.run_frame(idx, ref_idx, img)
        self.sub_message_r(color_str(': write output image', constants.LOG_COLOR_LEVEL_3))
        if img is not None:
            write_img(self.output_dir + "/" + filename, img)
        else:
            self.print_message(color_str(
                "No output file resulted from processing input file: "
                f"{self.input_full_path}/{filename}",
                constants.LOG_COLOR_ALERT), level=logging.WARNING)

    def end(self):
        for a in self._actions:
            if a.enabled:
                a.end()
