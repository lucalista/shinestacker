# pylint: disable=C0114, C0115, C0116, E1101, E0606
import numpy as np
import cv2
from .utils import bgr_to_lab, lab_to_bgr


def local_tonemapping(img, amount, clip_limit, tile_size):
    if img.dtype not in (np.uint8, np.uint16):
        raise ValueError(f"Unsupported image dtype: {img.dtype}")
    if len(img.shape) == 3:
        lab = bgr_to_lab(img)
        l_channel, a, b = cv2.split(lab)
        is_color = True
    else:
        l_channel = img
        is_color = False
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    if l_channel.dtype == np.uint8:
        l_enhanced = clahe.apply(l_channel)
    else:
        l_scaled = np.rint(l_channel.astype(np.float32) / 65535.0 * 255.0).astype(np.uint8)
        l_enhanced_8bit = clahe.apply(l_scaled)
        l_enhanced = np.rint(
            l_enhanced_8bit.astype(np.float32) / 255.0 * 65535.0).astype(np.uint16)
    if amount <= 0:
        return img
    if amount >= 1.0:
        l_final = l_enhanced
    else:
        l_final = cv2.addWeighted(l_channel, 1 - amount, l_enhanced, amount, 0)
    if is_color:
        lab_enhanced = cv2.merge([l_final, a, b])
        return lab_to_bgr(lab_enhanced)
    return l_final
