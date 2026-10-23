# pylint: disable=C0114, C0116, C0302, W0718, R0911, R0912, E1101
import os
import re
import tifffile
import tifftools
from PIL.TiffImagePlugin import IFDRational
from ..config.constants import constants
from . import exif_constants as ec


def parse_xmp_to_exif(xmp_data):
    exif_data = {}
    if not xmp_data:
        return exif_data
    if isinstance(xmp_data, bytes):
        xmp_data = xmp_data.decode('utf-8', errors='ignore')
    for xmp_tag, exif_tag in ec.XMP_TO_EXIF_MAP.items():
        attr_pattern = f'{xmp_tag}="([^"]*)"'
        attr_matches = re.findall(attr_pattern, xmp_data)
        for value in attr_matches:
            if value:
                exif_data[exif_tag] = _parse_xmp_value(exif_tag, value)
        start_tag = f'<{xmp_tag}>'
        end_tag = f'</{xmp_tag}>'
        if start_tag in xmp_data:
            start = xmp_data.find(start_tag) + len(start_tag)
            end = xmp_data.find(end_tag, start)
            if end != -1:
                value = xmp_data[start:end].strip()
                if value:
                    exif_data[exif_tag] = _parse_xmp_value(exif_tag, value)
    return exif_data


def _parse_xmp_value(exif_tag, value):
    if exif_tag in [ec.EXPOSURETIME, ec.FNUMBER, ec.FOCALLENGTH]:
        if '/' in value:
            num, den = value.split('/')
            try:
                return IFDRational(int(num), int(den))
            except (ValueError, ZeroDivisionError):
                try:
                    return float(value) if value else 0.0
                except ValueError:
                    return 0.0
        return float(value) if value else 0.0
    if exif_tag == ec.ISOSPEEDRATINGS:  # ISO
        if '<rdf:li>' in value:
            matches = re.findall(r'<rdf:li>([^<]+)</rdf:li>', value)
            if matches:
                value = matches[0]
        try:
            return int(value)
        except ValueError:
            return value
    if exif_tag in [ec.DATETIME, ec.DATETIMEORIGINAL]:  # DateTime and DateTimeOriginal
        if 'T' in value:
            value = value.replace('T', ' ').replace('-', ':')
        return value
    return value


def safe_write_with_temp(out_filename, write_func, fallback_func=None):
    temp_filename = out_filename + ".tmp"
    try:
        write_func(temp_filename)
        if os.path.exists(out_filename):
            os.remove(out_filename)
        os.rename(temp_filename, out_filename)
    except Exception:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception:
                pass
        if fallback_func:
            fallback_func(out_filename)
        raise


def write_tiff_with_metadata(filename, image, exif, exif_extra_tags):
    metadata = {
        "description": f"image generated with {constants.APP_STRING} package"
    }
    extra_tags, exif_tags = exif_extra_tags(exif)
    write_tiff_with_exif(
        filename,
        image,
        extra_tags,
        metadata=metadata,
        compression="adobe_deflate",
        **exif_tags,
    )


# Tags of the Exif private IFD (Exif 2.32, section 4.6.5). In a TIFF file they
# belong in the IFD that tag 34665 points to, not in the image's own IFD, where
# libtiff (and so OpenCV) reports them as unknown fields.
EXIF_IFD_TAG_RANGES = ((33434, 33437), (34850, 34867), (36864, 37530), (40960, 42240))


def is_exif_ifd_tag(tag_id):
    return any(lo <= tag_id <= hi for lo, hi in EXIF_IFD_TAG_RANGES)


def split_exif_ifd_tags(extra_tags):
    """tifffile extratags -> (tags for the image IFD, tags for the Exif IFD)."""
    image_tags = [t for t in extra_tags if not is_exif_ifd_tag(t[0]) and t[0] != ec.EXIFIFD]
    exif_tags = [t for t in extra_tags if is_exif_ifd_tag(t[0])]
    return image_tags, exif_tags


def _tifftools_entry(dtype, value):
    """A tifffile extratags value as a tifftools tag entry."""
    if dtype == 2:
        data = value.decode("latin-1") if isinstance(value, bytes) else str(value)
    elif dtype == 7:
        data = value if isinstance(value, bytes) else str(value).encode("latin-1", "replace")
    elif dtype in (5, 10):
        pairs = value if isinstance(value[0], (tuple, list)) else [value]
        data = [int(v) for pair in pairs for v in pair]
    else:
        data = list(value) if isinstance(value, (tuple, list)) else [value]
    return {"datatype": tifftools.Datatype[dtype], "data": data}


def write_tiff_with_exif(filename, image, extra_tags, **kwargs):
    """tifffile.imwrite() with the Exif tags in an Exif IFD (tag 34665), which
    tifffile cannot write: tifftools rewrites the file with that IFD added,
    copying the image data unchanged."""
    image_tags, exif_tags = split_exif_ifd_tags(extra_tags)
    if not exif_tags:
        tifffile.imwrite(filename, image, extratags=image_tags, **kwargs)
        return
    plain = filename + ".noexif"
    tifffile.imwrite(plain, image, extratags=image_tags, **kwargs)
    try:
        info = tifftools.read_tiff(plain)
        info["ifds"][0]["tags"][tifftools.Tag.EXIFIFD.value] = {
            "datatype": tifftools.Datatype.IFD,
            "ifds": [[{"tags": {tag_id: _tifftools_entry(dtype, value)
                                for tag_id, dtype, _count, value, _ in exif_tags}}]]}
        tifftools.write_tiff(info, filename, allowExisting=True)
    finally:
        os.remove(plain)
