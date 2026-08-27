# pylint: disable=C0114, C0116, E1101
import cv2
import numpy as np


def denoise(image, h_luminance, template_window_size=7, search_window_size=21):
    if image.ndim == 3 and image.shape[2] == 4:
        color = denoise(image[..., :3], h_luminance,
                        template_window_size, search_window_size)
        return np.concatenate([color, image[..., 3:4]], axis=2)
    norm_type = cv2.NORM_L2 if image.dtype == np.uint8 else cv2.NORM_L1
    if image.dtype == np.uint16:
        h_luminance = h_luminance * 256
    return cv2.fastNlMeansDenoising(
        image, [h_luminance], None, template_window_size, search_window_size, norm_type
    )
