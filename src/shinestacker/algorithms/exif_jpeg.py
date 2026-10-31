# pylint: disable=C0302, W0718, R0911, R0912, E1101, R0914, R0915
import os
import logging
import traceback
import numpy as np
import cv2
from PIL import Image
from PIL.TiffImagePlugin import IFDRational
from .utils import read_img, write_img
from . import exif_constants as ec

COMPATIBLE_TAGS = [
    ec.MAKE, ec.MODEL, ec.SOFTWARE, ec.DATETIME, ec.ARTIST, ec.COPYRIGHT,
    ec.EXPOSURETIME, ec.FNUMBER, ec.ISOSPEEDRATINGS, ec.EXPOSUREPROGRAM,
    ec.SHUTTERSPEEDVALUE, ec.APERTUREVALUE, ec.BRIGHTNESSVALUE, ec.EXPOSUREBIASVALUE,
    ec.MAXAPERTUREVALUE, ec.SUBJECTDISTANCE, ec.METERINGMODE, ec.LIGHTSOURCE, ec.FLASH,
    ec.FOCALLENGTH, ec.EXPOSUREMODE, ec.WHITEBALANCE, ec.EXPOSUREINDEX,
    ec.SCENECAPTURETYPE, ec.DATETIMEORIGINAL, ec.LENSMODEL, ec.LENSMAKE,
    ec.FOCALLENGTHIN35MMFILM, ec.GAINCONTROL, ec.CONTRAST, ec.SATURATION, ec.SHARPNESS,
    ec.CUSTOMRENDERED, ec.DIGITALZOOMRATIO, ec.SUBJECTDISTANCERANGE,
    ec.EXIFVERSION, ec.FLASHPIXVERSION,
    ec.COLORSPACE, ec.PIXELXDIMENSION, ec.PIXELYDIMENSION, ec.IMAGEWIDTH, ec.IMAGELENGTH,
    ec.BITSPERSAMPLE, ec.ORIENTATION, ec.XRESOLUTION, ec.YRESOLUTION, ec.RESOLUTIONUNIT
]


def extract_enclosed_data_for_jpg(data, head, foot):
    xmp_start = data.find(head)
    if xmp_start == -1:
        return None
    xmp_end = data.find(foot, xmp_start)
    if xmp_end == -1:
        return None
    xmp_end += len(foot)
    return data[xmp_start:xmp_end]


def get_exif_from_jpg(image, exif_filename):
    exif_data = image.getexif()
    try:
        exif_subifd = exif_data.get_ifd(ec.EXIFIFD)
        for tag_id, value in exif_subifd.items():
            if tag_id in ec.EXPOSURE_TAGS_MAP:
                exif_data[tag_id] = value
            elif tag_id not in exif_data:
                exif_data[tag_id] = value
    except Exception:
        pass
    if ec.MAKERNOTE in exif_data:
        del exif_data[ec.MAKERNOTE]
    icc_profile = None
    if hasattr(image, 'info') and 'icc_profile' in image.info:
        icc_profile = image.info['icc_profile']
        if icc_profile and len(icc_profile) > 0:
            exif_data[ec.INTERCOLORPROFILE] = icc_profile
    if not icc_profile and ec.INTERCOLORPROFILE in exif_data:
        icc_profile = exif_data[ec.INTERCOLORPROFILE]
    if not icc_profile:
        try:
            with open(exif_filename, 'rb') as f:
                data = f.read()
                icc_profile = extract_icc_from_jpeg(data)
                if icc_profile:
                    exif_data[ec.INTERCOLORPROFILE] = icc_profile
        except Exception:
            pass
    with open(exif_filename, 'rb') as f:
        data = extract_enclosed_data_for_jpg(f.read(), b'<?xpacket', b'<?xpacket end="w"?>')
        if data is not None:
            exif_data[ec.XMLPACKET] = data
    return exif_data


def extract_icc_from_jpeg(jpeg_data):
    pos = 0
    while pos < len(jpeg_data) - 4:
        if jpeg_data[pos:pos + 2] == b'\xff\xe2':  # APP2 marker
            length = int.from_bytes(jpeg_data[pos + 2:pos + 4], 'big')
            if pos + 2 + length <= len(jpeg_data):
                segment = jpeg_data[pos:pos + 2 + length]
                if segment.startswith(b'\xff\xe2') and b'ICC_PROFILE' in segment[:20]:
                    # Extract ICC profile data (skip 2-byte marker, 2-byte length, and ICC header)
                    # ICC profile in APP2 marker has format: "ICC_PROFILE\0<chunk>\0<total>"
                    # Skip marker (2), length (2), and "ICC_PROFILE\0" (12)
                    icc_data = segment[14:]  # Adjust based on actual format
                    return icc_data
                pos += 2 + length
            else:
                break
        elif jpeg_data[pos] == 0xFF:
            marker = jpeg_data[pos + 1]
            if marker == 0xDA:  # Start of scan
                break
            if marker == 0xD9:  # End of image
                break
            if pos + 4 <= len(jpeg_data):
                length = int.from_bytes(jpeg_data[pos + 2:pos + 4], 'big')
                pos += 2 + length
            else:
                break
        else:
            pos += 1
    return None


def add_exif_data_to_jpg_file(exif, in_filename, out_filename, verbose=False):
    if exif is None:
        raise RuntimeError('No exif data provided.')
    xmp_data = exif.get(ec.XMLPACKET) if hasattr(exif, 'get') else None
    if out_filename is None:
        out_filename = in_filename
    use_temp = in_filename == out_filename
    if use_temp:
        temp_filename = out_filename + ".tmp"
        final_filename = temp_filename
    else:
        final_filename = out_filename
    try:
        with Image.open(in_filename) as image:
            jpeg_exif = Image.Exif()
            icc_profile = None
            if ec.INTERCOLORPROFILE in exif:
                icc_profile = exif[ec.INTERCOLORPROFILE]
                if not isinstance(icc_profile, bytes):
                    if isinstance(icc_profile, str):
                        icc_profile = icc_profile.encode('utf-8', errors='ignore')
                    else:
                        icc_profile = None
                        if verbose:
                            print(f"ICC profile is not bytes: {type(icc_profile)}")
            if not icc_profile and hasattr(image, 'info') and 'icc_profile' in image.info:
                icc_profile = image.info['icc_profile']
                if verbose:
                    print(f"Using ICC profile from source image: {len(icc_profile)} bytes")
            for tag_id in COMPATIBLE_TAGS:
                if tag_id in exif:
                    value = exif[tag_id]
                    if tag_id in [ec.ORIENTATION, ec.FLASH] and isinstance(value, float):
                        value = int(value)
                        if verbose:
                            print(f"Converted Orientation from float to int: {value}")
                    elif tag_id == ec.BITSPERSAMPLE and isinstance(value, tuple):
                        jpeg_exif[tag_id] = 8
                        if verbose:
                            print(f"Converted BitsPerSample from {value} to 8 for JPEG")
                        continue
                    try:
                        if tag_id in [ec.EXIFVERSION, ec.FLASHPIXVERSION]:
                            if isinstance(value, str):
                                jpeg_exif[tag_id] = value.encode('ascii')
                            else:
                                jpeg_exif[tag_id] = value
                        elif isinstance(value, tuple) and len(value) == 2:
                            value = IFDRational(value[0], value[1])
                            jpeg_exif[tag_id] = value
                        elif isinstance(value, (int, str, float, IFDRational)):
                            jpeg_exif[tag_id] = value
                        else:
                            if verbose:
                                print(f"Skipping unsupported type for tag {tag_id}: {type(value)}")
                    except Exception as e:
                        if verbose:
                            print(msg=f"Failed to add tag {tag_id}: {e}")
            try:
                if hasattr(jpeg_exif, 'get_ifd'):
                    exif_ifd = jpeg_exif.get_ifd(ec.EXIFIFD)
                    if exif_ifd is None:
                        exif_ifd = {}
                    tags_to_move = [
                        ec.LENSMODEL, ec.EXPOSURETIME, ec.FNUMBER, ec.ISOSPEEDRATINGS,
                        ec.FOCALLENGTH, ec.SHUTTERSPEEDVALUE, ec.APERTUREVALUE,
                        ec.EXPOSUREBIASVALUE]
                    for tag_id in tags_to_move:
                        if tag_id in exif:
                            exif_ifd[tag_id] = exif[tag_id]
                            if tag_id in jpeg_exif:
                                del jpeg_exif[tag_id]
            except Exception as e:
                if verbose:
                    print(f"Failed to move tags to EXIF sub-IFD: {e}")
            exif_bytes = jpeg_exif.tobytes()
            save_kwargs = {"exif": exif_bytes, "quality": 100, "subsampling": 0}
            if icc_profile and isinstance(icc_profile, bytes) and len(icc_profile) > 0:
                try:
                    if icc_profile.startswith(b'\x00') or len(icc_profile) < 128:
                        if verbose:
                            print(f"ICC profile appears invalid: {len(icc_profile)} bytes")
                    else:
                        save_kwargs["icc_profile"] = icc_profile
                        if verbose:
                            print(f"Adding ICC profile to JPEG: {len(icc_profile)} bytes")
                except Exception as e:
                    if verbose:
                        print(f"Failed to prepare ICC profile: {e}")
            image.save(final_filename, "JPEG", **save_kwargs)
            if xmp_data and isinstance(xmp_data, bytes):
                _insert_xmp_into_jpeg(final_filename, xmp_data, verbose)
        if use_temp:
            if os.path.exists(out_filename):
                os.remove(out_filename)
            os.rename(temp_filename, out_filename)
    except Exception as e:
        traceback.print_exc()
        if verbose:
            print(f"Failed to save JPEG with EXIF: {e}")
        if use_temp and os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception:
                traceback.print_exc()
        else:
            try:
                write_img(out_filename, read_img(in_filename))
            except Exception:
                traceback.print_exc()
        raise


def _insert_xmp_into_jpeg(jpeg_path, xmp_data, verbose=False):
    logger = logging.getLogger(__name__)
    with open(jpeg_path, 'rb') as f:
        jpeg_data = f.read()
    soi_pos = jpeg_data.find(b'\xFF\xD8')
    if soi_pos == -1:
        if verbose:
            logger.warning("No SOI marker found, cannot insert XMP")
        return
    insert_pos = soi_pos + 2
    current_pos = insert_pos
    while current_pos < len(jpeg_data) - 4:
        if jpeg_data[current_pos] != 0xFF:
            break
        marker = jpeg_data[current_pos + 1]
        if marker == 0xDA:
            break
        segment_length = int.from_bytes(jpeg_data[current_pos + 2:current_pos + 4], 'big')
        if marker == 0xE1:
            insert_pos = current_pos + 2 + segment_length
            current_pos = insert_pos
            continue
        current_pos += 2 + segment_length
    xmp_identifier = b'http://ns.adobe.com/xap/1.0/\x00'
    xmp_payload = xmp_identifier + xmp_data
    segment_length = len(xmp_payload) + 2
    xmp_segment = b'\xFF\xE1' + segment_length.to_bytes(2, 'big') + xmp_payload
    updated_data = (
        jpeg_data[:insert_pos] +
        xmp_segment +
        jpeg_data[insert_pos:]
    )
    with open(jpeg_path, 'wb') as f:
        f.write(updated_data)
    if verbose:
        logger.info("Successfully inserted XMP data into JPEG")


def write_image_with_exif_data_jpg(exif, image, out_filename, verbose):
    save_img = (image // 256).astype(np.uint8) if image.dtype == np.uint16 else image
    cv2.imwrite(out_filename, save_img, [cv2.IMWRITE_JPEG_QUALITY, 100])
    add_exif_data_to_jpg_file(exif, out_filename, out_filename, verbose)
