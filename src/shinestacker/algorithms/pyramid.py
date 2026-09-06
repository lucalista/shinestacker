# pylint: disable=C0114, C0115, C0116, E1101, R0913, R0917, R0902
import os
import traceback
import logging
import numpy as np
import cv2
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. core.colors import color_str
from .utils import read_and_validate_img
from .base_stack_algo import BaseStackAlgo


class PyramidBase(BaseStackAlgo):
    def __init__(self, name, **kwargs):
        default_params = DEFAULTS['pyramid_params']
        float_type = kwargs.get('float_type', default_params['float_type'])
        super().__init__(name, 1, float_type)
        self.min_size = kwargs.get('min_size', default_params['min_size'])
        kernel_size = kwargs.get('kernel_size', default_params['kernel_size'])
        self.pad_amount = (kernel_size - 1) // 2
        gen_kernel = kwargs.get('gen_kernel', default_params['gen_kernel'])
        kernel = np.array([0.25 - gen_kernel / 2.0, 0.25,
                           gen_kernel, 0.25, 0.25 - gen_kernel / 2.0])
        self.gen_kernel_1d = kernel
        self.dtype = None
        self.num_pixel_values = None
        self.max_pixel_value = None
        self.n_levels = 0
        self.n_frames = 0

    def init(self, filenames):
        super().init(filenames)
        self.n_levels = int(np.log2(min(self.shape) / self.min_size))

    def total_steps(self, n_frames):
        self.n_frames = n_frames
        return super().total_steps(n_frames) + self.n_levels

    def convolve(self, image):
        return cv2.sepFilter2D(image, -1, self.gen_kernel_1d, self.gen_kernel_1d,
                               borderType=cv2.BORDER_REFLECT101)

    def reduce_layer(self, layer):
        if len(layer.shape) == 2:
            return self.convolve(layer)[::2, ::2]
        convolved = self.convolve(layer)
        return convolved[::2, ::2, :]

    def expand_layer(self, layer):
        if len(layer.shape) == 2:
            h, w = layer.shape
            expand = np.zeros((2 * h, 2 * w), dtype=layer.dtype)
            expand[::2, ::2] = layer
            return 4. * self.convolve(expand)
        h, w, c = layer.shape
        expand = np.zeros((2 * h, 2 * w, c), dtype=layer.dtype)
        expand[::2, ::2, :] = layer
        return 4. * self.convolve(expand)

    def collapse(self, pyramid):
        self.print_message(': collapsing pyramid')
        img = pyramid[-1]
        for layer in pyramid[-2::-1]:
            expanded = self.expand_layer(img)
            if expanded.shape != layer.shape:
                expanded = expanded[:layer.shape[0], :layer.shape[1]]
            img = expanded + layer
        return np.clip(np.abs(img), 0, self.max_pixel_value)

    def entropy(self, image):
        levels, counts = np.unique(image.astype(self.dtype), return_counts=True)
        probabilities = np.zeros((self.num_pixel_values), dtype=self.float_type)
        probabilities[levels] = counts.astype(self.float_type) / counts.sum()
        padded_image = cv2.copyMakeBorder(image, self.pad_amount, self.pad_amount, self.pad_amount,
                                          self.pad_amount, cv2.BORDER_REFLECT101)
        return np.fromfunction(np.vectorize(lambda row, column: self.area_entropy(
            self.get_pad(padded_image, row, column), probabilities)), image.shape[:2], dtype=int)

    def area_entropy(self, area, probabilities):
        levels = area.flatten()
        return self.float_type(-1. * (levels * np.log(probabilities[levels])).sum())

    def get_pad(self, padded_image, row, column):
        return padded_image[row + self.pad_amount +
                            self.offset[:, np.newaxis], column +
                            self.pad_amount + self.offset]

    def area_deviation(self, area):
        return np.square(area - np.average(area).astype(self.float_type)).sum() / area.size

    def deviation(self, image):
        padded_image = cv2.copyMakeBorder(image, self.pad_amount, self.pad_amount, self.pad_amount,
                                          self.pad_amount, cv2.BORDER_REFLECT101)
        return np.fromfunction(
            np.vectorize(lambda row, column:
                         self.area_deviation(self.get_pad(padded_image, row, column))),
            image.shape[:2], dtype=int)

    def get_fused_base(self, laplacians):
        images = np.stack(laplacians, axis=0)
        layers = images.shape[0]
        entropies = np.zeros(images.shape[:3], dtype=self.float_type)
        deviations = np.copy(entropies)
        gray_images = np.array([cv2.cvtColor(
            images[layer][..., :3] if self.float_type == np.float32 else
            images[layer][..., :3].astype(np.float32),
            cv2.COLOR_BGR2GRAY).astype(self.dtype) for layer in range(layers)])
        entropies = np.array([self.entropy(img) for img in gray_images])
        deviations = np.array([self.deviation(img) for img in gray_images])
        best_e = np.argmax(entropies, axis=0)
        best_d = np.argmax(deviations, axis=0)
        fused = np.zeros(images.shape[1:], dtype=self.float_type)
        for layer in range(layers):
            img = images[layer]
            fused += np.where(best_e[:, :, np.newaxis] == layer, img, 0)
            fused += np.where(best_d[:, :, np.newaxis] == layer, img, 0)
        return (fused / 2).astype(images.dtype)

    def single_image_laplacian(self, img, levels):
        pyramid = [img.astype(self.float_type)]
        for _ in range(levels):
            next_layer = self.reduce_layer(pyramid[-1])
            if min(next_layer.shape[:2]) < 4:
                break
            pyramid.append(next_layer)
        laplacian = [pyramid[-1]]
        for level in range(len(pyramid) - 1, 0, -1):
            expanded = self.expand_layer(pyramid[level])
            pyr = pyramid[level - 1]
            h, w = pyr.shape[:2]
            expanded = expanded[:h, :w]
            laplacian.append(pyr - expanded)
        return laplacian

    def premultiply_alpha(self, img):
        if self.alpha_mode and img.ndim == 3 and img.shape[2] == 4:
            f = img.astype(self.float_type)
            a_norm = f[..., 3:4] / self.max_pixel_value
            color_pm = f[..., :3] * a_norm
            return np.concatenate([color_pm, f[..., 3:4]], axis=2)
        return img

    def unpremultiply_alpha(self, img):
        if not getattr(self, 'alpha_mode', False):
            return img
        f = img.astype(self.float_type)
        a = np.clip(f[..., 3:4], 0, self.max_pixel_value)
        a_norm = a / self.max_pixel_value
        floor = 2.0 / 255.0
        color = np.where(a_norm > floor, f[..., :3] / np.maximum(a_norm, floor), 0.0)
        color = np.clip(color, 0, self.max_pixel_value)
        return np.concatenate([color, a], axis=2)

    def fuse_laplacian(self, laplacians_list):
        laplacians = np.stack(laplacians_list, axis=0)
        n_layers, h, w, _ = laplacians.shape
        if laplacians.dtype != np.float32:
            laplacians_32 = laplacians.astype(np.float32)
        else:
            laplacians_32 = laplacians
        energies = np.empty((n_layers, h, w), dtype=np.float32)
        for i in range(n_layers):
            gray = cv2.cvtColor(laplacians_32[i][..., :3], cv2.COLOR_BGR2GRAY)
            energies[i] = self.convolve(gray * gray)
        best = np.argmax(energies, axis=0)
        rows = np.arange(h)[:, None]
        cols = np.arange(w)
        fused = laplacians[best, rows, cols, :]
        return fused


class PyramidStack(PyramidBase):
    supports_alpha = True

    def __init__(self, **kwargs):
        super().__init__("pyramid", **kwargs)
        self.offset = np.arange(-self.pad_amount, self.pad_amount + 1)

    def process_single_image(self, img, levels):
        laplacian = self.single_image_laplacian(img, levels)
        return laplacian[::-1]

    def fuse_pyramids(self, all_laplacians):
        fused = [self.get_fused_base([p[-1] for p in all_laplacians])]
        count = 0
        n_layers = len(all_laplacians[0]) - 2
        self.process.callback(constants.CALLBACKS_SET_TOTAL_ACTIONS,
                              self.process.output_path, self.output_filename, n_layers + 1)
        action_count = 0
        for layer in range(n_layers, -1, -1):
            self.print_message(f': fusing pyramids, layer: {layer + 1}')
            fused.append(self.fuse_laplacian([p[layer] for p in all_laplacians]))
            count += 1
            self.after_step(self._steps_per_frame * self.n_frames + count)
            self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                  self.process.output_path, self.output_filename, action_count)
            action_count += 1
            self.check_running()
        self.print_message(': pyramids fusion completed')
        return fused[::-1]

    def focus_stack(self):
        all_laplacians = []
        for i, img_path in enumerate(self.filenames):
            self.print_message(
                f": reading and validating {self.image_str(i)}")
            filename = os.path.basename(img_path)
            self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                  self.process.input_path, filename, 200)
            img = read_and_validate_img(img_path, self.shape, self.dtype)
            img = self.premultiply_alpha(img)
            self.check_running()
            self.print_message(
                f": processing {self.image_str(i)}")
            try:
                all_laplacians.append(self.process_single_image(img, self.n_levels))
            except Exception as e:
                err_msg = f"failed to process {self.image_str(i)}: {str(e)}"
                self.process.sub_message_r(color_str(f": {err_msg}", constants.LOG_COLOR_ALERT),
                                           level=logging.ERROR)
                traceback.print_exc()
                raise RuntimeError(err_msg) from e
            self.after_step(i + 1)
            self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                  self.process.input_path, filename, 201)
            self.check_running()
        stacked_image = self.collapse(self.fuse_pyramids(all_laplacians))
        stacked_image = self.unpremultiply_alpha(stacked_image)
        return stacked_image.astype(self.dtype)
