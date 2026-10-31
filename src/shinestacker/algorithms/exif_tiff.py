# pylint: disable=C0302, W0718, R0911, R0912, E1101, R0914
import cv2
import tifffile
from PIL import Image
from PIL.ExifTags import TAGS
from PIL.TiffImagePlugin import IFDRational
from . import exif_constants as ec
from ..config.constants import constants
from .exif_common import parse_xmp_to_exif, safe_write_with_temp, write_tiff_with_metadata

NO_COPY_TIFF_TAGS_ID = [
    ec.IMAGEWIDTH,
    ec.IMAGELENGTH,
    ec.XRESOLUTION,
    ec.YRESOLUTION,
    ec.BITSPERSAMPLE,
    ec.PHOTOMETRICINTERPRETATION,
    ec.SAMPLESPERPIXEL,
    ec.PLANARCONFIGURATION,
    ec.SOFTWARE,
    ec.RESOLUTIONUNIT,
    ec.EXIFIFD,
    ec.INTERCOLORPROFILE,
    ec.IMAGERESOURCES,
    ec.STRIPOFFSETS,
    ec.STRIPBYTECOUNTS,
    ec.TILEOFFSETS,
    ec.TILEBYTECOUNTS,
    ec.GPSIFD
]

NO_COPY_TIFF_TAGS = ["Compression", "StripOffsets", "RowsPerStrip", "StripByteCounts"]


def get_exif_from_tiff(image, exif_filename):
    if image is not None:
        exif_data = image.tag_v2 if hasattr(image, "tag_v2") else image.getexif()
    else:
        exif_data = Image.Exif()
    try:
        with tifffile.TiffFile(exif_filename) as tif:
            for page in tif.pages:
                if ec.EXIFIFD in page.tags:
                    exif_dict_data = page.tags[ec.EXIFIFD].value
                    for exif_key, tag_id in ec.EXPOSURE_DATA_TIFF.items():
                        if exif_key in exif_dict_data:
                            value = exif_dict_data[exif_key]
                            if isinstance(value, tuple) and len(value) == 2:
                                value = IFDRational(value[0], value[1])
                            exif_data[tag_id] = value
                    break
                if ec.INTERCOLORPROFILE in page.tags:
                    icc_profile = page.tags[ec.INTERCOLORPROFILE].value
                    exif_data[ec.INTERCOLORPROFILE] = icc_profile
    except Exception as e:
        print(f"Error reading EXIF with tifffile: {e}")
    try:
        if ec.XMLPACKET in exif_data:
            xmp_data = exif_data[ec.XMLPACKET]
            if isinstance(xmp_data, bytes):
                xmp_string = xmp_data.decode("utf-8", errors="ignore")
            else:
                xmp_string = str(xmp_data)
            xmp_exif = parse_xmp_to_exif(xmp_string)
            for tag_id in [
                ec.EXPOSURETIME,
                ec.FNUMBER,
                ec.ISOSPEEDRATINGS,
                ec.FOCALLENGTH,
                ec.LENSMODEL,
            ]:
                if tag_id in xmp_exif and tag_id not in exif_data:
                    exif_data[tag_id] = xmp_exif[tag_id]
    except Exception:
        pass
    return exif_data


def clean_data_for_tiff(data):
    if isinstance(data, str):
        return data.encode("ascii", "ignore").decode("ascii")
    if isinstance(data, bytes):
        decoded = data.decode("utf-8", "ignore")
        return decoded.encode("ascii", "ignore").decode("ascii")
    if isinstance(data, IFDRational):
        return (data.numerator, data.denominator)
    return data


def exif_extra_tags_for_tif(exif):
    res_x, res_y = exif.get(ec.XRESOLUTION), exif.get(ec.YRESOLUTION)
    resolution = (
        ((res_x.numerator, res_x.denominator), (res_y.numerator, res_y.denominator))
        if res_x and res_y
        else ((720000, 10000), (720000, 10000))
    )
    exif_tags = {
        "resolution": resolution,
        "resolutionunit": exif.get(ec.RESOLUTIONUNIT, 2),
        "software": clean_data_for_tiff(exif.get(ec.SOFTWARE)) or constants.APP_TITLE,
        "photometric": exif.get(ec.PHOTOMETRICINTERPRETATION, 2),
    }
    extra = []
    safe_tags = [
        ec.MAKE,
        ec.MODEL,
        ec.SOFTWARE,
        ec.DATETIME,
        ec.ARTIST,
        ec.COPYRIGHT,
        ec.ISOSPEEDRATINGS,
        ec.ORIENTATION,
        ec.IMAGEWIDTH,
        ec.IMAGELENGTH,
    ]
    special_handling_tags = [
        ec.EXPOSURETIME,
        ec.FNUMBER,
        ec.FOCALLENGTH,
        ec.EXPOSUREBIASVALUE,
        ec.SHUTTERSPEEDVALUE,
        ec.APERTUREVALUE,
        ec.MAXAPERTUREVALUE,
    ]
    for tag_id in safe_tags:
        if tag_id in exif:
            data = exif[tag_id]
            processed_data = _process_tiff_data_safe(data)
            if processed_data:
                dtype, count, data_value = processed_data
                extra.append((tag_id, dtype, count, data_value, False))

    if ec.INTERCOLORPROFILE in exif:
        icc_profile = exif[ec.INTERCOLORPROFILE]
        if isinstance(icc_profile, bytes):
            extra.append(
                (ec.INTERCOLORPROFILE, 7, len(icc_profile), icc_profile, False)
            )

    for tag_id in special_handling_tags:
        if tag_id in exif:
            data = exif[tag_id]
            processed_data = _process_rational_tag(data)
            if processed_data:
                dtype, count, data_value = processed_data
                extra.append((tag_id, dtype, count, data_value, False))
    for tag_id in exif:
        if tag_id in NO_COPY_TIFF_TAGS_ID:
            continue
        if tag_id in safe_tags or tag_id in special_handling_tags:
            continue
        tag_name = TAGS.get(tag_id, tag_id)
        if tag_name in NO_COPY_TIFF_TAGS:
            continue
        data = exif.get(tag_id)
        if _is_safe_to_write(data):
            processed_data = _process_tiff_data_safe(data)
            if processed_data:
                dtype, count, data_value = processed_data
                extra.append((tag_id, dtype, count, data_value, False))
    extra.sort(key=lambda x: x[0])
    return extra, exif_tags


def _process_tiff_data_safe(data):
    if isinstance(data, IFDRational):
        return _process_rational_tag(data)
    if isinstance(data, (str, bytes)):
        clean_data = clean_data_for_tiff(data)
        if clean_data:
            return 2, len(clean_data) + 1, clean_data
    if isinstance(data, int):
        if 0 <= data <= 65535:
            return 3, 1, data
        return 4, 1, data
    if isinstance(data, float):
        return 11, 1, float(data)  # Use FLOAT only for actual floats
    if hasattr(data, "__iter__") and not isinstance(data, (str, bytes)):
        try:
            if all(isinstance(x, int) for x in data):
                return 3, len(data), tuple(data)  # Use SHORT array for integers
            clean_data = [float(x) for x in data]
            return 12, len(clean_data), tuple(clean_data)  # Use DOUBLE for floats
        except Exception:
            return None
    return None


def write_image_with_exif_data_tif(exif, image, out_filename):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def _write_tiff(temp_filename):
        write_tiff_with_metadata(temp_filename, image_rgb, exif, exif_extra_tags_for_tif)

    def _fallback_tiff(out_filename):
        tifffile.imwrite(out_filename, image_rgb, compression="adobe_deflate")

    safe_write_with_temp(out_filename, _write_tiff, _fallback_tiff)


def _process_rational_tag(data):
    if isinstance(data, IFDRational):
        numerator = data.numerator
        denominator = data.denominator if data.denominator != 0 else 1
        if denominator == 1:
            if 0 <= numerator <= 65535:
                return 3, 1, numerator  # SHORT
            return 4, 1, numerator  # LONG
        if abs(numerator) > 1000000 or abs(denominator) > 1000000:
            return 11, 1, float(data)  # Use FLOAT for very large values
        if numerator < 0:
            return 10, 1, (numerator, denominator)  # SRATIONAL
        return 5, 1, (numerator, denominator)  # RATIONAL
    return None


def _is_safe_to_write(data):
    if data is None:
        return False
    if isinstance(data, bytes) and len(data) > 10000:
        return False
    if hasattr(data, "__iter__") and not isinstance(data, (str, bytes, tuple, list)):
        return False
    return True
