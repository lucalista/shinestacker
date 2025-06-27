import numpy as np
import cv2
from termcolor import colored
from config.constants import constants
from focus_stack.utils import read_img, get_img_metadata, validate_image, img_bw
from focus_stack.exceptions import ImageLoadError, InvalidOptionError


class DepthMapStack:
    def __init__(self, map_type=constants.DEFAULT_DM_MAP, energy=constants.DEFAULT_DM_ENERGY,
                 kernel_size=constants.DEFAULT_DM_KERNEL_SIZE, blur_size=constants.DEFAULT_DM_BLUR_SIZE,
                 smooth_size=constants.DEFAULT_DM_SMOOTH_SIZE, temperature=constants.DEFAULT_DM_TEMPERATURE,
                 levels=constants.DEFAULT_DM_LEVELS, float_type=constants.DEFAULT_DM_FLOAT):
        self.map_type = map_type
        self.energy = energy
        self.kernel_size = kernel_size
        self.blur_size = blur_size
        self.smooth_size = smooth_size
        self.temperature = temperature
        self.levels = levels
        if float_type == constants.FLOAT_32:
            self.float_type = np.float32
        elif float_type == constants.FLOAT_64:
            self.float_type = np.float64
        else:
            raise InvalidOptionError("float_type", float_type, details=" valid values are FLOAT_32 and FLOAT_64")

    def name(self):
        return "depth map"

    def print_message(self, msg):
        self.process.sub_message_r(colored(msg, "light_blue"))

    def _get_sobel_map(self, images):
        energies = np.zeros(images.shape, dtype=np.float32)
        for i in range(images.shape[0]):
            img = images[i]
            energies[i] = np.abs(cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)) + np.abs(cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3))
        return energies

    def _get_laplacian_map(self, images):
        laplacian = np.zeros(images.shape, dtype=np.float32)
        for i in range(images.shape[0]):
            blurred = cv2.GaussianBlur(images[i], (self.blur_size, self.blur_size), 0)
            laplacian[i] = np.abs(cv2.Laplacian(blurred, cv2.CV_64F, ksize=self.kernel_size))
        return laplacian

    def _smooth_energy(self, energy_map):
        if self.smooth_size <= 0:
            return energy_map
        smoothed = np.zeros(energy_map.shape, dtype=energy_map.dtype)
        for i in range(energy_map.shape[0]):
            smoothed[i] = cv2.bilateralFilter(energy_map[i], self.smooth_size, 25, 25)
        return smoothed

    def _get_focus_map(self, energies):
        if self.map_type == 'average':
            sum_energies = np.sum(energies, axis=0)
            return np.divide(energies, sum_energies, where=sum_energies != 0)
        else:
            max_energy = np.max(energies, axis=0)
            relative = np.exp((energies - max_energy) / self.temperature)
            return relative / np.sum(relative, axis=0)

    def _pyramid_blend(self, images, weights):
        blended = None
        for i in range(images.shape[0]):
            img = images[i].astype(np.float32)
            weight = weights[i]
            gp_img = [img]
            gp_weight = [weight]
            for _ in range(self.levels - 1):
                gp_img.append(cv2.pyrDown(gp_img[-1]))
                gp_weight.append(cv2.pyrDown(gp_weight[-1]))
            lp_img = [gp_img[-1]]
            for j in range(self.levels - 1, 0, -1):
                size = (gp_img[j - 1].shape[1], gp_img[j - 1].shape[0])
                expanded = cv2.pyrUp(gp_img[j], dstsize=size)
                lp_img.append(gp_img[j - 1] - expanded)
            current_blend = []
            for j in range(self.levels):
                w = gp_weight[self.levels - 1 - j][..., np.newaxis]
                current_blend.append(lp_img[j] * w)
            if blended is None:
                blended = current_blend
            else:
                for j in range(self.levels):
                    blended[j] += current_blend[j]
        result = blended[0]
        for j in range(1, self.levels):
            size = (blended[j].shape[1], blended[j].shape[0])
            result = cv2.pyrUp(result, dstsize=size) + blended[j]

        return result

    def focus_stack(self, filenames):
        images = []
        metadata = None
        for img_path in filenames:
            self.print_message(': reading file {}'.format(img_path.split('/')[-1]))
            img = read_img(img_path)
            if img is None:
                raise ImageLoadError(img_path)
            if metadata is None:
                metadata = get_img_metadata(img)
            else:
                validate_image(img, *metadata)
            images.append(img)
        images = np.array(images)
        dtype = images[0].dtype
        if dtype == np.uint8:
            n_values = 255
        elif dtype == np.uint16:
            n_values = 65535
        else:
            Exception("Invalid image type: " + dtype.str)
        gray = np.zeros(images.shape[:-1], dtype=images.dtype)
        for i in range(images.shape[0]):
            gray[i] = img_bw(images[i])
        self.print_message(': compute energy map')
        if self.energy == 'sobel':
            energy = self._get_sobel_map(gray)
        else:
            energy = self._get_laplacian_map(gray)
            self.print_message(': smooth energy map')
        energy = self._smooth_energy(energy)
        self.print_message(': get weights')
        weights = self._get_focus_map(energy)
        self.print_message(': blend pyramid')
        result = self._pyramid_blend(images, weights)
        return np.clip(np.absolute(result), 0, n_values).astype(dtype)
