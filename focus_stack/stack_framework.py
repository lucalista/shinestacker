from .framework import  Job, ActionList, JobBase
from .utils import check_path_exists
from focus_stack.utils import read_img, write_img
from termcolor import colored
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
    def __init__(self, name, input_path=None, output_path=None, working_directory=None, resample=1, reverse_order=False):
        self.name = name
        self.working_directory = working_directory
        self.input_path = input_path
        self.output_path = output_path
        self.resample = resample
        self.reverse_order = reverse_order
    def folder_filelist(self, path):
        src_contents = os.walk(self.input_dir)
        dirpath, _, filenames = next(src_contents)
        filelist = [name for name in filenames if os.path.splitext(name)[-1][1:].lower() in FrameDirectory.EXTENSIONS]
        if self.reverse_order: filelist.reverse()
        if self.resample > 1: filelist = filelist[0::self.resample]
        return filelist
    def set_filelist(self):
        self.filenames = self.folder_filelist(self.input_dir)
        print(colored("{} files ".format(len(self.filenames)) + "in folder: '" + self.input_dir + "'", 'blue'))
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

class FrameMultiDirectory:
    EXTENSIONS = set(["jpeg", "jpg", "png", "tif", "tiff"])
    def __init__(self, name, input_path=None, output_path=None, working_directory=None, resample=1, reverse_order=False):
        self.name = name
        self.working_directory = working_directory
        self.input_path = input_path
        self.output_path = output_path
        self.resample = resample
        self.reverse_order = reverse_order
    def folder_filelist(self):
        if isinstance(self.input_dir, str):
            dirs = [self.input_dir]
            paths = [self.input_path]
        elif hasattr(self.input_dir, "__len__"):
            dirs = self.input_dir
            paths = self.input_path
        else:
            raise Exception("input_dir option must containa path or an array of paths") 
        files = []
        for d, p in zip(dirs, paths):
            src_contents = os.walk(d)
            dirpath, _, filenames = next(src_contents)
            filelist = [p + "/" + name for name in filenames if os.path.splitext(name)[-1][1:].lower() in FrameDirectory.EXTENSIONS]
            if self.reverse_order: filelist.reverse()
            if self.resample > 1: filelist = filelist[0::self.resample]
            files += filelist
        return files
    def set_filelist(self):
        self.filenames = self.folder_filelist()
        print(colored("{} files ".format(len(self.filenames)) + "in folder: '" + self.input_dir + "'", 'blue'))
    def init(self, job):
        if self.working_directory is None: self.working_directory = job.working_directory
        check_path_exists(self.working_directory)
        if self.input_path is None:
            assert len(job.paths)>0, "No input path has been specified in " + job.name
            self.input_path = job.paths[-1]
        if isinstance(self.input_path, str):
            self.input_dir = self.working_directory + ('' if self.working_directory[-1] == '/' else '/') + self.input_path
            check_path_exists(self.input_dir)
        elif hasattr(self.input_path, "__len__"):
            self.input_dir = []
            for path in self.input_path:
                self.input_dir.append(self.working_directory + ('' if self.working_directory[-1] == '/' else '/') + path)
                check_path_exists(self.input_dir[-1])        
        if self.output_path is None: self.output_path = self.name
        self.output_dir = self.working_directory + ('' if self.working_directory[-1] == '/' else '/') + self.output_path
        if not os.path.exists(self.output_dir): os.makedirs(self.output_dir)        
        job.paths.append(self.output_path)
        
class FramesRefActions(FrameDirectory, ActionList):
    def __init__(self, name, input_path=None, output_path=None, working_directory=None, resample=1, ref_idx=-1, step_process=False):
        FrameDirectory.__init__(self, name, input_path, output_path, working_directory, resample)
        ActionList.__init__(self, name)
        self.ref_idx = ref_idx
        self.step_process = step_process
    def begin(self):
        self.set_filelist()
        self.counts = len(self.filenames)
        if self.ref_idx == -1: self.ref_idx = len(self.filenames) // 2
    def run_frame(self, idx, ref_idx):
        assert(False), 'abstract method'
    def run_step(self):
        if self.count == 1:
            self.__idx = self.ref_idx if self.step_process else 0
            self.__ref_idx = self.ref_idx
            self.__idx_step = +1
        ll = len(self.filenames)
        self.print_message(colored("step {}/{}: process file: {}, reference: {} ".format(self.count, ll, self.filenames[self.__idx], self.filenames[self.__ref_idx]), "blue"), end='\r')
        self.run_frame(self.__idx, self.__ref_idx)
        if(self.__idx < ll):
            if self.step_process: self.__ref_idx = self.__idx
            self.__idx += self.__idx_step
        if(self.__idx == ll):
            self.__idx = self.ref_idx - 1
            if self.step_process: self.__ref_idx = self.ref_idx
            self.__idx_step = -1
            
class MultiRefActions(FramesRefActions):
    def __init__(self, name, input_path=None, output_path=None, working_directory=None, resample=1, ref_idx=-1, step_process=True, actions=None):
        FramesRefActions.__init__(self, name, input_path, output_path, working_directory, resample, ref_idx, step_process)
        self.__actions = []
        for a in actions:
            self.__actions.append(a)
    def begin(self):
        FramesRefActions.begin(self)
        for a in self.__actions:
            a.begin(self)
    def img_ref(self, idx):
        filename = self.filenames[idx]
        img = read_img((self.output_dir if self.step_process else self.input_dir)  + "/" + filename)
        if img is None: raise Exception("Invalid file: " + self.input_dir + "/" + filename)
        return img 
    def run_frame(self, idx, ref_idx):
        filename = self.filenames[idx]
        self.sub_message('- read image        ', end='\r')
        img = read_img(self.input_dir + "/" + filename)
        if img is None: raise Exception("Invalid file: " + self.input_dir + "/" + filename)
        if idx == ref_idx:
            write_img(self.output_dir + "/" + filename, img)
            return
        for a in self.__actions:
            img = a.run_frame(idx, ref_idx, img)
        self.sub_message('- write image        ', end='\r')
        write_img(self.output_dir + "/" + filename, img)
    def end(self):
        for a in self.__actions:
            a.end()