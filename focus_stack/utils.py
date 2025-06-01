from focus_stack.exceptions import ShapeError, BitDepthError
import cv2
import os
import numpy as np
import logging
import matplotlib.pyplot as plt
from tqdm import tqdm
from tqdm.notebook import tqdm_notebook


def check_path_exists(path):
    if not os.path.exists(path):
        raise Exception('Path does not exist: ' + path)


def make_tqdm_bar(name, size, ncols=80):
    try:
        __IPYTHON__  # noqa
        bar = tqdm_notebook(desc=name, total=size)
    except Exception:
        bar = tqdm(desc=name, total=size, ncols=ncols)
    return bar


def read_img(file_path):
    if not os.path.isfile(file_path):
        raise Exception("File does not exist: " + file_path)
    ext = file_path.split(".")[-1]
    if ext == 'jpeg' or ext == 'jpg':
        img = cv2.imread(file_path)
    elif ext == 'tiff' or ext == 'tif' or ext == 'png':
        img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
    return img


def write_img(file_path, img):
    ext = file_path.split(".")[-1]
    if ext == 'jpeg' or ext == 'jpg':
        cv2.imwrite(file_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
    elif ext == 'tiff' or ext == 'tif':
        cv2.imwrite(file_path, img, [int(cv2.IMWRITE_TIFF_COMPRESSION), 1])
    elif ext == 'png':
        cv2.imwrite(file_path, img)


def img_8bit(img):
    return (img >> 8).astype('uint8') if img.dtype == np.uint16 else img


def img_bw_8bit(img):
    return cv2.cvtColor(img_8bit(img), cv2.COLOR_BGR2GRAY)


def get_img_metadata(img):
    return img.shape[:2], img.dtype


def validate_image(img, expected_shape=None, expected_dtype=None):
    shape, dtype = get_img_metadata(img)
    if expected_shape and shape != expected_shape:
        raise ShapeError(shape, expected_shape)
    if expected_dtype and dtype != expected_dtype:
        raise BitDepthError(dtype, expected_dtype)


def save_plot(filename, show=True):
    logging.getLogger(__name__).debug("save plot file: " + filename)
    plt.savefig(filename, dpi=150)
    if show:
        try:
            __IPYTHON__  # noqa
            plt.show()
        except Exception:
            pass
    plt.close()
