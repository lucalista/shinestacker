import numpy as np
import cv2
import os
from termcolor import colored
from .exif import copy_exif
from config.constants import constants
from core.framework import JobBase
from core.exceptions import InvalidOptionError
from algorithms.utils import write_img
from algorithms.stack_framework import FrameDirectory, ActionList


class FocusStackBase:
    def __init__(self, stack_algo, exif_path='',
                 prefix=constants.DEFAULT_STACK_PREFIX,
                 denoise=0, plot_stack=False):
        self.stack_algo = stack_algo
        self.exif_path = exif_path
        self.prefix = prefix if prefix != '' else constants.DEFAULT_STACK_PREFIX
        self.denoise = denoise
        self.plot_stack = plot_stack
        self.stack_algo.process = self
        self.frame_count = -1

    def focus_stack(self, filenames):
        self.sub_message_r(': reading input files')
        img_files = sorted([os.path.join(self.input_full_path, name) for name in filenames])
        stacked_img = self.stack_algo.focus_stack(img_files)
        in_filename = filenames[0].split(".")
        out_filename = f"{self.output_dir}/{self.prefix}{in_filename[0]}." + '.'.join(in_filename[1:])
        if self.denoise > 0:
            self.sub_message_r(': denoise image')
            stacked_img = cv2.fastNlMeansDenoisingColored(stacked_img, None, self.denoise, self.denoise, 7, 21)
        write_img(out_filename, stacked_img)
        if self.exif_path != '' and stacked_img.dtype == np.uint8:
            self.sub_message_r(': copy exif data')
            dirpath, _, fnames = next(os.walk(self.exif_path))
            fnames = [name for name in fnames if os.path.splitext(name)[-1][1:].lower() in constants.EXTENSIONS]
            exif_filename = f"{self.exif_path}/{fnames[0]}"
            copy_exif(exif_filename, out_filename)
            self.sub_message_r(' ' * 60)
        if self.plot_stack:
            idx_str = "{:04d}".format(self.frame_count) if self.frame_count >= 0 else ''
            name = f"{self.name}: {self.stack_algo.name()}"
            if idx_str != '':
                name += f"\nbunch: {idx_str}"
            self.callback('save_plot', self.id, name, out_filename)
        if self.frame_count >= 0:
            self.frame_count += 1

    def init(self, job, working_path):
        if self.exif_path is None:
            self.exif_path = job.paths[0]
        if self.exif_path != '':
            self.exif_path = working_path + "/" + self.exif_path


class FocusStackBunch(FocusStackBase, FrameDirectory, ActionList):
    def __init__(self, name, stack_algo, enabled=True, **kwargs):
        FocusStackBase.__init__(self, stack_algo,
                                exif_path=kwargs.pop('exif_path', ''),
                                prefix=kwargs.pop('prefix', constants.DEFAULT_STACK_PREFIX),
                                denoise=kwargs.pop('denoise', 0),
                                plot_stack=kwargs.pop('plot_stack', constants.DEFAULT_PLOT_STACK_BUNCH))
        FrameDirectory.__init__(self, name, **kwargs)
        ActionList.__init__(self, name, enabled)
        self.frame_count = 0
        self.frames = kwargs.get('frames', constants.DEFAULT_FRAMES)
        self.overlap = kwargs.get('overlap', constants.DEFAULT_OVERLAP)
        self.denoise = kwargs.get('denoise', 0)
        if self.overlap >= self.frames:
            raise InvalidOptionError("overlap", self.overlap, "overlap must be smaller than batch size")

    def begin(self):
        ActionList.begin(self)
        fnames = self.folder_filelist(self.input_full_path)
        self.__chunks = [fnames[x:x + self.frames] for x in range(0, len(fnames) - self.overlap, self.frames - self.overlap)]
        self.set_counts(len(self.__chunks))

    def end(self):
        ActionList.end(self)

    def run_step(self):
        self.print_message_r(colored("fusing bunch: {}".format(self.count), "blue"))
        self.focus_stack(self.__chunks[self.count - 1])

    def init(self, job):
        FrameDirectory.init(self, job)
        FocusStackBase.init(self, job, self.working_path)


class FocusStack(FocusStackBase, FrameDirectory, JobBase):
    def __init__(self, name, stack_algo, enabled=True, **kwargs):
        FocusStackBase.__init__(self, stack_algo,
                                exif_path=kwargs.pop('exif_path', ''),
                                prefix=kwargs.pop('prefix', constants.DEFAULT_STACK_PREFIX),
                                denoise=kwargs.pop('denoise', 0),
                                plot_stack=kwargs.pop('plot_stack', constants.DEFAULT_PLOT_STACK))
        FrameDirectory.__init__(self, name, **kwargs)
        JobBase.__init__(self, name, enabled)

    def run_core(self):
        self.set_filelist()
        self.focus_stack(self.filenames)

    def init(self, job):
        FrameDirectory.init(self, job)
        FocusStackBase.init(self, job, self.working_path)
