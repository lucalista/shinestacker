import numpy as np
import cv2
from termcolor import colored
from focus_stack.exceptions import ImageLoadError
from focus_stack.utils import read_img, get_img_metadata, validate_image


class PyramidSequentialStack:
    def __init__(self, min_size=32, kernel_size=5, gen_kernel=0.4):
        self.min_size = min_size
        self.kernel_size = kernel_size
        self.pad_amount = (kernel_size - 1) // 2
        kernel = np.array([0.25 - gen_kernel / 2.0, 0.25, gen_kernel, 0.25, 0.25 - gen_kernel / 2.0])
        self.gen_kernel = np.outer(kernel, kernel)

    def messenger(self, messenger):
        self.messenger = messenger

    def print_message(self, msg):
        self.messenger.sub_message_r(colored(msg, "light_blue"))

    def convolve(self, image):
        return cv2.filter2D(image, -1, self.gen_kernel, borderType=cv2.BORDER_REFLECT101)

    def reduce_layer(self, layer):
        if len(layer.shape) == 2:
            return self.convolve(layer)[::2, ::2]
        ch_layer = self.reduce_layer(layer[:, :, 0])
        next_layer = np.zeros(list(ch_layer.shape) + [layer.shape[2]], dtype=layer.dtype)
        next_layer[:, :, 0] = ch_layer
        for channel in range(1, layer.shape[2]):
            next_layer[:, :, channel] = self.reduce_layer(layer[:, :, channel])
        return next_layer

    def expand_layer(self, layer):
        if len(layer.shape) == 2:
            expand = np.zeros((2 * layer.shape[0], 2 * layer.shape[1]), dtype=np.float64)
            expand[::2, ::2] = layer
            return 4. * self.convolve(expand)
        ch_layer = self.expand_layer(layer[:, :, 0])
        next_layer = np.zeros(list(ch_layer.shape) + [layer.shape[2]], dtype=layer.dtype)
        next_layer[:, :, 0] = ch_layer
        for channel in range(1, layer.shape[2]):
            next_layer[:, :, channel] = self.expand_layer(layer[:, :, channel])
        return next_layer

    def compute_pyramids(self, image, levels):
        gaussian = [image.astype(np.float64)]
        for _ in range(levels):
            reduced = self.reduce_layer(gaussian[-1])
            if min(reduced.shape[:2]) < 2:
                break
            gaussian.append(reduced)
        laplacian = [gaussian[-1]]
        for level in range(len(gaussian) - 1, 0, -1):
            expanded = self.expand_layer(gaussian[level])
            target_shape = gaussian[level - 1].shape
            if expanded.shape != target_shape:
                expanded = expanded[:target_shape[0], :target_shape[1]]
            laplacian.append(gaussian[level - 1] - expanded)
        return laplacian[::-1]

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
        img = pyramid[0]  # Parte dal livello più piccolo
        for layer in pyramid[1:]:  # Espande progressivamente
            expanded = self.expand_layer(img)
            if expanded.shape != layer.shape:
                expanded = expanded[:layer.shape[0], :layer.shape[1]]
            img = expanded + layer
        return np.clip(np.abs(img), 0, self.n_values - 1)

    def calculate_entropy(self, gray_img):
        hist = cv2.calcHist([gray_img.astype(np.uint8)], [0], None, [256], [0, 256])
        hist = hist / hist.sum()
        hist[hist == 0] = 1e-10
        entropy = -np.sum(hist * np.log(hist))
        return np.full(gray_img.shape, entropy)  # Semplificato per l'esempio

    def calculate_deviation(self, gray_img):
        mean = cv2.blur(gray_img, (self.kernel_size, self.kernel_size))
        sq_diff = (gray_img - mean)**2
        return cv2.blur(sq_diff, (self.kernel_size, self.kernel_size))

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
        self.dtype = images[0].dtype
        self.n_values = 256 if self.dtype == np.uint8 else 65536
        levels = max(1, int(np.log2(min(metadata[0][:2]) / self.min_size)))
        pyramids = [self.compute_pyramids(img, levels) for img in images]
        fused_pyramid = []
        base_levels = [p[-1] for p in pyramids]
        fused_pyramid.append(self.fuse_base(base_levels))
        for level in range(levels - 1, -1, -1):
            current_levels = [p[level] for p in pyramids]
            fused_pyramid.append(self.fuse_laplacian(current_levels))
        return self.collapse_pyramid(fused_pyramid).astype(self.dtype)
