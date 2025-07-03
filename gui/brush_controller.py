import numpy as np
from gui.brush_preview import create_brush_mask
from config.constants import constants

DEFAULT_BRUSH_HARDNESS = 50
DEFAULT_BRUSH_OPACITY = 100

BRUSH_SIZES = {
    'default': 50,
    'min': 4,
    'mid': 50,
    'max': 1000
}


class BrushController:
    def __init__(self):
        self._brush_mask_cache = {}
        self.brush_size = BRUSH_SIZES['default']
        self.brush_hardness = DEFAULT_BRUSH_HARDNESS
        self.brush_opacity = DEFAULT_BRUSH_OPACITY

    def apply_brush_operation(self, master_layer, source_layer, dest_layer, mask_layer, view_pos, image_viewer):
        if master_layer is None or source_layer is None:
            return False
        if dest_layer is None:
            dest_layer = master_layer
        scene_pos = image_viewer.mapToScene(view_pos)
        x_center = int(round(scene_pos.x()))
        y_center = int(round(scene_pos.y()))
        radius = int(round(self.brush_size // 2))
        h, w = master_layer.shape[:2]
        x_start, x_end = max(0, x_center - radius), min(w, x_center + radius + 1)
        y_start, y_end = max(0, y_center - radius), min(h, y_center + radius + 1)
        if x_start >= x_end or y_start >= y_end:
            return 0, 0, 0, 0
        mask = self._get_brush_mask(radius)
        if mask is None:
            return 0, 0, 0, 0
        master_area = master_layer[y_start:y_end, x_start:x_end]
        source_area = source_layer[y_start:y_end, x_start:x_end]
        dest_area = dest_layer[y_start:y_end, x_start:x_end]
        mask_layer_area = mask_layer[y_start:y_end, x_start:x_end]
        mask_area = mask[y_start - (y_center - radius):y_end - (y_center - radius), x_start - (x_center - radius):x_end - (x_center - radius)]
        mask_layer_area[:] = np.maximum(mask_layer_area, mask_area)
        self._apply_mask(master_area, source_area, mask_layer_area, dest_area)
        return x_start, y_start, x_end, y_end

    def _get_brush_mask(self, radius):
        mask_key = (radius, self.brush_hardness)
        if mask_key not in self._brush_mask_cache.keys():
            full_mask = create_brush_mask(size=radius * 2 + 1, hardness_percent=self.brush_hardness,
                                          opacity_percent=self.brush_opacity)
            self._brush_mask_cache[mask_key] = full_mask
        return self._brush_mask_cache[mask_key]

    def _apply_mask(self, master_area, source_area, mask_area, dest_area):
        opacity_factor = float(self.brush_opacity) / 100.0
        effective_mask = np.clip(mask_area * opacity_factor, 0, 1)
        dtype = master_area.dtype
        max_px_value = constants.MAX_UINT16 if dtype == np.uint16 else constants.MAX_UINT8
        if master_area.ndim == 3:
            dest_area[:] = np.clip(master_area * (1 - effective_mask[..., np.newaxis]) + source_area * # noqa
                                   effective_mask[..., np.newaxis], 0, max_px_value).astype(dtype)
        else:
            dest_area[:] = np.clip(master_area * (1 - effective_mask) + source_area * effective_mask, 0, max_px_value).astype(dtype)

    def clear_cache(self):
        self._brush_mask_cache.clear()
