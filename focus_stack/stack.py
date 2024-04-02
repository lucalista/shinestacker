import numpy as np
import cv2
from .pyramid import get_pyramid_fusion
from focus_stack.stack_framework import *
from PIL import Image

EXTENSIONS = set(["jpeg", "jpg", "png", "tif", "tiff"])

def convert_to_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def blend(images, focus_map):
    return np.sum(images.astype(np.float64) * focus_map[:, :, :, np.newaxis], axis=0).astype(images.dtype)

def get_sobel_map(images):
    energies = np.zeros(images.shape, dtype=np.float32)
    for index in range(images.shape[0]):
        image = images[index]
        energies[index] = np.abs(cv2.Sobel(image, cv2.CV_64F, 1, 0)) + np.abs(cv2.Sobel(image, cv2.CV_64F, 0, 1))
    return energies

def get_laplacian_map(images, kernel_size, blur_size):
    laplacian = np.zeros(images.shape, dtype=np.float32)
    for index in range(images.shape[0]):
        gaussian = cv2.GaussianBlur(images[index], (blur_size, blur_size), 0)
        laplacian[index] = np.abs(cv2.Laplacian(gaussian, cv2.CV_64F, ksize = kernel_size))
    return laplacian

def smooth_energy_map(energies, smooth_size):
    smoothed = np.zeros(energies.shape, dtype=energies.dtype)
    if (smooth_size > 0):
        for index in range(energies.shape[0]):
            smoothed[index] = cv2.bilateralFilter(energies[index], smooth_size, 25, 25)
    return smoothed

def get_focus_map(energies, choice):
    if (choice == CHOICE_AVERAGE):
        tile_shape = np.array(energies.shape)
        tile_shape[1:] = 1

        sum_energies = np.tile(np.sum(energies, axis=0), tile_shape)
        return np.divide(energies, sum_energies, where=sum_energies!=0)
    focus_map = np.zeros(energies.shape, dtype=np.float64)
    best_layer = np.argmax(energies, axis=0)
    for index in range(energies.shape[0]):
        focus_map[index] = best_layer == index
    return focus_map

class DepthMapStack:
    ENERGY_SOBEL = "sobel"
    ENERGY_LAPLACIAN = "laplacian"
    MAP_MAX = "max"
    MAP_AVERAGE = "average"
    def __init__(self, map_type=MAP_MAX, energy=ENERGY_LAPLACIAN, kernel_size=5, blur_size=5, smooth_size=32):
        self.choice = choice
        self.energy = energy
        self.kernel_size = kernel_size
        self.blur_size = blur_size
        self.smooth_size = smooth_size
    def focus_stack(self, images):
        gray_images = np.zeros(images.shape[:-1], dtype=np.uint8)
        for index in range(images.shape[0]):
            gray_images[index] = convert_to_grayscale(images[index])
        if self.energy == DepthMapStack.ENERGY_SOBEL:
            energy_map = get_sobel_map(gray_images)
        elif self.energy == DepthMapStack.ENERGY_LAPLACIAN:
            energy_map = get_laplacian_map(gray_images, kernel_size, blur_size)
        else:
            assert(False), 'invalid energy parameter: ' + self.energy
        if smooth_size > 0:
            energy_map = smooth_energy_map(energy_map, smooth_size)
        focus_map = get_focus_map(energy_map, self.map_type)
        stacked_image = blend(images, focus_map)
        return cv2.convertScaleAbs(stacked_image)

class PyramidStack:
    def __init__(self, pyramid_min_size=32, kernel_size=5):
        self.pyramid_min_size = pyramid_min_size
        self.kernel_size = kernel_size
    def focus_stack(self, images):
        stacked_image = get_pyramid_fusion(images, self.pyramid_min_size, self.kernel_size, verbose=False)
        return cv2.convertScaleAbs(stacked_image)  
    
class FocusStackBase:
    def __init__(self, wdir, stack_algo, exif_dir='', postfix='', denoise=0):
        self.stack_algo = stack_algo
        self.exif_dir = '' if exif_dir=='' else wdir + "/" + exif_dir
        self.postfix = postfix
        self.denoise = denoise
    def focus_stack(self, filenames):
        img_files = sorted([os.path.join(self.input_dir, name) for name in filenames])
        img_files = [cv2.imread(name) for name in img_files]
        if any([img is None for img in img_files]):
            raise RuntimeError("failed to load one or more image files.")
        img_files = np.array(img_files, dtype=img_files[0].dtype)
        stacked_img = self.stack_algo.focus_stack(img_files)
        in_filename = filenames[0].split(".")
        out_filename = self.output_dir + "/" + in_filename[0] + self.postfix + '.' + '.'.join(in_filename[1:])
        if self.denoise > 0:
            s = cv2.fastNlMeansDenoisingColored(stacked_img, None, self.denoise, self.denoise, 7, 21)
        cv2.imwrite(out_filename, s, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
        if self.exif_dir != '':
            dirpath, _, fnames = next(os.walk(self.exif_dir))
            fnames = [name for name in fnames if os.path.splitext(name)[-1][1:].lower() in EXTENSIONS]
            exif_filename = self.exif_dir + '/' + fnames[0]
            if(not os.path.isfile(exif_filename)): raise Exception("File does not exist: " + exif_filename)
            image = Image.open(exif_filename)
            exif = image.info['exif']
            image_new = Image.open(out_filename)
            image_new.save(out_filename, 'JPEG', exif=exif, quality=100)
            
class FocusStackBunch(FrameDirectory, ActionList, FocusStackBase):
    def __init__(self, wdir, name, stack_algo, input_path, output_path='', exif_dir='', frames=10, overlap=0, postfix='', denoise=0):
        FrameDirectory.__init__(self, wdir, name, input_path, output_path)
        ActionList.__init__(self, name)
        FocusStackBase.__init__(self, wdir, stack_algo, exif_dir, postfix, denoise)
        if overlap >= frames: raise Exception("Overlap must be smaller than batch size")
        self.frames = frames
        self.overlap = overlap
    def begin(self):
        fnames = self.folder_filelist(self.input_dir)
        self.__chunks = [fnames[x:x + self.frames] for x in range(0, len(fnames), self.frames - self.overlap)]
        self.counts = len(self.__chunks)
    def run_step(self):
        print("bunch: {}                    ".format(self.count), end='\r')
        self.focus_stack(self.__chunks[self.count - 1])
        
class FocusStack(FrameDirectory, Timer, FocusStackBase):
    def __init__(self, wdir, name, stack_algo, input_path, output_path='', exif_dir='', postfix='', denoise=0):
        self.name = name
        FrameDirectory.__init__(self, wdir, name, input_path, output_path)
        Timer.__init__(self, name)
        FocusStackBase.__init__(self, wdir, stack_algo, exif_dir, postfix, denoise)
    def run_core(self):
        cprint("running " + self.name, "blue", attrs=["bold"])
        self.set_filelist()
        self.focus_stack(self.filenames)
    