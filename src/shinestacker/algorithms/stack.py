# pylint: disable=C0114, C0115, C0116, R0913, R0917
import os
import numpy as np
from .. config.constants import constants
from .. core.framework import JobBase
from .. core.colors import color_str
from .. core.exceptions import InvalidOptionError
from .utils import write_img
from .stack_framework import FrameDirectory, ActionList
from .exif import copy_exif_from_file_to_file
from .denoise import denoise


class FocusStackBase(JobBase, FrameDirectory):
    def __init__(self, name, stack_algo, enabled=True, **kwargs):
        FrameDirectory.__init__(self, name, **kwargs)
        JobBase.__init__(self, name, enabled)
        self.stack_algo = stack_algo
        self.exif_path = kwargs.pop('exif_path', '')
        self.prefix = kwargs.pop('prefix', constants.DEFAULT_STACK_PREFIX)
        self.denoise_amount = kwargs.pop('denoise_amount', 0)
        self.plot_stack = kwargs.pop('plot_stack', constants.DEFAULT_PLOT_STACK)
        self.stack_algo.process = self
        self.frame_count = -1

    def focus_stack(self, filenames):
        self.sub_message_r(color_str(': reading input files', constants.LOG_COLOR_LEVEL_3))
        img_files = sorted([os.path.join(self.input_full_path, name) for name in filenames])
        stacked_img = self.stack_algo.focus_stack(img_files)
        in_filename = filenames[0].split(".")
        out_filename = f"{self.output_dir}/{self.prefix}{in_filename[0]}." + \
            '.'.join(in_filename[1:])
        if self.denoise_amount > 0:
            self.sub_message_r(': denoise image')
            stacked_img = denoise(stacked_img, self.denoise_amount, self.denoise_amount)
        write_img(out_filename, stacked_img)
        if self.exif_path != '' and stacked_img.dtype == np.uint8:
            self.sub_message_r(': copy exif data')
            _dirpath, _, fnames = next(os.walk(self.exif_path))
            fnames = [name for name in fnames
                      if os.path.splitext(name)[-1][1:].lower() in constants.EXTENSIONS]
            exif_filename = f"{self.exif_path}/{fnames[0]}"
            copy_exif_from_file_to_file(exif_filename, out_filename)
            self.sub_message_r(' ' * 60)
        if self.plot_stack:
            idx_str = f"{self.frame_count + 1:04d}" if self.frame_count >= 0 else ''
            name = f"{self.name}: {self.stack_algo.name()}"
            if idx_str != '':
                name += f"\nbunch: {idx_str}"
            self.callback('save_plot', self.id, name, out_filename)
        if self.frame_count >= 0:
            self.frame_count += 1

    def init(self, job, working_path=''):
        if self.exif_path is None:
            self.exif_path = job.paths[0]
        if self.exif_path != '':
            self.exif_path = working_path + "/" + self.exif_path


def get_bunches(collection, n_frames, n_overlap):
    bunches = [collection[x:x + n_frames]
               for x in range(0, len(collection) - n_overlap, n_frames - n_overlap)]
    return bunches


class FocusStackBunch(ActionList, FocusStackBase):
    def __init__(self, name, stack_algo, enabled=True, **kwargs):
        ActionList.__init__(self, name, enabled)
        FocusStackBase.__init__(self, name, stack_algo, enabled, **kwargs)
        self._chunks = None
        self.frame_count = 0
        self.frames = kwargs.get('frames', constants.DEFAULT_FRAMES)
        self.overlap = kwargs.get('overlap', constants.DEFAULT_OVERLAP)
        self.denoise_amount = kwargs.get('denoise_amount', 0)
        self.stack_algo.do_step_callback = False
        if self.overlap >= self.frames:
            raise InvalidOptionError("overlap", self.overlap,
                                     "overlap must be smaller than batch size")

    def init(self, job, _working_path=''):
        FrameDirectory.init(self, job)
        FocusStackBase.init(self, job, self.working_path)

    def begin(self):
        ActionList.begin(self)
        fnames = self.folder_filelist()
        self._chunks = get_bunches(fnames, self.frames, self.overlap)
        self.set_counts(len(self._chunks))

    def end(self):
        ActionList.end(self)

    def run_step(self):
        self.print_message_r(color_str(f"fusing bunch: {self.count + 1}/{self.counts}",
                                       constants.LOG_COLOR_LEVEL_2))
        self.focus_stack(self._chunks[self.count - 1])


class FocusStack(FocusStackBase):
    def __init__(self, name, stack_algo, enabled=True, **kwargs):
        super().__init__(name, stack_algo, enabled, **kwargs)
        self.stack_algo.do_step_callback = True

    def run_core(self):
        self.set_filelist()
        self.callback('step_counts', self.id, self.name,
                      self.stack_algo.steps_per_frame() * len(self.filenames))
        self.focus_stack(self.filenames)

    def init(self, job, _working_path=''):
        FrameDirectory.init(self, job)
        FocusStackBase.init(self, job, self.working_path)
