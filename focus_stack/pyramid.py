import numpy as np
from scipy import ndimage
import cv2
# from CGPT
from scipy.ndimage import generic_filter


def generating_kernel(a):
    kernel = np.array([0.25 - a/2.0, 0.25, a, 0.25, 0.25 - a/2.0])
    return np.outer(kernel, kernel)

def convolve(image, kernel=generating_kernel(0.4)):
    #return ndimage.convolve(image.astype(np.float64), kernel, mode='mirror')
    return cv2.filter2D(image, -1, kernel, borderType=cv2.BORDER_REFLECT)
    
def reduce_layer(layer, kernel=generating_kernel(0.4)):
    if len(layer.shape) == 2:
        convolution = convolve(layer, kernel)
        return convolution[::2, ::2]
    ch_layer = reduce_layer(layer[:, :, 0])
    next_layer = np.zeros(list(ch_layer.shape) + [layer.shape[2]], dtype = ch_layer.dtype)
    next_layer[:, :, 0] = ch_layer
    for channel in range(1, layer.shape[2]):
        next_layer[:, :, channel] = reduce_layer(layer[:, :, channel])
    return next_layer

def expand_layer(layer, kernel=generating_kernel(0.4)):
    if len(layer.shape) == 2:
        expand = np.zeros((2*layer.shape[0], 2*layer.shape[1]), dtype=np.float64)
        expand[::2, ::2] = layer;
        convolution = convolve(expand, kernel)
        return 4.*convolution
    ch_layer = expand_layer(layer[:, :, 0])
    next_layer = np.zeros(list(ch_layer.shape) + [layer.shape[2]], dtype=ch_layer.dtype)
    next_layer[:, :, 0] = ch_layer
    for channel in range(1, layer.shape[2]):
        next_layer[:, :, channel] = expand_layer(layer[:, :, channel])
    return next_layer

class PyramidStack:
    def __init__(self, min_size=32, kernel_size=5, verbose=False):
        self.min_size = min_size
        self.kernel_size = kernel_size
        self.verbose = verbose
    def gaussian_pyramid(self, images, levels):
        if self.verbose: print('- gaussian pyramids, level:', end='')
        pyramid = [images.astype(np.float64)]
        num_images = images.shape[0]
        while levels > 0:
            if self.verbose: print(' {}'.format(levels), end='')
            next_layer = reduce_layer(pyramid[-1][0])
            next_layer_size = [num_images] + list(next_layer.shape)
            pyramid.append(np.zeros(next_layer_size, dtype=next_layer.dtype))
            pyramid[-1][0] = next_layer
            for layer in range(1, images.shape[0]):
                pyramid[-1][layer] = reduce_layer(pyramid[-2][layer])
            levels = levels - 1
        if self.verbose: print(' gaussian pyramids completed')
        return pyramid
    def laplacian_pyramid(self, images, levels):
        gaussian = self.gaussian_pyramid(images, levels)
        pyramid = [gaussian[-1]]
        if self.verbose: print('- laplacian pyramids, level:', end='')
        for level in range(len(gaussian) - 1, 0, -1):
            if self.verbose: print(' {}'.format(level), end='')
            gauss = gaussian[level - 1]
            pyramid.append(np.zeros(gauss.shape, dtype=gauss.dtype))
            for layer in range(images.shape[0]):
                gauss_layer = gauss[layer]
                expanded = expand_layer(gaussian[level][layer])
                if expanded.shape != gauss_layer.shape:
                    expanded = expanded[:gauss_layer.shape[0], :gauss_layer.shape[1]]
                pyramid[-1][layer] = gauss_layer - expanded
        if self.verbose: print(' laplacian pyramids completed')
        return pyramid[::-1]
    def area_entropy(self, area, probabilities):
        levels = area.flatten()
        return -1.*(levels*np.log(probabilities[levels])).sum()
    def get_probabilities(self, gray_image):
        levels, counts = np.unique(gray_image.astype(self.dtype), return_counts=True)
        probabilities = np.zeros((self.n_values), dtype=np.float64)
        probabilities[levels] = counts.astype(np.float64)/counts.sum()
        return probabilities
    def entropy(self, image):
        probabilities = self.get_probabilities(image)
        pad_amount = int((self.kernel_size - 1)/2)
        padded_image = cv2.copyMakeBorder(image, pad_amount, pad_amount, pad_amount, pad_amount, cv2.BORDER_REFLECT101)
        entropies = np.zeros(image.shape[:2], dtype=np.float64)
        offset = np.arange(-pad_amount, pad_amount + 1)
        for row in range(entropies.shape[0]):
            for column in range(entropies.shape[1]):
                entropies[row, column] = self.area_entropy(padded_image[row + pad_amount + offset[:, np.newaxis], column + pad_amount + offset], probabilities)
        return entropies
    def area_deviation(self, area):
        average = np.average(area).astype(np.float64)
        return np.square(area - average).sum()/area.size
    def deviation(self, image):
        pad_amount = int((self.kernel_size - 1)/2)
        padded_image = cv2.copyMakeBorder(image, pad_amount, pad_amount, pad_amount, pad_amount, cv2.BORDER_REFLECT101)
        deviations = np.zeros(image.shape[:2], dtype=np.float64)
        offset = np.arange(-pad_amount, pad_amount + 1)
        for row in range(deviations.shape[0]):
            for column in range(deviations.shape[1]):
                deviations[row, column] = self.area_deviation(padded_image[row + pad_amount + offset[:, np.newaxis], column + pad_amount + offset])
        return deviations
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
            fused += np.where(best_e[:, :, np.newaxis]==layer, images[layer], 0)
            fused += np.where(best_d[:, :, np.newaxis]==layer, images[layer], 0)
        return (fused/2).astype(images.dtype)
    def get_fused_laplacian(self, laplacians):
        def _region_energy(laplacian):
            return convolve(np.square(laplacian))
        layers = laplacians.shape[0]
        region_energies = np.zeros(laplacians.shape[:3], dtype=np.float64)
        gray_laps = [cv2.cvtColor(laplacians[layer].astype(np.float32), cv2.COLOR_BGR2GRAY) for layer in range(layers)]
        region_energies = np.array([_region_energy(gray_lap) for gray_lap in gray_laps])
        best_re = np.argmax(region_energies, axis = 0)
        fused = np.zeros(laplacians.shape[1:], dtype=laplacians.dtype)
        for layer in range(layers):
            fused += np.where(best_re[:, :, np.newaxis]==layer, laplacians[layer], 0)
        return fused
    def fuse_pyramids(self, pyramids):
        if self.verbose: print('- fuse pyramids, layer:', end='')
        fused = [self.get_fused_base(pyramids[-1])]
        for layer in range(len(pyramids) - 2, -1, -1):
            if self.verbose: print(' {}'.format(layer + 1), end='')
            fused.append(self.get_fused_laplacian(pyramids[layer]))
        if self.verbose: print(' fuse pyramids completed ')
        return fused[::-1]
    def collapse(self, pyramid):
        image = pyramid[-1]
        for layer in pyramid[-2::-1]:
            expanded = expand_layer(image)
            if expanded.shape != layer.shape:
                expanded = expanded[:layer.shape[0], :layer.shape[1]]
            image = expanded + layer
        return image    
    def focus_stack(self, images):
        self.dtype = images[0].dtype
        if self.dtype == np.uint8: self.n_values = 256
        elif self.dtype == np.uint16: self.n_values = 65536
        else: Exception("Invalid image type: " + self.dtype.str)
        smallest_side = min(images[0].shape[:2])
        depth = int(np.log2(smallest_side/self.min_size))
        pyramids = self.laplacian_pyramid(images, depth)
        fusion = self. fuse_pyramids(pyramids)
        stacked_image = self.collapse(fusion)
        return np.clip(np.absolute(stacked_image), 0, self.n_values - 1).astype(self.dtype)