# pylint: disable=C0114, C0115, C0116, E1101
import numpy as np
import cv2
from ..config.constants import constants


def gamma_correction(img, gamma):
    max_px_val = constants.MAX_UINT8 if img.dtype == np.uint8 else constants.MAX_UINT16
    ar = np.arange(0, max_px_val + 1, dtype=np.float64)
    lut = np.rint(((ar / max_px_val) ** (1.0 / gamma)) * max_px_val).astype(img.dtype)
    return cv2.LUT(img, lut) if img.dtype == np.uint8 else np.take(lut, img)


def contrast_correction(img, k):
    max_px_val = constants.MAX_UINT8 if img.dtype == np.uint8 else constants.MAX_UINT16
    ar = np.arange(0, max_px_val + 1, dtype=np.float64)
    x = 2.0 * (ar / max_px_val) - 1.0
    # f(x) = x * exp(k) / (1 + (exp(k) - 1)|x|),  -1 < x < +1
    # note that: f(f(x, k), -k) = x
    exp_k = np.exp(k)
    numerator = x * exp_k
    denominator = 1 + (exp_k - 1) * np.abs(x)
    corrected = numerator / denominator
    corrected = (corrected + 1.0) * 0.5 * max_px_val
    lut = np.clip(np.rint(corrected), 0, max_px_val).astype(img.dtype)
    return cv2.LUT(img, lut) if img.dtype == np.uint8 else np.take(lut, img)
