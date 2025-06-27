import numpy as np
import cv2
from termcolor import colored
from config.constants import constants
from focus_stack.exceptions import ImageLoadError, InvalidOptionError
from focus_stack.utils import read_img, get_img_metadata, validate_image
from focus_stack.exceptions import RunStopException


class PyramidBase:
    def __init__(self, min_size=constants.DEFAULT_PY_MIN_SIZE, kernel_size=constants.DEFAULT_PY_KERNEL_SIZE,
                 gen_kernel=constants.DEFAULT_PY_GEN_KERNEL, float_type=constants.DEFAULT_PY_FLOAT):
        self.min_size = min_size
        self.kernel_size = kernel_size
        self.pad_amount = (kernel_size - 1) // 2
        kernel = np.array([0.25 - gen_kernel / 2.0, 0.25, gen_kernel, 0.25, 0.25 - gen_kernel / 2.0])
        self.gen_kernel = np.outer(kernel, kernel)
        if float_type == constants.FLOAT_32:
            self.float_type = np.float32
        elif float_type == constants.FLOAT_64:
            self.float_type = np.float64
        else:
            raise InvalidOptionError("float_type", float_type, details=" valid values are FLOAT_32 and FLOAT_64")

    def print_message(self, msg):
        self.process.sub_message_r(colored(msg, "light_blue"))

    def convolve(self, image):
        return cv2.filter2D(image, -1, self.gen_kernel, borderType=cv2.BORDER_REFLECT101)

    def reduce_layer(self, layer):
        if len(layer.shape) == 2:
            return self.convolve(layer)[::2, ::2]
        reduced_channels = [self.reduce_layer(layer[:, :, channel]) for channel in range(layer.shape[2])]
        return np.stack(reduced_channels, axis=-1)

    def expand_layer(self, layer):
        if len(layer.shape) == 2:
            expand = np.empty((2 * layer.shape[0], 2 * layer.shape[1]), dtype=layer.dtype)
            expand[::2, ::2] = layer
            expand[1::2, :] = 0
            expand[:, 1::2] = 0
            return 4. * self.convolve(expand)
        ch_layer = self.expand_layer(layer[:, :, 0])
        next_layer = np.zeros(list(ch_layer.shape) + [layer.shape[2]], dtype=layer.dtype)
        next_layer[:, :, 0] = ch_layer
        for channel in range(1, layer.shape[2]):
            next_layer[:, :, channel] = self.expand_layer(layer[:, :, channel])
        return next_layer


class PyramidStack(PyramidBase):
    def __init__(self, min_size=constants.DEFAULT_PY_MIN_SIZE, kernel_size=constants.DEFAULT_PY_KERNEL_SIZE,
                 gen_kernel=constants.DEFAULT_PY_GEN_KERNEL, float_type=constants.DEFAULT_PY_FLOAT):
        super().__init__(min_size, kernel_size, gen_kernel, float_type)

    def name(self):
        return "pyramid"

    def compute_pyramids(self, image, levels):
        self.print_message(': beginning gaussian pyramids')
        gaussian = [image.astype(self.float_type)]
        for _ in range(levels):
            self.print_message(f': gaussian pyramids, level: {_}/{levels}')
            reduced = self.reduce_layer(gaussian[-1])
            if min(reduced.shape[:2]) < 4:
                break
            gaussian.append(reduced)
        laplacian = [gaussian[-1]]
        for level in range(len(gaussian) - 1, 0, -1):
            expanded = self.expand_layer(gaussian[level])
            h, w = gaussian[level - 1].shape[:2]
            expanded = expanded[:h, :w]
            laplacian.append(gaussian[level - 1] - expanded)
        self.print_message(': gaussian pyramids completed')
        return laplacian[::-1]

    def calculate_entropy(self, image):
        hist = cv2.calcHist([image.astype(self.dtype)], [0], None, [self.n_values], [0, self.n_values])
        hist = np.maximum(hist / hist.sum(), 1e-10)
        entropy = -np.sum(hist * np.log(hist))
        return np.full(image.shape, entropy)

    def calculate_deviation(self, image):
        mean = cv2.boxFilter(image, -1, (self.kernel_size, self.kernel_size), normalize=True)
        sq_diff = cv2.multiply(image - mean, image - mean)
        variance = cv2.boxFilter(sq_diff, -1, (self.kernel_size, self.kernel_size), normalize=True)
        return variance

    def fuse_base(self, base_imgs):
        gray_imgs = [cv2.cvtColor(img.astype(np.float32), cv2.COLOR_BGR2GRAY) for img in base_imgs]
        entropies = [self.calculate_entropy(gray) for gray in gray_imgs]
        deviations = [self.calculate_deviation(gray) for gray in gray_imgs]
        best_e = np.argmax(entropies, axis=0)
        best_d = np.argmax(deviations, axis=0)
        fused = np.zeros_like(base_imgs[0])
        for i, img in enumerate(base_imgs):
            fused += np.where(best_e[:, :, np.newaxis] == i, img, 0)
            fused += np.where(best_d[:, :, np.newaxis] == i, img, 0)
        return (fused / 2)

    def fuse_laplacian(self, laplacians):
        gray_laps = [cv2.cvtColor(lap.astype(np.float32), cv2.COLOR_BGR2GRAY) for lap in laplacians]
        energies = [self.convolve(np.square(gray_lap)) for gray_lap in gray_laps]
        best = np.argmax(energies, axis=0)
        fused = np.zeros_like(laplacians[0])
        for i, lap in enumerate(laplacians):
            fused += np.where(best[:, :, np.newaxis] == i, lap, 0)
        return fused

    def collapse_pyramid(self, pyramid):
        img = pyramid[0]
        for layer in pyramid[1:]:
            expanded = self.expand_layer(img)
            if expanded.shape != layer.shape:
                expanded = expanded[:layer.shape[0], :layer.shape[1]]
            img = expanded + layer
        return np.clip(np.abs(img), 0, self.n_values - 1)

    def focus_stack(self, filenames):
        metadata = None
        pyramids = []
        base_levels = []
        self.process.callback('step_counts', self.process.id, self.process.name, len(filenames))
        for i, img_path in enumerate(filenames):
            self.print_message(': reading file {}'.format(img_path.split('/')[-1]))
            img = read_img(img_path)
            if img is None:
                raise ImageLoadError(img_path)
            if metadata is None:
                metadata = get_img_metadata(img)
                shape, self.dtype = metadata
                self.n_values = 256 if self.dtype == np.uint8 else 65536
            else:
                validate_image(img, *metadata)
            levels = max(1, int(np.log2(min(metadata[0][:2]) / self.min_size)))
            pyramid = self.compute_pyramids(img, levels)
            pyramids.append(pyramid)
            base_levels.append(pyramid[-1])
            self.process.callback('after_step', self.process.id, self.process.name, i)
            if self.process.callback('check_running', self.process.id, self.process.name) is False:
                raise RunStopException(self.name)
        fused_pyramid = [self.fuse_base(base_levels)]
        for level in range(levels - 1, -1, -1):
            current_levels = [p[level] for p in pyramids]
            fused_pyramid.append(self.fuse_laplacian(current_levels))
        return self.collapse_pyramid(fused_pyramid).astype(self.dtype)
