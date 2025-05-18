import cv2
import os
import re
import numpy as np
from PIL import Image, ExifTags
from PIL.TiffImagePlugin import IFDRational
from PIL.ExifTags import TAGS
import warnings
import logging
import tifffile
import matplotlib.pyplot as plt

IMAGEWIDTH = 256
IMAGELENGTH = 257
RESOLUTIONX = 282
RESOLUTIONY = 283
RESOLUTIONUNIT = 296
BITSPERSAMPLE = 258
PHOTOMETRICINTERPRETATION = 262
SAMPLESPERPIXEL = 277
PLANARCONFIGURATION = 284
SOFTWARE = 305
IMAGERESOURCES = 34377
INTERCOLORPROFILE = 34675
EXIFTAG = 34665
XMLPACKET = 700
NO_COPY_TIFF_TAGS_ID = [IMAGEWIDTH, IMAGELENGTH, RESOLUTIONX, RESOLUTIONY, BITSPERSAMPLE, PHOTOMETRICINTERPRETATION, SAMPLESPERPIXEL, PLANARCONFIGURATION, SOFTWARE, RESOLUTIONUNIT, EXIFTAG, INTERCOLORPROFILE, IMAGERESOURCES]
NO_COPY_TIFF_TAGS = ["Compression", "StripOffsets", "RowsPerStrip", "StripByteCounts"]

def check_path_exists(path):
    if not os.path.exists(path): raise Exception('Path does not exist: ' + path)

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
    return (img >> 8).astype('uint8') if img.dtype == np.uint16 else img

def get_exif(exif_filename):
    if(not os.path.isfile(exif_filename)): raise Exception("File does not exist: " + exif_filename)
    ext = exif_filename.split(".")[-1]
    image = Image.open(exif_filename)
    if ext == 'tif' or ext == 'tiff':
        return image.tag_v2 if hasattr(image, 'tag_v2') else image.getexif()
    elif ext == 'jpeg' or ext == 'jpg':
        with open(exif_filename, 'rb') as f:
            data = f.read()
            xmp_start = data.find(b'<?xpacket')
            xmp_end = data.find(b'<?xpacket end="w"?>') + len('<?xpacket end="w"?>')
            if xmp_start != -1 and xmp_end != -1:
                xmp_bytes = data[xmp_start:xmp_end]
            else: xmp_bytes = ''
        exif_dict = image.getexif()
        exif_dict[XMLPACKET] = xmp_bytes
        return exif_dict
    else: return None

def print_exif(exif, ext):
    logger = logging.getLogger(__name__)
    if exif is None: raise Exception('Image has no exif data.')
    else:
        for tag_id in exif:
            tag = TAGS.get(tag_id, tag_id)
            #if tag_id == XMLPACKET: data = "<<<XML data>>>"
            if tag_id == IMAGERESOURCES or tag_id == INTERCOLORPROFILE: data = "<<< Photoshop data >>>" 
            else:
                if hasattr(exif, 'get'): data = exif.get(tag_id)
                else: data = exif[tag_id]
            if isinstance(data, bytes):
                try: data = data.decode()
                except:
                    logger.warning(f"Print: can't decode EXIF tag {tag:25} [#{tag_id}]")
                    data = '<<< *** decode error *** >>>'
            if isinstance(data, IFDRational):
                data = f"{data.numerator}/{data.denominator}"
            logger.info(f"{tag:25} [#{tag_id:5d}]: {data}")

def get_tiff_dtype_count(value):
    if isinstance(value, str): return 2, len(value) + 1 # ASCII string, (dtype=2), length + null terminator
    elif isinstance(value, (bytes, bytearray)): return 1, len(value) # Binary data (dtype=1)
    elif isinstance(value, (list, tuple, np.ndarray)):
        if isinstance(value, np.ndarray): dtype = value.dtype # Array or sequence
        else: dtype = np.array(value).dtype # Map numpy dtype to TIFF dtype
        if dtype == np.uint8: return 1, len(value)
        elif dtype == np.uint16: return 3, len(value)
        elif dtype == np.uint32: return 4, len(value)
        elif dtype == np.float32: return 11, len(value)
        elif dtype == np.float64: return 12, len(value)
    elif isinstance(value, int):
        if 0 <= value <= 65535: return 3, 1  # uint16
        else: return 4, 1  # uint32
    elif isinstance(value, float): return 11, 1  # float64
    return 2, len(str(value)) + 1 # Default for othre cases (ASCII string)
        
def copy_exif(exif_filename, in_filename, out_filename=None, verbose=False):
    logger = logging.getLogger(__name__)
    ext = in_filename.split(".")[-1]
    if out_filename is None: out_filename = in_filename
    if(not os.path.isfile(exif_filename)): raise Exception("File does not exist: " + exif_filename)
    if(not os.path.isfile(in_filename)): raise Exception("File does not exist: " + in_filename)
    exif = get_exif(exif_filename)
    if exif is None: raise Exception('Image has no exif data.')
    if verbose: print_exif(exif, ext)
    if ext == 'tiff' or ext == 'tif': image_new = tifffile.imread(in_filename)
    else: image_new = Image.open(in_filename)
    if ext == 'jpeg' or ext == 'jpg':
        image_new.save(out_filename, 'JPEG', exif=exif, quality=100)
    elif ext == 'tiff' or ext == 'tif':
        metadata = { "description": "image generated with focusstack package" }
        extra = []
        for tag_id in exif:
            tag = TAGS.get(tag_id, tag_id)
            data = exif.get(tag_id)
            if isinstance(data, bytes):
                try:
                    if tag != "ImageResources" and tag != "InterColorProfile":
                        if tag_id == XMLPACKET:
                            data = re.sub(b'[^\x20-\x7E]', b'', data)
                        data = data.decode()
                except:
                    logger.warning(f"Copy: can't decode EXIF tag {tag:25} [#{tag_id}]")
                    data = '<<< decode error >>>'
            if isinstance(data, IFDRational):
                    data = (data.numerator, data.denominator)
            res_x, res_y = exif.get(RESOLUTIONX), exif.get(RESOLUTIONY)
            if not (res_x is None or res_y is None):
                resolution = ((res_x.numerator, res_x.denominator), (res_y.numerator, res_y.denominator))
            else:
                resolution=((720000, 10000), (720000, 10000))
            res_u = exif.get(RESOLUTIONUNIT)
            resolutionunit = res_u if not res_u is None else 'inch'
            sw = exif.get(SOFTWARE)
            software = sw if not sw is None else "N/A"
            phint = exif.get(PHOTOMETRICINTERPRETATION)
            photometric = phint if not phint is None else None
            if tag not in NO_COPY_TIFF_TAGS and tag_id not in NO_COPY_TIFF_TAGS_ID:
                extra.append((tag_id, *get_tiff_dtype_count(data), data, False))
            else:
                logger.info(f"Skip tag {tag:25} [#{tag_id}]")
        tifffile.imwrite(out_filename, image_new, metadata=metadata, extratags=extra, compression='adobe_deflate',
                        resolution=resolution, resolutionunit=resolutionunit, software=software, photometric=photometric)
    elif ext == 'png':
        image_new.save(out_filename, 'PNG', exif=exif, quality=100)
    return exif

def save_plot(filename, show=True):
    logging.getLogger(__name__).debug("save plot file: " + filename)  
    plt.savefig(filename, dpi=150)
    if show:
        try:
            __IPYTHON__
            plt.show()
        except:
            plt.close()