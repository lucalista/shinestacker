import numpy as np
import cv2
import os
from termcolor import colored
from .exif import copy_exif
from focus_stack.utils import write_img
from focus_stack.stack_framework import FrameDirectory, JobBase, ActionList
from focus_stack.exceptions import InvalidOptionError

EXTENSIONS = set(["jpeg", "jpg", "png", "tif", "tiff"])


class FocusStackBase:
    def __init__(self, stack_algo, exif_path='', postfix='', denoise=0):
        self.stack_algo = stack_algo
        self.exif_path = exif_path
        self.postfix = postfix
        self.denoise = denoise
        self.stack_algo.messenger(self)

    def focus_stack(self, filenames):
        self.sub_message_r(': reading input files')
        img_files = sorted([os.path.join(self.input_dir, name) for name in filenames])
        stacked_img = self.stack_algo.focus_stack(img_files)
        in_filename = filenames[0].split(".")
        out_filename = self.output_dir + "/" + in_filename[0] + self.postfix + '.' + '.'.join(in_filename[1:])
        if self.denoise > 0:
            self.sub_message_r(': denoise image')
            stacked_img = cv2.fastNlMeansDenoisingColored(stacked_img, None, self.denoise, self.denoise, 7, 21)
        write_img(out_filename, stacked_img)
        if self.exif_path != '' and stacked_img.dtype == np.uint8:
            self.sub_message_r(': copy exif data')
            dirpath, _, fnames = next(os.walk(self.exif_path))
            fnames = [name for name in fnames if os.path.splitext(name)[-1][1:].lower() in EXTENSIONS]
            exif_filename = self.exif_path + '/' + fnames[0]
            copy_exif(exif_filename, out_filename)
            self.sub_message_r(' ' * 60)

    def init(self, job, working_path):
        if self.exif_path is None:
            self.exif_path = job.paths[0]
        if self.exif_path != '':
            self.exif_path = working_path + "/" + self.exif_path


class FocusStackBunch(FrameDirectory, ActionList, FocusStackBase):
    def __init__(self, name, stack_algo, input_path='', output_path='', working_path='',
                 resample=1, exif_path='', postfix='', frames=10, overlap=0, denoise=0):
        FrameDirectory.__init__(self, name, input_path, output_path, working_path, '', resample)
        ActionList.__init__(self, name)
        FocusStackBase.__init__(self, stack_algo, exif_path, postfix, denoise)
        if overlap >= frames:
            raise InvalidOptionError("overlap", overlap, "overlap must be smaller than batch size")
        self.frames = frames
        self.overlap = overlap

    def begin(self):
        ActionList.begin(self)
        fnames = self.folder_filelist(self.input_dir)
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


class FocusStack(FrameDirectory, JobBase, FocusStackBase):
    def __init__(self, name, stack_algo, input_path='', output_path='', working_path='', resample=1, exif_path='', postfix='', denoise=0):
        self.name = name
        FrameDirectory.__init__(self, name, input_path, output_path, working_path, '', resample)
        JobBase.__init__(self, name)
        FocusStackBase.__init__(self, stack_algo, exif_path, postfix, denoise)

    def run_core(self):
        self.set_filelist()
        self.focus_stack(self.filenames)

    def init(self, job):
        FrameDirectory.init(self, job)
        FocusStackBase.init(self, job, self.working_path)
