# pylint: disable=C0114, C0116, E1101
import cv2
import numpy as np


def unsharp_mask(image, radius=1.0, amount=1.0, threshold=0.0):
    if image.ndim == 3 and image.shape[2] == 4:
        color = unsharp_mask(image[..., :3], radius, amount, threshold)
        return np.concatenate([color, image[..., 3:4]], axis=2)
    if image.dtype == np.uint16:
        threshold = threshold * 256
    blurred = cv2.GaussianBlur(image, (0, 0), radius)
    if threshold == 0:
        sharpened = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
    else:
        sharpened_base = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
        image_float = image.astype(np.float32)
        blurred_float = blurred.astype(np.float32)
        diff = image_float - blurred_float
        mask = np.abs(diff) > threshold
        sharpened = np.where(mask, sharpened_base, image)
    return sharpened
