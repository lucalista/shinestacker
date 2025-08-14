# pylint: disable=C0114, C0116
import numpy as np


def white_balance_from_rgb(img, target_rgb):
    img_float = img.astype(np.float64)
    target_bgr = (target_rgb[2], target_rgb[1], target_rgb[0])
    target_gray = sum(target_bgr) / 3.0
    scales = [target_gray / val if val != 0 else 1.0 for val in target_bgr]
    for c in range(3):
        img_float[..., c] *= scales[c]
    max_val = np.iinfo(img.dtype).max
    img_float = np.clip(img_float, 0, max_val)
    return img_float.astype(img.dtype)
