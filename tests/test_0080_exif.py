import os
import logging
from PIL import Image
from PIL.ExifTags import TAGS
from focusstack.core.logging import setup_logging
from focusstack.algorithms.exif import get_exif, copy_exif_from_file_to_file, print_exif


NO_TEST_TIFF_TAGS = ["XMLPacket", "Compression", "StripOffsets", "RowsPerStrip", "StripByteCounts", "ImageResources", "ExifOffset", 34665]

NO_TEST_JPG_TAGS = [34665]


def test_exif_jpg():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        out_filename = output_dir + "/0001.jpg"
        ext = out_filename.split(".")[-1]
        logger.info("======== Testing JPG EXIF ======== ")
        logger.info("*** Source JPG EXIF ***")
        exif = copy_exif_from_file_to_file("../examples/input/img-jpg/0000.jpg", "../examples/input/img-jpg/0001.jpg",
                                           out_filename=out_filename, verbose=True)
        exif_copy = get_exif(out_filename)
        logger.info("*** Copy JPG EXIF ***")
        print_exif(exif_copy, ext)
        for tag, tag_copy in zip(exif, exif_copy):
            data, data_copy = exif.get(tag), exif_copy.get(tag_copy)
            if isinstance(data, bytes):
                data = data.decode()
            if isinstance(data_copy, bytes):
                data_copy = data_copy.decode()
            if tag not in NO_TEST_TIFF_TAGS and not (tag == tag_copy and data == data_copy):
                logger.error("JPG EXIF data don't match: {tag} => {data}, {tag_copy} => {data_copy}")
                assert False
    except Exception:
        assert False


def common_entries(*dcts):
    if not dcts:
        return
    for i in set(dcts[0]).intersection(*dcts[1:]):
        yield (i,) + tuple(d[i] for d in dcts)


def test_exif_tiff():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        out_filename = output_dir + "/0001.tif"
        logger.info("======== Testing TIFF EXIF ========")
        logging.getLogger(__name__).info("*** Source TIFF EXIF ***")
        exif = copy_exif_from_file_to_file("../examples/input/img-tif/0000.tif", "../examples/input/img-tif/0001.tif",
                                           out_filename=out_filename, verbose=True)
        image = Image.open(out_filename)
        exif_copy = image.tag_v2 if hasattr(image, 'tag_v2') else image.getexif()
        ext = out_filename.split(".")[-1]
        logging.getLogger(__name__).info("*** Copy TIFF EXIF ***")
        print_exif(exif_copy, ext)
        meta, meta_copy = {}, {}
        for tag_id, tag_id_copy in zip(exif, exif_copy):
            tag = TAGS.get(tag_id, tag_id)
            tag_copy = TAGS.get(tag_id_copy, tag_id_copy)
            data, data_copy = exif.get(tag_id), exif_copy.get(tag_id_copy)
            if isinstance(data, bytes):
                if tag != "ImageResources":
                    try:
                        data = data.decode()
                    except Exception:
                        logger.warning("Test: can't decode EXIF tag {tag:25} [#{tag_id}]")
                        data = '<<< decode error >>>'
            if isinstance(data_copy, bytes):
                data_copy = data_copy.decode()
            meta[tag], meta_copy[tag_copy] = data, data_copy
        for (tag, data, data_copy) in list(common_entries(meta, meta_copy)):
            if tag not in NO_TEST_TIFF_TAGS and not data == data_copy:
                logger.error(f"TIFF EXIF data don't match: {tag}: {data}=>{data_copy}")
                assert False
    except Exception:
        assert False


if __name__ == '__main__':
    test_exif_tiff()
    test_exif_jpg()
