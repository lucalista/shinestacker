import numpy as np
import cv2
from .pyramid import PyramidStack
from .depth_map import DepthMapStack
from .utils import copy_exif
from focus_stack.utils import read_img, write_img
from focus_stack.stack_framework import *

EXTENSIONS = set(["jpeg", "jpg", "png", "tif", "tiff"])

class FocusStackBase:
    def __init__(self, stack_algo, exif_dir=None, postfix='', denoise=0):
        self.stack_algo = stack_algo
        self.exif_dir = exif_dir
        self.postfix = postfix
        self.denoise = denoise
    def focus_stack(self, filenames):
        img_files = sorted([os.path.join(self.input_dir, name) for name in filenames])
        img_files = [read_img(name) for name in img_files]
        if any([img is None for img in img_files]):
            raise RuntimeError("failed to load one or more image files.")
        img_files = np.array(img_files, dtype=img_files[0].dtype)
        stacked_img = self.stack_algo.focus_stack(img_files)
        in_filename = filenames[0].split(".")
        out_filename = self.output_dir + "/" + in_filename[0] + self.postfix + '.' + '.'.join(in_filename[1:])
        if self.denoise > 0:
            stacked_img = cv2.fastNlMeansDenoisingColored(stacked_img, None, self.denoise, self.denoise, 7, 21)
        write_img(out_filename, stacked_img)
        if self.exif_dir != '':
            dirpath, _, fnames = next(os.walk(self.exif_dir))
            fnames = [name for name in fnames if os.path.splitext(name)[-1][1:].lower() in EXTENSIONS]
            exif_filename = self.exif_dir + '/' + fnames[0]
            copy_exif(exif_filename, out_filename)
    def init(self, job, working_directory):
        if self.exif_dir is None: self.exif_dir = job.paths[0]
        if self.exif_dir != '': self.exif_dir = working_directory + "/" + self.exif_dir
        
class FocusStackBunch(FrameDirectory, ActionList, FocusStackBase):
    def __init__(self, name, stack_algo, input_path=None, output_path=None, working_directory=None, exif_dir=None, postfix='', frames=10, overlap=0, denoise=0):
        FrameDirectory.__init__(self, name, input_path, output_path, working_directory)
        ActionList.__init__(self, name)
        FocusStackBase.__init__(self, stack_algo, exif_dir, postfix, denoise)
        if overlap >= frames: raise Exception("Overlap must be smaller than batch size")
        self.frames = frames
        self.overlap = overlap
    def begin(self):
        fnames = self.folder_filelist(self.input_dir)
        self.__chunks = [fnames[x:x + self.frames] for x in range(0, len(fnames) - self.overlap, self.frames - self.overlap)]
        self.counts = len(self.__chunks)
    def run_step(self):
        print("bunch: {}                    ".format(self.count), end='\r')
        self.focus_stack(self.__chunks[self.count - 1])
    def init(self, job):
        FrameDirectory.init(self, job)
        FocusStackBase.init(self, job, self.working_directory)
        
class FocusStack(FrameDirectory, Timer, FocusStackBase):
    def __init__(self, name, stack_algo, input_path=None, output_path=None, working_directory=None, exif_dir=None, postfix='', denoise=0):
        self.name = name
        FrameDirectory.__init__(self, name, input_path, output_path, working_directory)
        Timer.__init__(self, name)
        FocusStackBase.__init__(self, stack_algo, exif_dir, postfix, denoise)
    def run_core(self):
        cprint("running " + self.name, "blue", attrs=["bold"])
        self.set_filelist()
        self.focus_stack(self.filenames)
    def init(self, job):
        FrameDirectory.init(self, job)
        FocusStackBase.init(self, job, self.working_directory)