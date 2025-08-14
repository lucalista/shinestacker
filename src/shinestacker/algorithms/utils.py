# pylint: disable=C0114, C0116, E1101
import os
import logging
import numpy as np
import cv2
import matplotlib.pyplot as plt
from .. config.config import config
from .. core.exceptions import ShapeError, BitDepthError


def read_img(file_path):
    if not os.path.isfile(file_path):
        raise RuntimeError("File does not exist: " + file_path)
    ext = file_path.split(".")[-1]
    img = None
    if ext in ['jpeg', 'jpg']:
        img = cv2.imread(file_path)
    elif ext in ['tiff', 'tif', 'png']:
        img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
    return img


def write_img(file_path, img):
    ext = file_path.split(".")[-1]
    if ext in ['jpeg', 'jpg']:
        cv2.imwrite(file_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
    elif ext in ['tiff', 'tif']:
        cv2.imwrite(file_path, img, [int(cv2.IMWRITE_TIFF_COMPRESSION), 1])
    elif ext == 'png':
        cv2.imwrite(file_path, img)


def img_8bit(img):
    return (img >> 8).astype('uint8') if img.dtype == np.uint16 else img


def img_bw_8bit(img):
    img = img_8bit(img)
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if len(img.shape) == 2:
        return img
    raise ValueError(f"Unsupported image format: {img.shape}")


def img_bw(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def get_img_metadata(img):
    if img is None:
        return None, None
    return img.shape[:2], img.dtype


def validate_image(img, expected_shape=None, expected_dtype=None):
    if img is None:
        raise RuntimeError("Image is None")
    shape, dtype = get_img_metadata(img)
    if expected_shape and shape[:2] != expected_shape[:2]:
        raise ShapeError(expected_shape, shape)
    if expected_dtype and dtype != expected_dtype:
        raise BitDepthError(expected_dtype, dtype)


def save_plot(filename):
    logging.getLogger(__name__).debug(msg=f"save plot file: {filename}")
    dir_path = os.path.dirname(filename)
    if not dir_path:
        dir_path = '.'
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)
    plt.savefig(filename, dpi=150)
    if config.JUPYTER_NOTEBOOK:
        plt.show()
    plt.close('all')
