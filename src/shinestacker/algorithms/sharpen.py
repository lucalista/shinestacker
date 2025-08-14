# pylint: disable=C0114, C0116, E1101
import cv2
import numpy as np


def unsharp_mask(image, radius=1.0, amount=1.0, threshold=0.0):
    if image.dtype == np.uint16:
        threshold = threshold * 256
    blurred = cv2.GaussianBlur(image, (0, 0), radius)
    if threshold == 0:
        sharpened = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
    else:
        image_float = image.astype(np.float32)
        blurred_float = blurred.astype(np.float32)
        diff = image_float - blurred_float
        mask = np.abs(diff) > threshold
        sharpened_float = np.where(mask, image_float + amount * diff, image_float)
        if np.issubdtype(image.dtype, np.integer):
            min_val, max_val = np.iinfo(image.dtype).min, np.iinfo(image.dtype).max
            sharpened = np.clip(sharpened_float, min_val, max_val).astype(image.dtype)
        else:
            sharpened = sharpened_float.astype(image.dtype)
    return sharpened
