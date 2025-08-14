# pylint: disable=C0114, C0116, W0718, R0911, R0912, E1101
import os
import re
import io
import logging
import cv2
import numpy as np
from PIL import Image
from PIL.TiffImagePlugin import IFDRational
from PIL.ExifTags import TAGS
import tifffile
from .. config.constants import constants
from .utils import write_img

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
STRIPOFFSETS = 273
STRIPBYTECOUNTS = 279
NO_COPY_TIFF_TAGS_ID = [IMAGEWIDTH, IMAGELENGTH, RESOLUTIONX, RESOLUTIONY, BITSPERSAMPLE,
                        PHOTOMETRICINTERPRETATION, SAMPLESPERPIXEL, PLANARCONFIGURATION, SOFTWARE,
                        RESOLUTIONUNIT, EXIFTAG, INTERCOLORPROFILE, IMAGERESOURCES]
NO_COPY_TIFF_TAGS = ["Compression", "StripOffsets", "RowsPerStrip", "StripByteCounts"]


def extract_enclosed_data_for_jpg(data, head, foot):
    size = len(foot.decode('ascii'))
    xmp_start, xmp_end = data.find(head), data.find(foot)
    if xmp_start != -1 and xmp_end != -1:
        return re.sub(
            b'[^\x20-\x7E]', b'',
            data[xmp_start:xmp_end + size]
        ).decode().replace('\x00', '').encode()
    return None


def get_exif(exif_filename):
    if not os.path.isfile(exif_filename):
        raise RuntimeError(f"File does not exist: {exif_filename}")
    ext = exif_filename.split(".")[-1]
    image = Image.open(exif_filename)
    if ext in ('tif', 'tiff'):
        return image.tag_v2 if hasattr(image, 'tag_v2') else image.getexif()
    if ext in ('jpeg', 'jpg'):
        exif_data = image.getexif()
        with open(exif_filename, 'rb') as f:
            data = extract_enclosed_data_for_jpg(f.read(), b'<?xpacket', b'<?xpacket end="w"?>')
            if data is not None:
                exif_data[XMLPACKET] = data
        return exif_data
    return image.getexif()


def exif_extra_tags_for_tif(exif):
    logger = logging.getLogger(__name__)
    res_x, res_y = exif.get(RESOLUTIONX), exif.get(RESOLUTIONY)
    if not (res_x is None or res_y is None):
        resolution = ((res_x.numerator, res_x.denominator), (res_y.numerator, res_y.denominator))
    else:
        resolution = ((720000, 10000), (720000, 10000))
    res_u = exif.get(RESOLUTIONUNIT)
    resolutionunit = res_u if res_u is not None else 'inch'
    sw = exif.get(SOFTWARE)
    software = sw if sw is not None else "N/A"
    phint = exif.get(PHOTOMETRICINTERPRETATION)
    photometric = phint if phint is not None else None
    extra = []
    for tag_id in exif:
        tag, data = TAGS.get(tag_id, tag_id), exif.get(tag_id)
        if isinstance(data, bytes):
            try:
                if tag_id not in (IMAGERESOURCES, INTERCOLORPROFILE):
                    if tag_id == XMLPACKET:
                        data = re.sub(b'[^\x20-\x7E]', b'', data)
                    data = data.decode()
            except Exception:
                logger.warning(msg=f"Copy: can't decode EXIF tag {tag:25} [#{tag_id}]")
                data = '<<< decode error >>>'
        if isinstance(data, IFDRational):
            data = (data.numerator, data.denominator)
        if tag not in NO_COPY_TIFF_TAGS and tag_id not in NO_COPY_TIFF_TAGS_ID:
            extra.append((tag_id, *get_tiff_dtype_count(data), data, False))
        else:
            logger.debug(msg=f"Skip tag {tag:25} [#{tag_id}]")
    return extra, {'resolution': resolution, 'resolutionunit': resolutionunit,
                   'software': software, 'photometric': photometric}


def get_tiff_dtype_count(value):
    if isinstance(value, str):
        return 2, len(value) + 1  # ASCII string, (dtype=2), length + null terminator
    if isinstance(value, (bytes, bytearray)):
        return 1, len(value)  # Binary data (dtype=1)
    if isinstance(value, (list, tuple, np.ndarray)):
        if isinstance(value, np.ndarray):
            dtype = value.dtype  # Array or sequence
        else:
            dtype = np.array(value).dtype  # Map numpy dtype to TIFF dtype
        if dtype == np.uint8:
            return 1, len(value)
        if dtype == np.uint16:
            return 3, len(value)
        if dtype == np.uint32:
            return 4, len(value)
        if dtype == np.float32:
            return 11, len(value)
        if dtype == np.float64:
            return 12, len(value)
    if isinstance(value, int):
        if 0 <= value <= 65535:
            return 3, 1  # uint16
        return 4, 1  # uint32
    if isinstance(value, float):
        return 11, 1  # float64
    return 2, len(str(value)) + 1  # Default for othre cases (ASCII string)


def add_exif_data_to_jpg_file(exif, in_filenama, out_filename, verbose=False):
    logger = logging.getLogger(__name__)
    if exif is None:
        raise RuntimeError('No exif data provided.')
    if verbose:
        print_exif(exif)
    xmp_data = extract_enclosed_data_for_jpg(exif[XMLPACKET], b'<x:xmpmeta', b'</x:xmpmeta>')
    with Image.open(in_filenama) as image:
        with io.BytesIO() as buffer:
            image.save(buffer, format="JPEG", exif=exif.tobytes(), quality=100)
            jpeg_data = buffer.getvalue()
            if xmp_data is not None:
                app1_marker_pos = jpeg_data.find(b'\xFF\xE1')
                if app1_marker_pos == -1:
                    app1_marker_pos = len(jpeg_data) - 2
                updated_data = (
                    jpeg_data[:app1_marker_pos] +
                    b'\xFF\xE1' + len(xmp_data).to_bytes(2, 'big') +
                    xmp_data + jpeg_data[app1_marker_pos:]
                )
            else:
                logger.warning("Copy: can't find XMLPacket in JPG EXIF data")
                updated_data = jpeg_data
            with open(out_filename, 'wb') as f:
                f.write(updated_data)
    return exif


def write_image_with_exif_data(exif, image, out_filename, verbose=False):
    if exif is None:
        write_img(out_filename, image)
        return None
    ext = out_filename.split(".")[-1]
    if verbose:
        print_exif(exif)
    if ext in ('jpeg', 'jpg'):
        cv2.imwrite(out_filename, image, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
        add_exif_data_to_jpg_file(exif, out_filename, out_filename, verbose)
    elif ext in ('tiff', 'tif'):
        metadata = {"description": f"image generated with {constants.APP_STRING} package"}
        extra_tags, exif_tags = exif_extra_tags_for_tif(exif)
        tifffile.imwrite(out_filename, image, metadata=metadata, compression='adobe_deflate',
                         extratags=extra_tags, **exif_tags)
    elif ext == 'png':
        image.save(out_filename, 'PNG', exif=exif, quality=100)
    return exif


def save_exif_data(exif, in_filename, out_filename=None, verbose=False):
    ext = in_filename.split(".")[-1]
    if out_filename is None:
        out_filename = in_filename
    if exif is None:
        raise RuntimeError('No exif data provided.')
    if verbose:
        print_exif(exif)
    if ext in ('tiff', 'tif'):
        image_new = tifffile.imread(in_filename)
    else:
        image_new = Image.open(in_filename)
    if ext in ('jpeg', 'jpg'):
        add_exif_data_to_jpg_file(exif, in_filename, out_filename, verbose)
    elif ext in ('tiff', 'tif'):
        metadata = {"description": f"image generated with {constants.APP_STRING} package"}
        extra_tags, exif_tags = exif_extra_tags_for_tif(exif)
        tifffile.imwrite(out_filename, image_new, metadata=metadata, compression='adobe_deflate',
                         extratags=extra_tags, **exif_tags)
    elif ext == 'png':
        image_new.save(out_filename, 'PNG', exif=exif, quality=100)
    return exif


def copy_exif_from_file_to_file(exif_filename, in_filename, out_filename=None, verbose=False):
    if not os.path.isfile(exif_filename):
        raise RuntimeError(f"File does not exist: {exif_filename}")
    if not os.path.isfile(in_filename):
        raise RuntimeError(f"File does not exist: {in_filename}")
    exif = get_exif(exif_filename)
    return save_exif_data(exif, in_filename, out_filename, verbose)


def exif_dict(exif, hide_xml=True):
    if exif is None:
        return None
    exif_data = {}
    for tag_id in exif:
        tag = TAGS.get(tag_id, tag_id)
        if tag_id == XMLPACKET and hide_xml:
            data = "<<< XML data >>>"
        elif tag_id in (IMAGERESOURCES, INTERCOLORPROFILE):
            data = "<<< Photoshop data >>>"
        elif tag_id == STRIPOFFSETS:
            data = "<<< Strip offsets >>>"
        elif tag_id == STRIPBYTECOUNTS:
            data = "<<< Strip byte counts >>>"
        else:
            data = exif.get(tag_id) if hasattr(exif, 'get') else exif[tag_id]
        if isinstance(data, bytes):
            try:
                data = data.decode()
            except Exception:
                pass
        exif_data[tag] = (tag_id, data)
    return exif_data


def print_exif(exif, hide_xml=True):
    exif_data = exif_dict(exif, hide_xml)
    if exif_data is None:
        raise RuntimeError('Image has no exif data.')
    logger = logging.getLogger(__name__)
    for tag, (tag_id, data) in exif_data.items():
        if isinstance(data, IFDRational):
            data = f"{data.numerator}/{data.denominator}"
        logger.info(msg=f"{tag:25} [#{tag_id:5d}]: {data}")
