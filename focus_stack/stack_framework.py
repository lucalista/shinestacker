from .framework import  Job, ActionList, Timer
from .helper import chunks
from .align import img_align
from .balance import lumi_balance, img_lumi_balance, img_lumi_balance_rgb, img_lumi_balance_hsv
from .stack import focus_stack
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
    def __init__(self, wdir, name, input_path, output_path='', ref_idx=-1, step_align=True):
        FrameDirectory.__init__(self, wdir, name, input_path, output_path)
        ActionList.__init__(self, name)
        self.ref_idx = ref_idx
        self.step_align = step_align
        assert  os.path.exists(wdir + input_path), 'path does not exist: ' + wdir + input_path
    def begin(self):
        self.set_filelist()
        self.counts = len(self.filenames)
        if self.ref_idx == -1: self.ref_idx = len(self.filenames) // 2
    def run_step(self):
        cprint("action: {} ".format(self.filenames[self.count - 1]), "blue", end='\r')
        if self.count == 1:
            self.__idx = self.ref_idx if self.step_align else 0
            self.__ref_idx = self.ref_idx
            self.__idx_step = +1
        self.run_frame(self.__idx, self.__ref_idx)
        ll = len(self.filenames)
        if(self.__idx < ll):
            if self.step_align: self.__ref_idx = self.__idx
            self.__idx += self.__idx_step
        if(self.__idx == ll):
            self.__idx = self.ref_idx - 1
            if self.step_align: self.__ref_idx = self.ref_idx
            self.__idx_step = -1
            
class AlignLayers(FramesRefActions):
    ALIGN_HOMOGRAPHY = "homography"
    ALIGN_RIGID = "rigid"
    def __init__(self, wdir, name, input_path, output_path='', ref_idx=-1, step_align=True, detector_method='SIFT', descriptor_method='SIFT', match_method='KNN', flann_idx_kdtree=0, match_threshold=0.7, method=ALIGN_HOMOGRAPHY, plot=False):
        FramesRefActions.__init__(self, wdir, name, input_path, output_path, ref_idx, step_align)
        self.detector_method = detector_method
        self.descriptor_method = descriptor_method
        self.match_method = match_method
        self.flann_idx_kdtree = flann_idx_kdtree
        self.match_threshold = match_threshold
        self.method = method
        self.plot = plot
    def run_frame(self, idx, ref_idx):
        print("frame: {}, index: {}, reference: {}, align file: {}                    ".format(self.count, idx, ref_idx, self.filenames[idx]), end='\r')
        ref_dir = self.output_dir if self.step_align else self.input_dir
        img_align(self.filenames[ref_idx], self.filenames[idx], ref_dir, self.input_dir, self.output_dir, self.detector_method, self.descriptor_method, self.match_method, self.flann_idx_kdtree, self.match_threshold, self.method, self.plot, verbose=False)
        
class BalanceLayers(FramesRefActions):
    BALANCE_LUMI = "lumi"
    BALANCE_RGB = "rgb"
    BALANCE_SV = "sv"
    BALANCE_LS = "ls"
    def __init__(self, wdir, name, input_path, output_path='', ref_idx=-1, method=BALANCE_LUMI, mask_radius=-1, i_min=0, i_max=255, plot=False):
        FramesRefActions.__init__(self, wdir, name, input_path, output_path, ref_idx, step_align=False)
        self.method = method
        self.mask_radius = mask_radius
        self.i_min = i_min
        self.i_max = i_max
        self.plot = plot
    def run_frame(self, idx, ref_idx):
        print("frame: {}, index: {}, reference: {}, balance file: {}                    ".format(self.count, idx, ref_idx, self.filenames[idx]), end='\r')
        if self.method ==BalanceLayers.BALANCE_LUMI:
            img_lumi_balance(self.filenames[ref_idx], self.filenames[idx], self.input_dir, self.output_dir, self.mask_radius, self.i_min, self.i_max, self.plot, verbose=False)
        elif self.method == BalanceLayers.BALANCE_RGB:
            img_lumi_balance_rgb(self.filenames[ref_idx], self.filenames[idx], self.input_dir, self.output_dir, self.mask_radius, self.i_min, self.i_max, self.plot, verbose=False)
        elif self.method == BalanceLayers.BALANCE_SV:
            img_lumi_balance_hsv(self.filenames[ref_idx], self.filenames[idx], self.input_dir, self.output_dir, self.mask_radius, self.i_min, self.i_max, self.plot, verbose=False)
        else: 
            raise Exceltion("invalid method: " + self.method)
            
class FocusStackBase:
    ENERGY_SOBEL = "sobel"
    ENERGY_LAPLACIAN = "laplacian"
    METHOD_PYRAMID = "pyramid"
    METHOD_MAX = "max"
    METHOD_AVERAGE = "average"
    def __init__(self, exif_dir='', postfix='', denoise=0, method=METHOD_PYRAMID, energy=ENERGY_LAPLACIAN, pyramid_min_size=32, kernel_size=5, blur_size=5, smooth_size=32):
        self.exif_dir = exif_dir
        self.postfix = postfix
        self.denoise = denoise
        self.method = method
        self.energy = energy
        self.pyramid_min_size = pyramid_min_size
        self.kernel_size = kernel_size
        self.blur_size = blur_size
        self.smooth_size = smooth_size
        
class FocusStackBunch(FrameDirectory, ActionList, FocusStackBase):
    ENERGY_SOBEL = "sobel"
    ENERGY_LAPLACIAN = "laplacian"
    METHOD_PYRAMID = "pyramid"
    METHOD_MAX = "max"
    METHOD_AVERAGE = "average"
    def __init__(self, wdir, name, input_path, output_path='', exif_dir='', frames=10, overlap=0, postfix='', denoise=0, method=METHOD_PYRAMID, energy=ENERGY_LAPLACIAN, pyramid_min_size=32, kernel_size=5, blur_size=5, smooth_size=32):
        FrameDirectory.__init__(self, wdir, name, input_path, output_path)
        ActionList.__init__(self, name)
        FocusStackBase.__init__(self, exif_dir, postfix, denoise, method, energy, pyramid_min_size, kernel_size, blur_size, smooth_size)
        if overlap >= frames: raise Exception("Overlap must be smaller than batch size")
        self.frames = frames
        self.overlap = overlap
    def begin(self):
        fnames = self.folder_filelist(self.input_dir)
        self.__chunks = [fnames[x:x + self.frames] for x in range(0, len(fnames), self.frames - self.overlap)]
        self.counts = len(self.__chunks)
    def run_step(self):
        print("bunch: {}                    ".format(self.count), end='\r')
        focus_stack(self.__chunks[self.count - 1], self.input_dir, self.output_dir, self.working_directory + self.exif_dir, self.postfix, self.denoise, choice=self.method, energy=self.energy, pyramid_min_size=self.pyramid_min_size, kernel_size=self.kernel_size, blur_size=self.blur_size, smooth_size=self.smooth_size, verbose=False)
        
class FocusStack(FrameDirectory, Timer):
    ENERGY_SOBEL = "sobel"
    ENERGY_LAPLACIAN = "laplacian"
    METHOD_PYRAMID = "pyramid"
    METHOD_MAX = "max"
    METHOD_AVERAGE = "average"
    def __init__(self, wdir, name, input_path, output_path='', exif_dir='', postfix='', denoise=0, method=METHOD_PYRAMID, energy=ENERGY_LAPLACIAN, pyramid_min_size=32, kernel_size=5, blur_size=5, smooth_size=32):
        self.name = name
        FrameDirectory.__init__(self, wdir, name, input_path, output_path)
        Timer.__init__(self, name)
        FocusStackBase.__init__(self, exif_dir, postfix, denoise, method, energy, pyramid_min_size, kernel_size, blur_size, smooth_size)
    def run_core(self):
        cprint("running " + self.name, "blue", attrs=["bold"])
        self.set_filelist()
        focus_stack(self.filenames, self.input_dir, self.output_dir, self.working_directory + self.exif_dir, self.postfix, self.denoise, choice=self.method, energy=self.energy, pyramid_min_size=self.pyramid_min_size, kernel_size=self.kernel_size, blur_size=self.blur_size, smooth_size=self.smooth_size, verbose=False)
        