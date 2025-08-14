# pylint: disable=C0114, C0115, C0116, R0914
import numpy as np
from .image_editor import ImageEditor
from .filter_manager import FilterManager
from .denoise_filter import DenoiseFilter
from .unsharp_mask_filter import UnsharpMaskFilter
from .white_balance_filter import WhiteBalanceFilter


class ImageFilters(ImageEditor):
    def __init__(self):
        super().__init__()
        self.filter_manager = FilterManager(self)
        self.filter_manager.register_filter("denoise", DenoiseFilter)
        self.filter_manager.register_filter("unsharp_mask", UnsharpMaskFilter)
        self.filter_manager.register_filter("white_balance", WhiteBalanceFilter)

    def denoise_filter(self):
        self.filter_manager.apply("denoise")

    def unsharp_mask(self):
        self.filter_manager.apply("unsharp_mask")

    def white_balance(self, init_val=None):
        self.filter_manager.apply("white_balance", init_val=init_val or (128, 128, 128))

    def connect_preview_toggle(self, preview_check, do_preview, restore_original):
        def on_toggled(checked):
            if checked:
                do_preview()
            else:
                restore_original()
        preview_check.toggled.connect(on_toggled)

    def get_pixel_color_at(self, pos, radius=None):
        item_pos = self.image_viewer.position_on_image(pos)
        x = int(item_pos.x())
        y = int(item_pos.y())
        master_layer = self.master_layer()
        if (0 <= x < self.master_layer().shape[1]) and \
           (0 <= y < self.master_layer().shape[0]):
            if radius is None:
                radius = int(self.brush.size)
            if radius > 0:
                y_indices, x_indices = np.ogrid[-radius:radius + 1, -radius:radius + 1]
                mask = x_indices**2 + y_indices**2 <= radius**2
                x0 = max(0, x - radius)
                x1 = min(master_layer.shape[1], x + radius + 1)
                y0 = max(0, y - radius)
                y1 = min(master_layer.shape[0], y + radius + 1)
                mask = mask[radius - (y - y0): radius + (y1 - y),
                            radius - (x - x0): radius + (x1 - x)]
                region = master_layer[y0:y1, x0:x1]
                if region.size == 0:
                    pixel = master_layer[y, x]
                else:
                    if region.ndim == 3:
                        pixel = [region[:, :, c][mask].mean() for c in range(region.shape[2])]
                    else:
                        pixel = region[mask].mean()
            else:
                pixel = self.master_layer()[y, x]
            if np.isscalar(pixel):
                pixel = [pixel, pixel, pixel]
            pixel = [np.float32(x) for x in pixel]
            if master_layer.dtype == np.uint16:
                pixel = [x / 256.0 for x in pixel]
            return tuple(int(v) for v in pixel)
        return (0, 0, 0)
