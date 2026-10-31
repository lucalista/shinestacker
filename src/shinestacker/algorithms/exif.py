# pylint: disable=C0302, W0718, R0911, R0912
# pylint: disable=R0915, R1702, R0914, R0917, R0913
import os
import logging
import traceback
import cv2
from PIL import Image, UnidentifiedImageError
from PIL.TiffImagePlugin import IFDRational
from PIL.ExifTags import TAGS
import tifffile
from .utils import (
    read_img, write_img, extension_jpg, extension_tif, extension_png, extension_raw)
from .exif_tiff import (
    get_exif_from_tiff,
    exif_extra_tags_for_tif,
    write_image_with_exif_data_tif,
)
from .exif_jpeg import (
    add_exif_data_to_jpg_file,
    write_image_with_exif_data_jpg,
    get_exif_from_jpg,
)
from .exif_png import (
    get_exif_from_png,
    write_image_with_exif_data_png,
    get_enhanced_exif_from_png,
)
from .exif_common import write_tiff_with_metadata


def get_exif(exif_filename, enhanced_png_parsing=True):
    if not os.path.isfile(exif_filename):
        raise RuntimeError(f"File does not exist: {exif_filename}")
    is_raw = extension_raw(exif_filename)
    try:
        image = Image.open(exif_filename)
    except UnidentifiedImageError as e:
        if not is_raw:
            traceback.print_stack()
            raise RuntimeError(
                f"PIL.Image.open UnidentifiedImageError exception: {str(e)}"
            ) from e
        image = None

    if extension_tif(exif_filename) or is_raw:
        return get_exif_from_tiff(image, exif_filename)
    if extension_jpg(exif_filename):
        return get_exif_from_jpg(image, exif_filename)
    if extension_png(exif_filename):
        if enhanced_png_parsing:
            return get_enhanced_exif_from_png(image)
        exif_data = get_exif_from_png(image)
        return exif_data if exif_data else image.getexif()
    return image.getexif()


def write_image_with_exif_data(
    exif, image, out_filename, verbose=False, color_order="auto"
):
    if exif is None:
        write_img(out_filename, image)
        return None
    if verbose:
        print_exif(exif)
    if extension_jpg(out_filename):
        write_image_with_exif_data_jpg(exif, image, out_filename, verbose)
    elif extension_tif(out_filename):
        write_image_with_exif_data_tif(exif, image, out_filename)
    elif extension_png(out_filename):
        write_image_with_exif_data_png(
            exif, image, out_filename, color_order=color_order
        )
    return exif


def save_exif_data(exif, in_filename, out_filename=None, verbose=False):
    if out_filename is None:
        out_filename = in_filename
    if exif is None:
        raise RuntimeError("No exif data provided.")
    use_temp = in_filename == out_filename
    temp_filename = out_filename + ".tmp" if use_temp else out_filename
    try:
        if extension_png(in_filename) or extension_tif(in_filename):
            if extension_tif(in_filename):
                image_new = tifffile.imread(in_filename)
            elif extension_png(in_filename):
                image_new = cv2.imread(in_filename, cv2.IMREAD_UNCHANGED)
            if extension_tif(in_filename):
                write_tiff_with_metadata(temp_filename, image_new, exif, exif_extra_tags_for_tif)
            elif extension_png(in_filename):
                write_image_with_exif_data_png(exif, image_new, temp_filename)
        else:
            add_exif_data_to_jpg_file(exif, in_filename, temp_filename, verbose)
        if use_temp:
            if os.path.exists(out_filename):
                os.remove(out_filename)
            os.rename(temp_filename, out_filename)
        return exif
    except Exception:
        if use_temp and os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception:
                pass
        if extension_tif(in_filename):
            image_new = tifffile.imread(in_filename)
            tifffile.imwrite(out_filename, image_new, compression="adobe_deflate")
        elif extension_png(in_filename):
            image_new = cv2.imread(in_filename, cv2.IMREAD_UNCHANGED)
            write_img(out_filename, image_new)
        else:
            write_img(out_filename, read_img(in_filename))
        raise


def copy_exif_from_file_to_file(
    exif_filename, in_filename, out_filename=None, verbose=False
):
    if not os.path.isfile(exif_filename):
        raise RuntimeError(f"File does not exist: {exif_filename}")
    if not os.path.isfile(in_filename):
        raise RuntimeError(f"File does not exist: {in_filename}")
    exif = get_exif(exif_filename)
    return save_exif_data(exif, in_filename, out_filename, verbose)


def exif_dict(exif_data):
    if exif_data is None:
        return None
    result = {}
    for tag, value in exif_data.items():
        if isinstance(tag, int):
            tag_name = TAGS.get(tag, str(tag))
        else:
            tag_name = str(tag)
        if tag_name.startswith("PNG_EXIF_"):
            standard_tag = tag_name[9:]
        elif tag_name.startswith("EXIF_"):
            standard_tag = tag_name[5:]
        elif tag_name.startswith("PNG_"):
            continue
        else:
            standard_tag = tag_name
        result[standard_tag] = (tag, value)
    return result


def print_exif(exif):
    exif_data = exif_dict(exif)
    if exif_data is None:
        raise RuntimeError("Image has no exif data.")
    logger = logging.getLogger(__name__)
    for tag, (tag_id, data) in exif_data.items():
        if isinstance(data, IFDRational):
            data = f"{data.numerator}/{data.denominator}"
        data_str = f"{data}"
        if len(data_str) > 40:
            data_str = f"{data_str[:40]}... (truncated)"
        if isinstance(tag_id, int):
            tag_id_str = f"[#{tag_id:5d}]"
        else:
            tag_id_str = f"[ {tag_id:20} ]"
        logger.info(msg=f"{tag:25} {tag_id_str}: {data_str}")
