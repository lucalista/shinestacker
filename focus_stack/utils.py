import cv2
import os
import numpy as np

def read_img(file_path):
    if not os.path.isfile(file_path): raise Exception("File does not exist: " + file_path)
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
    elif ext == 'tiff' or ext == 'tif' or ext == 'png':
        cv2.imwrite(file_path, img)
        
def img_8bit(img):
    if img.dtype == np.uint16:
        return (img >> 8).astype('uint8')
    else:
        return img