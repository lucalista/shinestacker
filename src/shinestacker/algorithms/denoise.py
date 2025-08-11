import cv2
import numpy as np


def denoise(image, h_luminance, photo_render, search_window=21, block_size=7):
    if image.dtype == np.uint8:
        return cv2.fastNlMeansDenoisingColored(image, None, h_luminance, photo_render, search_window, block_size)
    else:
        raise RuntimeError("denoise only supports 8 bit images")
