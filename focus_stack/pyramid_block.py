import numpy as np
from config.constants import constants
from focus_stack.exceptions import ImageLoadError
from focus_stack.utils import read_img, get_img_metadata, validate_image
from focus_stack.pyramid import PyramidBase


class PyramidBlock(PyramidBase):
    def __init__(self, min_size=constants.DEFAULT_PY_MIN_SIZE, kernel_size=constants.DEFAULT_PY_KERNEL_SIZE,
                 gen_kernel=constants.DEFAULT_PY_GEN_KERNEL, float_type=constants.DEFAULT_PY_FLOAT):
        super().__init__(min_size, kernel_size, gen_kernel, float_type)
        self.offset = np.arange(-self.pad_amount, self.pad_amount + 1)

    def name(self):
        return "pyramid-block"

    def gaussian_pyramid(self, levels):
        self.print_message(': beginning gaussian pyramids')
        pyramid = [self.images.astype(self.float_type)]
        while levels > 0:
            self.print_message(': gaussian pyramids, level: {}'.format(levels))
            next_layer = self.reduce_layer(pyramid[-1][0])
            next_layer_size = [self.num_images] + list(next_layer.shape)
            pyramid.append(np.zeros(next_layer_size, dtype=next_layer.dtype))
            pyramid[-1][0] = next_layer
            for layer in range(1, self.num_images):
                pyramid[-1][layer] = self.reduce_layer(pyramid[-2][layer])
            levels = levels - 1
        self.print_message(': gaussian pyramids completed')
        return pyramid

    def laplacian_pyramid(self, levels):
        gaussian = self.gaussian_pyramid(levels)
        pyramid = [gaussian[-1]]
        for level in range(len(gaussian) - 1, 0, -1):
            self.print_message(': laplacian pyramids, level: {}: begin'.format(levels))
            gauss = gaussian[level - 1]
            pyramid.append(np.zeros(gauss.shape, dtype=gauss.dtype))
            for layer in range(self.num_images):
                self.print_message(
                    ': laplacian pyramids, level: {}, layer: {}/{}'.format(level, layer + 1, self.num_images))
                gauss_layer = gauss[layer]
                expanded = self.expand_layer(gaussian[level][layer])
                if expanded.shape != gauss_layer.shape:
                    expanded = expanded[:gauss_layer.shape[0], :gauss_layer.shape[1]]
                pyramid[-1][layer] = gauss_layer - expanded
        self.print_message(': laplacian pyramids completed')
        return pyramid[::-1]

    def fuse_pyramids(self, pyramids):
        fused = [self.get_fused_base(pyramids[-1])]
        for layer in range(len(pyramids) - 2, -1, -1):
            laplacians = pyramids[layer]
            self.print_message(': fusing pyramids, layer: {}'.format(layer + 1))
            fused.append(self.fuse_laplacian(laplacians))
        self.print_message(': pyramids fusion completed')
        return fused[::-1]

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
                self.dtype = metadata[1]
            else:
                validate_image(img, *metadata)
            images.append(img)
        self.images = np.array(images, dtype=self.dtype)
        self.num_images = self.images.shape[0]
        self.n_values = 256 if self.dtype == np.uint8 else 65536
        stacked_image = self.collapse(self.fuse_pyramids(
            self.laplacian_pyramid(int(np.log2(min(self.images[0].shape[:2]) / self.min_size)))))
        return stacked_image.astype(self.dtype)
