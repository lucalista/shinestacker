import numpy as np
from scipy import ndimage
import cv2
from termcolor import colored
from scipy.ndimage import generic_filter

class PyramidStack:
    def __init__(self, min_size=32, kernel_size=5, gen_kernel=0.4):
        self.min_size = min_size
        self.kernel_size = kernel_size
        self.pad_amount = int((self.kernel_size - 1)/2)
        self.offset = np.arange(-self.pad_amount, self.pad_amount + 1)
        kernel = np.array([0.25 - gen_kernel/2.0, 0.25, gen_kernel, 0.25, 0.25 - gen_kernel/2.0])
        self.gen_kernel = np.outer(kernel, kernel)
    def messenger(self, messenger):
        self.messenger = messenger
    def print_message(self, msg):
        self.messenger.sub_message(msg, end='\r')
    def convolve(self, image):
        return cv2.filter2D(image, -1, self.gen_kernel, borderType=cv2.BORDER_REFLECT101)
    def reduce_layer(self, layer):
        if len(layer.shape) == 2:
            return self.convolve(layer)[::2, ::2]
        ch_layer = self.reduce_layer(layer[:, :, 0])
        next_layer = np.zeros(list(ch_layer.shape) + [layer.shape[2]], dtype = ch_layer.dtype)
        next_layer[:, :, 0] = ch_layer
        for channel in range(1, layer.shape[2]):
            next_layer[:, :, channel] = self.reduce_layer(layer[:, :, channel])
        return next_layer
    def expand_layer(self, layer):
        if len(layer.shape) == 2:
            expand = np.zeros((2*layer.shape[0], 2*layer.shape[1]), dtype=np.float64)
            expand[::2, ::2] = layer;
            return 4.*self.convolve(expand)
        ch_layer = self.expand_layer(layer[:, :, 0])
        next_layer = np.zeros(list(ch_layer.shape) + [layer.shape[2]], dtype=ch_layer.dtype)
        next_layer[:, :, 0] = ch_layer
        for channel in range(1, layer.shape[2]):
            next_layer[:, :, channel] = self.expand_layer(layer[:, :, channel])
        return next_layer
    def gaussian_pyramid(self, levels):
        self.print_message(' - begin gaussian pyramids               ')
        pyramid = [self.images.astype(np.float64)]
        while levels > 0:
            self.print_message(' - gaussian pyramids, level: {}     '.format(levels))
            next_layer = self.reduce_layer(pyramid[-1][0])
            next_layer_size = [self.num_images] + list(next_layer.shape)
            pyramid.append(np.zeros(next_layer_size, dtype=next_layer.dtype))
            pyramid[-1][0] = next_layer
            for layer in range(1, self.num_images):
                pyramid[-1][layer] = self.reduce_layer(pyramid[-2][layer])
            levels = levels - 1
        self.print_message(' - gaussian pyramids completed               ')
        return pyramid
    def laplacian_pyramid(self, levels):
        gaussian = self.gaussian_pyramid(levels)
        pyramid = [gaussian[-1]]
        for level in range(len(gaussian) - 1, 0, -1):
            self.print_message(' - laplacian pyramids, level: {} - begin     '.format(levels))
            gauss = gaussian[level - 1]
            pyramid.append(np.zeros(gauss.shape, dtype=gauss.dtype))
            for layer in range(self.num_images):
                self.print_message(' - laplacian pyramids, level: {}, layer: {}/{}     '.format(level, layer + 1, self.num_images))
                gauss_layer = gauss[layer]
                expanded = self.expand_layer(gaussian[level][layer])
                if expanded.shape != gauss_layer.shape:
                    expanded = expanded[:gauss_layer.shape[0], :gauss_layer.shape[1]]
                pyramid[-1][layer] = gauss_layer - expanded
        self.print_message(' - laplacian pyramids completed               ')
        return pyramid[::-1]
    def area_entropy(self, area, probabilities):
        levels = area.flatten()
        return np.float64(-1.*(levels*np.log(probabilities[levels])).sum())
    def get_probabilities(self, gray_image):
        levels, counts = np.unique(gray_image.astype(self.dtype), return_counts=True)
        probabilities = np.zeros((self.n_values), dtype=np.float64)
        probabilities[levels] = counts.astype(np.float64)/counts.sum()
        return probabilities
    def get_pad(self, padded_image, row, column):
        return padded_image[row + self.pad_amount + self.offset[:, np.newaxis], column + self.pad_amount + self.offset]
    def entropy(self, image):
        probabilities = self.get_probabilities(image)
        padded_image = cv2.copyMakeBorder(image, self.pad_amount, self.pad_amount, self.pad_amount, self.pad_amount, cv2.BORDER_REFLECT101)
        return np.fromfunction(np.vectorize(lambda row, column: self.area_entropy(self.get_pad(padded_image, row, column), probabilities)), image.shape[:2], dtype=int)
    def area_deviation(self, area):
        return np.square(area - np.average(area).astype(np.float64)).sum()/area.size
    def deviation(self, image):
        padded_image = cv2.copyMakeBorder(image, self.pad_amount, self.pad_amount, self.pad_amount, self.pad_amount, cv2.BORDER_REFLECT101)
        return np.fromfunction(np.vectorize(lambda row, column: self.area_deviation(self.get_pad(padded_image, row, column))), image.shape[:2], dtype=int)
    def get_fused_base(self, images):
        layers, height, width, _ = images.shape
        entropies = np.zeros(images.shape[:3], dtype=np.float64)
        deviations = np.copy(entropies)
        gray_images = np.array([cv2.cvtColor(images[layer].astype(np.float32), cv2.COLOR_BGR2GRAY).astype(self.dtype) for layer in range(layers)])
        entropies = np.array([self.entropy(img) for img in gray_images])
        deviations = np.array([self.deviation(img) for img in gray_images])
        best_e = np.argmax(entropies, axis=0)
        best_d = np.argmax(deviations, axis=0)
        fused = np.zeros(images.shape[1:], dtype=np.float64)
        for layer in range(layers):
            img = images[layer]
            fused += np.where(best_e[:, :, np.newaxis]==layer, img, 0)
            fused += np.where(best_d[:, :, np.newaxis]==layer, img, 0)
        return (fused/2).astype(images.dtype)
    def fuse_pyramids(self, pyramids):
        fused = [self.get_fused_base(pyramids[-1])]
        for layer in range(len(pyramids) - 2, -1, -1):
            laplacians = pyramids[layer]
            layers = laplacians.shape[0]
            self.print_message(' - fuse pyramids, layer: {}     '.format(layer + 1))
            region_energies = np.zeros(laplacians.shape[:3], dtype=np.float64)
            gray_laps = [cv2.cvtColor(laplacians[layer].astype(np.float32), cv2.COLOR_BGR2GRAY) for layer in range(layers)]
            region_energies = np.array([self.convolve(np.square(gray_lap)) for gray_lap in gray_laps])
            best_re = np.argmax(region_energies, axis = 0)
            self.print_message(' - compute fused laplacian: {}     '.format(layer + 1))
            fused_lapl = np.zeros(laplacians.shape[1:], dtype=laplacians.dtype)
            for layer in range(layers):
                fused_lapl += np.where(best_re[:, :, np.newaxis]==layer, laplacians[layer], 0)
            #optimized, but requires more memory
            #return np.array([np.where(best_re[:, :, np.newaxis]==layer, laplacians[layer], 0) for layer in range(layers)]).sum(axis=0)
            fused.append(fused_lapl)
        self.print_message(' - pyramids fusion completed              ')
        return fused[::-1]
    def collapse(self, pyramid):
        image = pyramid[-1]
        for layer in pyramid[-2::-1]:
            expanded = self.expand_layer(image)
            if expanded.shape != layer.shape:
                expanded = expanded[:layer.shape[0], :layer.shape[1]]
            image = expanded + layer
        return image    
    def focus_stack(self, images):
        self.images = images
        self.num_images = images.shape[0]
        self.dtype = images[0].dtype
        if self.dtype == np.uint8: self.n_values = 256
        elif self.dtype == np.uint16: self.n_values = 65536
        else: Exception("Invalid image type: " + self.dtype.str)
        stacked_image = self.collapse(self.fuse_pyramids(self.laplacian_pyramid(int(np.log2(min(images[0].shape[:2])/self.min_size)))))
        return np.clip(np.absolute(stacked_image), 0, self.n_values - 1).astype(self.dtype)