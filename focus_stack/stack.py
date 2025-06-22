import numpy as np
import cv2
import os
from termcolor import colored
import matplotlib.pyplot as plt
from .exif import copy_exif
from focus_stack.utils import write_img, save_plot, img_8bit
from focus_stack.framework import JobBase
from focus_stack.stack_framework import FrameDirectory, ActionList
from focus_stack.exceptions import InvalidOptionError

EXTENSIONS = set(["jpeg", "jpg", "png", "tif", "tiff"])
DEFAULT_FRAMES = 10


class FocusStackBase:
    def __init__(self, stack_algo, exif_path='', postfix='', denoise=0, plot_stack=False):
        self.stack_algo = stack_algo
        self.exif_path = exif_path
        self.postfix = postfix
        self.denoise = denoise
        self.plot_stack = plot_stack
        self.stack_algo.messenger(self)
        self.frame_count = -1

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
        if self.plot_stack:
            idx_str = "{:04d}".format(self.frame_count) if self.frame_count >= 0 else ''
            idx_postfix = f"-{idx_str}" if idx_str != '' else ''
            plot_path = f"{self.working_path}/{self.plot_path}/{self.name}-stack{idx_postfix}.pdf"
            plt.figure(figsize=(10, 5))
            plt.title("Stack" + (f", bunch: {idx_str}" if idx_str != '' else ''))
            plot_img = cv2.cvtColor(img_8bit(stacked_img), cv2.COLOR_BGR2RGB)
            plt.imshow(plot_img, 'gray')
            save_plot(plot_path)
            plt.close('all')
            name = f"{self.name}: stack"
            if idx_str != '':
                name += f"\n bunch: {idx_str}"
            self.callback('save_plot', self.id, name, plot_path)
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
                                postfix=kwargs.pop('postfix', ''),
                                denoise=kwargs.pop('denoise', 0),
                                plot_stack=kwargs.pop('plot_stack', ''))
        FrameDirectory.__init__(self, name, **kwargs)
        ActionList.__init__(self, name, enabled)
        self.frame_count = 0
        self.frames = kwargs.get('frames', DEFAULT_FRAMES)
        self.overlap = kwargs.get('overlap', 0)
        self.denoise = kwargs.get('denoise', 0)
        if self.overlap >= self.frames:
            raise InvalidOptionError("overlap", self.overlap, "overlap must be smaller than batch size")

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
    def __init__(self, name, stack_algo, enabled=True, **kwargs):
        FrameDirectory.__init__(self, name, **kwargs)
        JobBase.__init__(self, name, enabled)
        FocusStackBase.__init__(self, stack_algo,
                                exif_path=kwargs.pop('exif_path', ''),
                                postfix=kwargs.pop('postfix', ''),
                                denoise=kwargs.pop('denoise', 0),
                                plot_stack=kwargs.pop('plot_stack', ''))

    def run_core(self):
        self.set_filelist()
        self.focus_stack(self.filenames)

    def init(self, job):
        FrameDirectory.init(self, job)
        FocusStackBase.init(self, job, self.working_path)
