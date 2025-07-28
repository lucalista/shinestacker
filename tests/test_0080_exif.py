import os
import logging
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS
from shinestacker.core.logging import setup_logging
from shinestacker.algorithms.exif import get_exif, copy_exif_from_file_to_file, print_exif, write_image_with_exif_data


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
        logger.info("======== Testing JPG EXIF ======== ")
        logger.info("*** Source JPG EXIF ***")
        exif = copy_exif_from_file_to_file("examples/input/img-jpg/0000.jpg", "examples/input/img-jpg/0001.jpg",
                                           out_filename=out_filename, verbose=True)
        exif_copy = get_exif(out_filename)
        logger.info("*** Copy JPG EXIF ***")
        print_exif(exif_copy)
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
        exif = copy_exif_from_file_to_file("examples/input/img-tif/0000.tif", "examples/input/img-tif/0001.tif",
                                           out_filename=out_filename, verbose=True)
        image = Image.open(out_filename)
        exif_copy = image.tag_v2 if hasattr(image, 'tag_v2') else image.getexif()
        logging.getLogger(__name__).info("*** Copy TIFF EXIF ***")
        print_exif(exif_copy)
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


def test_write_image_with_exif_data():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        XMLPACKET = 700
        IMAGERESOURCES = 34377
        INTERCOLORPROFILE = 34675
        logger.info("======== Testing write_image_with_exif_data (JPG) ========")
        jpg_out_filename = output_dir + "/0001_write_test.jpg"
        exif = get_exif("examples/input/img-jpg/0000.jpg")
        image = Image.open("examples/input/img-jpg/0001.jpg")
        write_image_with_exif_data(exif, np.array(image), jpg_out_filename, verbose=True)
        written_exif = get_exif(jpg_out_filename)
        logger.info("*** Written JPG EXIF ***")
        print_exif(written_exif)
        for tag_id in exif:
            if tag_id not in NO_TEST_JPG_TAGS:
                original_data = exif.get(tag_id)
                written_data = written_exif.get(tag_id)
                # Skip binary data comparison for certain tags
                if tag_id in [XMLPACKET, IMAGERESOURCES, INTERCOLORPROFILE]:
                    continue
                if isinstance(original_data, bytes):
                    try:
                        original_data = original_data.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                        continue  # Skip if we can't decode
                if isinstance(written_data, bytes):
                    try:
                        written_data = written_data.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                        continue  # Skip if we can't decode
                if original_data != written_data:
                    logger.error(f"JPG EXIF data don't match for tag {tag_id}: {original_data} != {written_data}")
                    assert False
        logger.info("======== Testing write_image_with_exif_data (TIFF) ========")
        tiff_out_filename = output_dir + "/0001_write_test.tif"
        exif = get_exif("examples/input/img-tif/0000.tif")
        image = Image.open("examples/input/img-tif/0001.tif")
        if image.mode == 'I;16':
            image_array = np.array(image, dtype=np.uint16)
        elif image.mode == 'RGB':
            if image.getexif().get(258, (8, 8, 8))[0] == 16:
                image_array = np.array(image, dtype=np.uint16)
            else:
                image_array = np.array(image)
        else:
            image_array = np.array(image)
        write_image_with_exif_data(exif, image_array, tiff_out_filename, verbose=True)
        written_image = Image.open(tiff_out_filename)
        written_exif = written_image.tag_v2 if hasattr(written_image, 'tag_v2') else written_image.getexif()
        logger.info("*** Written TIFF EXIF ***")
        print_exif(written_exif)
        TIFF_SKIP_TAGS = [
            258,    # BitsPerSample
            259,    # Compression
            273,    # StripOffsets
            278,    # RowsPerStrip
            279,    # StripByteCounts
            282,    # XResolution
            283,    # YResolution
            296,    # ResolutionUnit
            IMAGERESOURCES,
            INTERCOLORPROFILE,
            XMLPACKET
        ]
        for tag_id in exif:
            if tag_id not in TIFF_SKIP_TAGS:
                original_data = exif.get(tag_id)
                written_data = written_exif.get(tag_id)
                if original_data is None or written_data is None:
                    continue
                if isinstance(original_data, bytes) or isinstance(written_data, bytes):
                    continue
                if hasattr(original_data, 'numerator') and hasattr(written_data, 'numerator'):
                    if float(original_data) != float(written_data):
                        logger.error(f"TIFF EXIF data don't match for tag {tag_id}: {original_data} != {written_data}")
                        assert False
                    continue
                elif hasattr(original_data, 'numerator') or hasattr(written_data, 'numerator'):
                    logger.error(f"TIFF EXIF type mismatch for tag {tag_id}: {type(original_data)} != {type(written_data)}")
                    assert False
                if original_data != written_data:
                    logger.error(f"TIFF EXIF data don't match for tag {tag_id}: {original_data} != {written_data}")
                    assert False
        logger.info("Skipped tags comparison for:")
        for tag_id in TIFF_SKIP_TAGS:
            if tag_id in exif:
                tag_name = TAGS.get(tag_id, tag_id)
                logger.info(f"  {tag_name} (tag {tag_id})")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        assert False


if __name__ == '__main__':
    test_exif_tiff()
    test_exif_jpg()
    test_write_image_with_exif_data()
