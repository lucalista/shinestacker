import cv2
import os
import numpy as np
from PIL import Image, ExifTags
from PIL.ExifTags import TAGS
import warnings

# Bad TIFF keys in specific PIL version
BAD_EXIF_KEYS_16BITS_TIFF = [33723, 34665]
#BAD_EXIF_KEYS_16BITS_TIFF = []

def check_path_exists(path):
    assert os.path.exists(path), 'path does not exist: ' + path

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
    elif ext == 'tiff' or ext == 'tif':
        cv2.imwrite(file_path, img, [int(cv2.IMWRITE_TIFF_COMPRESSION), 1])
    elif ext == 'png':
        cv2.imwrite(file_path, img) 
        
def img_8bit(img):
    if img.dtype == np.uint16:
        return (img >> 8).astype('uint8')
    else:
        return img
    
def print_exif(exif, ext):
    if exif is None:
        print('image has no exif data.')
    else:
        for tag_id in exif:
            if (ext == 'tiff' or ext == 'tif') and (tag_id in BAD_EXIF_KEYS_16BITS_TIFF):
                print(f'<<< skipped >>>           [#{tag_id}]: <<< bad key for TIFF format in PIL module >>>')
            else:
                tag = TAGS.get(tag_id, tag_id)
                data = exif.get(tag_id)
                if isinstance(data, bytes):
                    try:
                        data = data.decode()
                    except:
                        data = '<<< decode error >>>'
                print(f"{tag:25} [#{tag_id}]: {data}")
                
def copy_exif(exif_filename, in_filename, out_filename=None, verbose=False):
    if out_filename is None: out_filename = in_filename
    if(not os.path.isfile(exif_filename)): raise Exception("File does not exist: " + exif_filename)
    if(not os.path.isfile(in_filename)): raise Exception("File does not exist: " + in_filename)
    image = Image.open(exif_filename)
    exif = image.tag_v2 if hasattr(image, 'tag_v2') else image.getexif()
    ext = in_filename.split(".")[-1]
    if verbose: print_exif(exif, ext)
    image_new = Image.open(in_filename)
    if ext == 'jpeg' or ext == 'jpg':
        image_new.save(out_filename, 'JPEG', exif=exif, quality=100)
    elif ext == 'tiff' or ext == 'tif':
        for k in BAD_EXIF_KEYS_16BITS_TIFF:
            if k in exif: del exif[k]
        image_new.save(out_filename, 'TIFF', exif=exif)
    elif ext == 'png':
        image_new.save(out_filename, 'PNG', exif=exif, quality=100)