from .framework import  Job, ActionList, Timer
from .helper import chunks
from termcolor import colored, cprint
import os

class StackJob(Job):
    def __init__(self, name, wdir):
        assert  os.path.exists(wdir), 'Path does not exist: ' + wdir
        self.working_directory = wdir
        Job.__init__(self, name)
        
class FrameDirectory:
    EXTENSIONS = set(["jpeg", "jpg", "png", "tif", "tiff"])
    def __init__(self, wdir, name, input_path, output_path=''):
        assert  os.path.exists(wdir), 'Path does not exist: ' + wdir
        self.working_directory = wdir
        self.input_dir = wdir + input_path
        assert  os.path.exists(self.input_dir), 'path does not exist: ' + self.input_dir
        if output_path=='': output_path = name
        self.output_dir = wdir + output_path
        if not os.path.exists(self.output_dir): os.makedirs(self.output_dir)
    def folder_filelist(self, path):
        src_contents = os.walk(self.input_dir)
        dirpath, _, filenames = next(src_contents)
        return [name for name in filenames if os.path.splitext(name)[-1][1:].lower() in FrameDirectory.EXTENSIONS]
    def set_filelist(self):
        self.filenames = self.folder_filelist(self.input_dir)
        cprint("{} files ".format(len(self.filenames)) + "in folder: '" + self.input_dir + "'", 'blue')
        
class FramesRefActions(FrameDirectory, ActionList):
    def __init__(self, wdir, name, input_path, output_path='', ref_idx=-1, step_process=False):
        FrameDirectory.__init__(self, wdir, name, input_path, output_path)
        ActionList.__init__(self, name)
        self.ref_idx = ref_idx
        self.step_process = step_process
        assert  os.path.exists(wdir + input_path), 'path does not exist: ' + wdir + input_path
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
            
        