from .framework import  Job, ActionList, Timer
from .utils import check_path_exists
from termcolor import colored, cprint
import os

class StackJob(Job):
    def __init__(self, name, working_directory, input_path=None):
        check_path_exists(working_directory)
        self.working_directory = working_directory
        if input_path is None or input_path == '': self.paths = []
        else: self.paths = [input_path]
        Job.__init__(self, name)
    def init(self, a):
        a.init(self)

class FrameDirectory:
    EXTENSIONS = set(["jpeg", "jpg", "png", "tif", "tiff"])
    def __init__(self, name, input_path=None, output_path=None, working_directory=None):
        self.name = name
        self.working_directory = working_directory
        self.input_path = input_path
        self.output_path = output_path
    def folder_filelist(self, path):
        src_contents = os.walk(self.input_dir)
        dirpath, _, filenames = next(src_contents)
        return [name for name in filenames if os.path.splitext(name)[-1][1:].lower() in FrameDirectory.EXTENSIONS]
    def set_filelist(self):
        self.filenames = self.folder_filelist(self.input_dir)
        cprint("{} files ".format(len(self.filenames)) + "in folder: '" + self.input_dir + "'", 'blue')
    def init(self, job):
        if self.working_directory is None: self.working_directory = job.working_directory
        check_path_exists(self.working_directory)
        if self.input_path is None:
            assert len(job.paths)>0, "No input path has been specified in " + job.name
            self.input_path = job.paths[-1]
        self.input_dir = self.working_directory + ('' if self.working_directory[-1] == '/' else '/') + self.input_path
        check_path_exists(self.input_dir)
        if self.output_path is None: self.output_path = self.name
        self.output_dir = self.working_directory + ('' if self.working_directory[-1] == '/' else '/') + self.output_path
        if not os.path.exists(self.output_dir): os.makedirs(self.output_dir)        
        job.paths.append(self.output_path)
        
class FramesRefActions(FrameDirectory, ActionList):
    def __init__(self, name, input_path=None, output_path=None, working_directory=None, ref_idx=-1, step_process=False):
        FrameDirectory.__init__(self, name, input_path, output_path, working_directory)
        ActionList.__init__(self, name)
        self.ref_idx = ref_idx
        self.step_process = step_process
    def begin(self):
        self.set_filelist()
        self.counts = len(self.filenames)
        if self.ref_idx == -1: self.ref_idx = len(self.filenames) // 2
    def run_step(self):
        cprint("action: {} ".format(self.filenames[self.count - 1]), "blue", end='\r')
        if self.count == 1:
            self.__idx = self.ref_idx if self.step_process else 0
            self.__ref_idx = self.ref_idx
            self.__idx_step = +1
        self.run_frame(self.__idx, self.__ref_idx)
        ll = len(self.filenames)
        if(self.__idx < ll):
            if self.step_process: self.__ref_idx = self.__idx
            self.__idx += self.__idx_step
        if(self.__idx == ll):
            self.__idx = self.ref_idx - 1
            if self.step_process: self.__ref_idx = self.ref_idx
            self.__idx_step = -1
            
        