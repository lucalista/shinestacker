from focus_stack.exceptions import ShapeError, BitDepthError
import cv2
import os
import numpy as np
import logging
import matplotlib.pyplot as plt
from config.config import config

if not config.DISABLE_TQDM:
    from tqdm import tqdm
    from tqdm.notebook import tqdm_notebook


def check_path_exists(path):
    if not os.path.exists(path):
        raise Exception('Path does not exist: ' + path)
    
    
def make_tqdm_bar(name, size, ncols=80):
    if not config.DISABLE_TQDM:
        if config.JUPYTER_NOTEBOOK:
            bar = tqdm_notebook(desc=name, total=size)
        else:
            bar = tqdm(desc=name, total=size, ncols=ncols)
        return bar
    else:
        return None


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
    dir_path = os.path.dirname(filename)
    if not dir_path:
        dir_path = '.'
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)
    plt.savefig(filename, dpi=150)
    if show and config.JUPYTER_NOTEBOOK:
        plt.show()
    plt.close('all')
