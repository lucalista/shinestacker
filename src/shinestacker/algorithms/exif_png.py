# pylint: disable=C0302, W0718, R0911, R0912
import numpy as np
import cv2
from PIL import Image
from PIL.ExifTags import TAGS
from PIL.PngImagePlugin import PngInfo
from PIL.TiffImagePlugin import IFDRational
from .utils import write_img
from . import exif_constants as ec
from .exif_common import parse_xmp_to_exif, safe_write_with_temp


PNG_TAG_MAP = {
    'EXIF_CameraMake': ec.MAKE,
    'EXIF_CameraModel': ec.MODEL,
    'EXIF_Software': ec.SOFTWARE,
    'EXIF_DateTime': ec.DATETIME,
    'EXIF_Artist': ec.ARTIST,
    'EXIF_Copyright': ec.COPYRIGHT,
    'EXIF_ExposureTime': ec.EXPOSURETIME,
    'EXIF_FNumber': ec.FNUMBER,
    'EXIF_ISOSpeedRatings': ec.ISOSPEEDRATINGS,
    'EXIF_ShutterSpeedValue': ec.SHUTTERSPEEDVALUE,
    'EXIF_ApertureValue': ec.APERTUREVALUE,
    'EXIF_FocalLength': ec.FOCALLENGTH,
    'EXIF_LensModel': ec.LENSMODEL,
    'EXIF_ExposureBiasValue': ec.EXPOSUREBIASVALUE,
    'EXIF_MaxApertureValue': ec.MAXAPERTUREVALUE,
    'EXIF_MeteringMode': ec.METERINGMODE,
    'EXIF_Flash': ec.FLASH,
    'EXIF_WhiteBalance': ec.WHITEBALANCE,
    'EXIF_ExposureMode': ec.EXPOSUREMODE,
    'EXIF_SceneCaptureType': ec.SCENECAPTURETYPE,
    'EXIF_DateTimeOriginal': ec.DATETIMEORIGINAL
}


def get_exif_from_png(image):
    exif_data = {}
    exif_from_image = image.getexif()
    if exif_from_image:
        exif_data.update(dict(exif_from_image))
    for attr_name in ['text', 'info']:
        if hasattr(image, attr_name) and getattr(image, attr_name):
            for key, value in getattr(image, attr_name).items():
                if attr_name == 'info' and key in ['dpi', 'gamma']:
                    continue
                exif_data[f"PNG_{key}"] = value
    return exif_data


def parse_typed_png_text(value):
    if isinstance(value, str):
        if value.startswith('RATIONAL:'):
            parts = value[9:].split('/')
            if len(parts) == 2:
                try:
                    return IFDRational(int(parts[0]), int(parts[1]))
                except (ValueError, ZeroDivisionError):
                    return value[9:]
        elif value.startswith('INT:'):
            try:
                return int(value[4:])
            except ValueError:
                return value[4:]
        elif value.startswith('FLOAT:'):
            try:
                return float(value[6:])
            except ValueError:
                return value[6:]
        elif value.startswith('STRING:'):
            return value[7:]
        elif value.startswith('BYTES:'):
            return value[6:].encode('utf-8')
        elif value.startswith('ARRAY:'):
            return [x.strip() for x in value[6:].split(',')]
    return value


def get_enhanced_exif_from_png(image):
    basic_exif = get_exif_from_png(image)
    enhanced_exif = {}
    enhanced_exif.update(basic_exif)
    xmp_data = None
    if hasattr(image, 'text') and image.text:
        xmp_data = image.text.get('XML:com.adobe.xmp') or image.text.get('xml:com.adobe.xmp')
    if not xmp_data and ec.XMLPACKET in basic_exif:
        xmp_data = basic_exif[ec.XMLPACKET]
    if xmp_data:
        enhanced_exif.update(parse_xmp_to_exif(xmp_data))
    if hasattr(image, 'text') and image.text:
        for key, value in image.text.items():
            if key.startswith('EXIF_'):
                parsed_value = parse_typed_png_text(value)
                tag_id = PNG_TAG_MAP.get(key)
                if tag_id:
                    enhanced_exif[tag_id] = parsed_value
    if ec.MAKERNOTE in enhanced_exif:
        del enhanced_exif[ec.MAKERNOTE]
    return {k: v for k, v in enhanced_exif.items() if isinstance(k, int)}


def write_image_with_exif_data_png(exif, image, out_filename, color_order='auto'):
    if isinstance(image, np.ndarray) and image.dtype == np.uint16:
        write_img(out_filename, image)
        return

    def _write_png(temp_filename):
        pil_image = _convert_to_pil_image(image, color_order)
        pnginfo, icc_profile = _prepare_png_metadata(exif)
        save_args = {'format': 'PNG', 'pnginfo': pnginfo}
        if icc_profile:
            save_args['icc_profile'] = icc_profile
        pil_image.save(temp_filename, **save_args)

    def _fallback_png(out_filename):
        write_img(out_filename, image)

    safe_write_with_temp(out_filename, _write_png, _fallback_png)


def _prepare_png_metadata(exif):
    pnginfo = PngInfo()
    icc_profile = None
    xmp_data = _extract_xmp_data(exif)
    if xmp_data:
        pnginfo.add_text("XML:com.adobe.xmp", xmp_data)
    _add_exif_tags_to_pnginfo(exif, pnginfo)
    icc_profile = _extract_icc_profile(exif)
    return pnginfo, icc_profile


def _extract_icc_profile(exif):
    if ec.INTERCOLORPROFILE in exif and isinstance(exif[ec.INTERCOLORPROFILE], bytes):
        return exif[ec.INTERCOLORPROFILE]
    for key, value in exif.items():
        if isinstance(key, str) and isinstance(value, bytes):
            if 'icc' in key.lower() or 'profile' in key.lower():
                return value
    return None


def _add_exif_tags_to_pnginfo(exif, pnginfo):
    for tag_id, value in exif.items():
        if value is None:
            continue
        if isinstance(tag_id, int):
            if tag_id in ec.CAMERA_TAGS_MAP:
                _add_typed_tag(pnginfo, f"EXIF_{ec.CAMERA_TAGS_MAP[tag_id]}", value)
            elif tag_id in ec.EXPOSURE_TAGS_MAP:
                _add_typed_tag(pnginfo, f"EXIF_{ec.EXPOSURE_TAGS_MAP[tag_id]}", value)
            else:
                _add_exif_tag(pnginfo, tag_id, value)
        elif isinstance(tag_id, str) and not tag_id.lower().startswith(('xmp', 'xml')):
            _add_png_text_tag(pnginfo, tag_id, value)


def _add_png_text_tag(pnginfo, key, value):
    try:
        clean_key = key[4:] if key.startswith('PNG_') else key
        if 'icc' in clean_key.lower() or 'profile' in clean_key.lower():
            return
        if isinstance(value, bytes):
            try:
                decoded_value = value.decode('utf-8', errors='replace')
                pnginfo.add_text(clean_key, decoded_value)
            except Exception:
                truncated_value = str(value)[:100] + "..."
                pnginfo.add_text(clean_key, truncated_value)
        else:
            pnginfo.add_text(clean_key, str(value))
    except Exception:
        pass


def _add_exif_tag(pnginfo, tag_id, value):
    try:
        tag_name = TAGS.get(tag_id, f"Unknown_{tag_id}")
        if isinstance(value, bytes) and len(value) > 1000:
            return
        if isinstance(value, (int, float, str)):
            pnginfo.add_text(tag_name, str(value))
        elif isinstance(value, bytes):
            try:
                decoded_value = value.decode('utf-8', errors='replace')
                pnginfo.add_text(tag_name, decoded_value)
            except Exception:
                pass
        elif hasattr(value, 'numerator'):
            rational_str = f"{value.numerator}/{value.denominator}"
            pnginfo.add_text(tag_name, rational_str)
        else:
            pnginfo.add_text(tag_name, str(value))
    except Exception:
        pass


def _add_typed_tag(pnginfo, key, value):
    try:
        if hasattr(value, 'numerator'):
            stored_value = f"RATIONAL:{value.numerator}/{value.denominator}"
        elif isinstance(value, bytes):
            try:
                stored_value = f"STRING:{value.decode('utf-8', errors='replace')}"
            except Exception:
                stored_value = f"BYTES:{str(value)[:100]}"
        elif isinstance(value, (list, tuple)):
            stored_value = f"ARRAY:{','.join(str(x) for x in value)}"
        elif isinstance(value, int):
            stored_value = f"INT:{value}"
        elif isinstance(value, float):
            stored_value = f"FLOAT:{value}"
        else:
            stored_value = f"STRING:{str(value)}"
        pnginfo.add_text(key, stored_value)
    except Exception:
        pass


def _extract_xmp_data(exif):
    for key, value in exif.items():
        if isinstance(key, str) and ('xmp' in key.lower() or 'xml' in key.lower()):
            if isinstance(value, bytes):
                return value.decode('utf-8', errors='ignore')
            if isinstance(value, str):
                return value
    return create_xmp_from_exif(exif)


def create_xmp_from_exif(exif_data):
    xmp_elements = []
    if exif_data:
        for tag_id, value in exif_data.items():
            if isinstance(tag_id, int) and value and tag_id in ec.XMP_TAG_MAP:
                config = ec.XMP_TAG_MAP[tag_id]
                processed_value = config['processor'](value) if config['processor'] else value
                if config['type'] == 'simple':
                    xmp_elements.append(
                        f'<{config["format"]}>{processed_value}</{config["format"]}>')
                elif config['type'] == 'rdf_alt':
                    xmp_elements.append(
                        f'<{config["format"]}><rdf:Alt>'
                        f'<rdf:li xml:lang="x-default">{processed_value}</rdf:li>'
                        f'</rdf:Alt></{config["format"]}>')
                elif config['type'] == 'rdf_seq':
                    xmp_elements.append(
                        f'<{config["format"]}><rdf:Seq>'
                        f'<rdf:li>{processed_value}</rdf:li>'
                        f'</rdf:Seq></{config["format"]}>')
                elif config['type'] == 'datetime':
                    if ':' in processed_value:
                        processed_value = processed_value.replace(':', '-', 2).replace(' ', 'T')
                    xmp_elements.append(
                        f'<{config["format"]}>{processed_value}</{config["format"]}>')
                elif config['type'] == 'rational':
                    float_value = float(value) \
                        if hasattr(value, 'numerator') \
                        else (float(value) if value else 0)
                    xmp_elements.append(
                        f'<{config["format"]}>{float_value}</{config["format"]}>')
                elif config['type'] == 'mapped':
                    mapped_value = config['map'].get(value, str(value))
                    xmp_elements.append(
                        f'<{config["format"]}>{mapped_value}</{config["format"]}>')
    if xmp_elements:
        xmp_content = '\n    '.join(xmp_elements)
        return ec.XMP_TEMPLATE.format(content=xmp_content)
    return ec.XMP_EMPTY_TEMPLATE


def _convert_to_pil_image(image, color_order):
    if isinstance(image, np.ndarray) and len(image.shape) == 3 and image.shape[2] == 3:
        if color_order in ['auto', 'bgr']:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            return Image.fromarray(image_rgb)
    return Image.fromarray(image) if isinstance(image, np.ndarray) else image
