import numpy as np
import cv2
from termcolor import colored
from focus_stack.utils import read_img, get_img_metadata, validate_image
from focus_stack.exceptions import ImageLoadError


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


ENERGY_SOBEL = "sobel"
ENERGY_LAPLACIAN = "laplacian"
MAP_MAX = "max"
MAP_AVERAGE = "average"


class DepthMapStack:
    def __init__(self, map_type=MAP_AVERAGE, energy=ENERGY_LAPLACIAN, kernel_size=5, blur_size=5, smooth_size=32):
        self.map_type = map_type
        self.energy = energy
        self.kernel_size = kernel_size
        self.blur_size = blur_size
        self.smooth_size = smooth_size

    def messenger(self, messenger):
        self.messenger = messenger

    def print_message(self, msg):
        self.messenger.sub_message_r(colored(msg, "light_blue"))

    def get_laplacian_map(self, images):
        laplacian = np.zeros(images.shape, dtype=np.float32)
        for index in range(images.shape[0]):
            gaussian = cv2.GaussianBlur(images[index], (self.blur_size, self.blur_size), 0)
            laplacian[index] = np.abs(cv2.Laplacian(gaussian, cv2.CV_64F, ksize=self.kernel_size))
        return laplacian

    def smooth_energy_map(self, energies):
        smoothed = np.zeros(energies.shape, dtype=energies.dtype)
        if (self.smooth_size > 0):
            for index in range(energies.shape[0]):
                smoothed[index] = cv2.bilateralFilter(energies[index], self.smooth_size, 25, 25)
        return smoothed

    def get_focus_map(self, energies):
        if (self.map_type == MAP_AVERAGE):
            tile_shape = np.array(energies.shape)
            tile_shape[1:] = 1
            sum_energies = np.tile(np.sum(energies, axis=0), tile_shape)
            return np.divide(energies, sum_energies, where=sum_energies != 0)
        else:
            focus_map = np.zeros(energies.shape, dtype=np.float64)
            best_layer = np.argmax(energies, axis=0)
            for index in range(energies.shape[0]):
                focus_map[index] = best_layer == index
            return focus_map

    def focus_stack(self, filenames):
        images = []
        metadata = None
        for img_path in filenames:
            img = read_img(img_path)
            if img is None:
                raise ImageLoadError(img_path)
            if metadata is None:
                metadata = get_img_metadata(img)
            else:
                validate_image(img, *metadata)
            images.append(img)
        dtype = images[0].dtype
        self.images = np.array(images, dtype=dtype)
        t = self.images[0].dtype
        if t == np.uint8:
            n_values = 255
        elif t == np.uint16:
            n_values = 65535
        else:
            Exception("Invalid image type: " + t.str)
        gray_images = np.zeros(self.images.shape[:-1], dtype=t)
        for index in range(self.images.shape[0]):
            gray_images[index] = convert_to_grayscale(self.images[index])
        self.print_message(': compute energy map')
        if self.energy == ENERGY_SOBEL:
            energy_map = get_sobel_map(gray_images)
        elif self.energy == ENERGY_LAPLACIAN:
            energy_map = self.get_laplacian_map(gray_images)
        else:
            assert False, 'invalid energy parameter: ' + self.energy
        if self.smooth_size > 0:
            self.print_message(': smoothing energy map')
            energy_map = self.smooth_energy_map(energy_map)
        self.print_message(': computing focus map')
        focus_map = self.get_focus_map(energy_map)
        self.print_message(': blending images')
        stacked_image = blend(self.images, focus_map)
        return np.clip(np.absolute(stacked_image), 0, n_values).astype(t)
