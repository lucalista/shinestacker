import os
import logging
import numpy as np
import cv2
from PIL import Image
from PIL.ExifTags import TAGS
from PIL.PngImagePlugin import PngInfo
from shinestacker.core.logging import setup_logging
from shinestacker.algorithms.utils import read_img
from shinestacker.algorithms.exif import (
    get_exif, copy_exif_from_file_to_file, print_exif, write_image_with_exif_data,
    save_exif_data, exif_dict, IFDRational)
from shinestacker.algorithms.exif_common import _parse_xmp_value, parse_xmp_to_exif
from shinestacker.algorithms.exif_tiff import (
    clean_data_for_tiff, _process_tiff_data_safe, write_image_with_exif_data_tif,
    exif_extra_tags_for_tif, NO_COPY_TIFF_TAGS_ID)
from shinestacker.algorithms.exif_jpeg import (
    add_exif_data_to_jpg_file, _insert_xmp_into_jpeg, extract_enclosed_data_for_jpg)
from shinestacker.algorithms.exif_png import (
    write_image_with_exif_data_png, get_enhanced_exif_from_png, get_exif_from_png,
    parse_typed_png_text)
from shinestacker.algorithms.exif_constants import safe_decode_bytes

NO_TEST_TIFF_TAGS = [
    "XMLPacket", "Compression", "StripOffsets", "RowsPerStrip", "StripByteCounts",
    "ImageResources", "ExifOffset", 34665, "IPTCNAA", 33723, "InterColorProfile"]

NO_TEST_JPG_TAGS = [34665]


def test_exif_jpg():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        out_filename = output_dir + "/0001.jpg"
        SKIP_TAGS = [
            256,  # IMAGEWIDTH
            257,  # IMAGELENGTH
            258,  # BITSPERSAMPLE
            259,  # COMPRESSION
            262,  # PHOTOMETRICINTERPRETATION
            273,  # STRIPOFFSETS
            277,  # SAMPLESPERPIXEL
            278,  # ROWSPERSTRIP
            279,  # STRIPBYTECOUNTS
            284,  # PLANARCONFIGURATION
            34665,  # EDIFID,
            34675,  # INTERCOLORPROFILE
        ]
        logger.info("======== Testing JPG EXIF ======== ")
        logger.info("*** Source JPG EXIF ***")
        exif = copy_exif_from_file_to_file(
            "examples/input/img-jpg/0000.jpg", "examples/input/img-jpg/0001.jpg",
            out_filename=out_filename, verbose=True)
        exif_copy = get_exif(out_filename)
        logger.info("*** Copy JPG EXIF ***")
        print_exif(exif_copy)
        all_tags = set(exif.keys()) | set(exif_copy.keys())
        mismatches = []
        for tag in all_tags:
            if tag in SKIP_TAGS:
                continue
            data_orig = exif.get(tag)
            data_copy = exif_copy.get(tag)
            if tag == 34675:  # INTERCOLORPROFILE
                if data_orig is None and data_copy is None:
                    continue  # Both None is OK
                elif data_orig is not None and data_copy is not None:
                    if data_orig != data_copy:
                        orig_preview = data_orig[:100].hex()[:50]
                        copy_preview = data_copy[:100].hex()[:50]
                        mismatches.append(
                            f"Tag {tag} (ICC profile): data mismatch "
                            f"({len(data_orig)} bytes vs {len(data_copy)} bytes) "
                            f"start: {orig_preview}... vs {copy_preview}..."
                        )
                elif data_orig is not None:
                    mismatches.append(
                        f"Tag {tag} missing in copy (ICC profile: {len(data_orig)} bytes)")
                else:
                    mismatches.append(
                        f"Tag {tag} added in copy (ICC profile: {len(data_copy)} bytes)")
                continue
            if isinstance(data_orig, bytes):
                data_orig = safe_decode_bytes(data_orig)
            if isinstance(data_copy, bytes):
                data_copy = safe_decode_bytes(data_copy)
            if tag in exif and tag in exif_copy:
                if data_orig != data_copy:
                    mismatches.append(f"Tag {tag}: {data_orig} vs {data_copy}")
            elif tag in exif and tag not in exif_copy:
                mismatches.append(f"Tag {tag} missing in copy (was: {data_orig})")
            elif tag not in exif and tag in exif_copy:
                mismatches.append(f"Tag {tag} added in copy (value: {data_copy})")
        if mismatches:
            for mismatch in mismatches:
                logger.error(mismatch)
            assert False, f"Found {len(mismatches)} EXIF mismatches"
    except Exception as e:
        logger.error(f"JPG EXIF test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
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
        exif = copy_exif_from_file_to_file(
            "examples/input/img-tif/0000.tif", "examples/input/img-tif/0001.tif",
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
                        assert False
            if isinstance(data_copy, bytes) and tag_copy != "InterColorProfile":
                data_copy = data_copy.decode()
            meta[tag], meta_copy[tag_copy] = data, data_copy
        for (tag, data, data_copy) in list(common_entries(meta, meta_copy)):
            if tag not in NO_TEST_TIFF_TAGS and not data == data_copy:
                if tag in ["XResolution", "YResolution"]:
                    try:
                        if float(data) == float(data_copy):
                            continue
                    except Exception:
                        pass
                logger.error(f"TIFF EXIF data don't match: {tag}: {data}=>{data_copy}")
                assert False
    except Exception:
        assert False


def test_exif_png():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        out_filename = output_dir + "/0001.png"
        logger.info("======== Testing PNG EXIF ========")
        png_file = "examples/input/img-png-8/0000.png"
        if os.path.exists(png_file):
            logger.info("*** Source PNG EXIF ***")
            exif = get_exif(png_file)
            print_exif(exif)
            logger.info("*** Writing PNG with EXIF ***")
            image = Image.open(png_file)
            image_array = np.array(image)
            write_image_with_exif_data(
                exif, image_array, out_filename, verbose=True, color_order='rgb')
            logger.info("*** Written PNG EXIF ***")
            exif_copy = get_exif(out_filename)
            print_exif(exif_copy)
            if exif_copy:
                logger.info("PNG metadata test passed - found metadata in output file")
            else:
                logger.warning("No metadata found in PNG output file (this may be normal)")
            assert os.path.exists(out_filename), "Output PNG file was not created"
            test_img = Image.open(out_filename)
            test_img.verify()
            test_img.close()
        else:
            logger.warning("Test PNG file not found, skipping PNG EXIF test")
            assert False
    except Exception as e:
        logger.error(f"PNG EXIF test failed: {str(e)}")
        assert False


def test_write_image_with_exif_data_jpg():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        SKIP_TAGS = [
            700,  # XMLPACKET
            34377,  # IMAGERESOURCES
            34675,  # INTERCOLORPROFILE
            256,  # IMAGEWIDTH
            257,  # IMAGELENGTH
            258,  # BITSPERSAMPLE
            259,  # COMPRESSION
            262,  # PHOTOMETRICINTERPRETATION
            273,  # STRIPOFFSETS
            277,  # SAMPLESPERPIXEL
            278,  # ROWSPERSTRIP
            279,  # STRIPBYTECOUNTS
            284,  # PLANARCONFIGURATION
            322,  # TILEWIDTH
            323,  # TILELENGTH
            324,  # TILEOFFSETS
            325,  # TILEBYTECOUNTS
            317,  # PREDICTOR
            318,  # WHITEPOINT
            319,  # PRIMARYCHROMATICITIES
            320,  # COLORMAP
            41486,  # FOCALPLANEXRESOLUTION
            41487,  # FOCALPLANEYRESOLUTION
            41488,  # FOCALPLANERESOLUTIONUNIT
            34665,  # EDIFID
        ]
        logger.info("======== Testing write_image_with_exif_data (JPG) ========")
        jpg_out_filename = output_dir + "/0001_write_test.jpg"
        exif = get_exif("examples/input/img-jpg/0000.jpg")
        image = read_img("examples/input/img-jpg/0001.jpg")
        write_image_with_exif_data(exif, image, jpg_out_filename, verbose=True)
        written_exif = get_exif(jpg_out_filename)
        logger.info("*** Written JPG EXIF ***")
        print_exif(written_exif)
        for tag_id in exif:
            if tag_id not in SKIP_TAGS:
                original_data = exif.get(tag_id)
                written_data = written_exif.get(tag_id)
                if isinstance(original_data, bytes):
                    try:
                        original_data = original_data.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                        continue
                if isinstance(written_data, bytes):
                    try:
                        written_data = written_data.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                        continue
                if original_data != written_data:
                    logger.error(
                        f"JPG EXIF data don't match for tag {tag_id}: "
                        f"{original_data} != {written_data}")
                    assert False
        logger.info("JPG write test passed successfully")
    except Exception as e:
        logger.error(f"JPG write test failed: {str(e)}")
        assert False


def test_write_image_with_exif_data_tiff():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        XMLPACKET = 700
        IMAGERESOURCES = 34377
        INTERCOLORPROFILE = 34675
        logger.info("======== Testing write_image_with_exif_data (TIFF) ========")
        tiff_out_filename = output_dir + "/0001_write_test.tif"
        exif = get_exif("examples/input/img-tif/0000.tif")
        image = read_img("examples/input/img-tif/0001.tif")
        write_image_with_exif_data(exif, image, tiff_out_filename, verbose=True)
        written_image = Image.open(tiff_out_filename)
        written_exif = written_image.tag_v2 \
            if hasattr(written_image, 'tag_v2') else \
            written_image.getexif()
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
            305,    # Software - changed to constants.APP_TITLE
            IMAGERESOURCES,
            INTERCOLORPROFILE,
            XMLPACKET,
            34665,  # ExifIFD: an offset within the file
        ]

        def values_equal(v1, v2):
            if v1 == v2:
                return True
            try:
                return float(v1) == float(v2)
            except (TypeError, ValueError):
                return False

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
                        logger.error(
                            f"TIFF EXIF data don't match for tag {tag_id}: "
                            f"{original_data} != {written_data}")
                        assert False
                    continue
                elif hasattr(original_data, 'numerator') or hasattr(written_data, 'numerator'):
                    try:
                        if float(original_data) != float(written_data):
                            logger.error(
                                f"TIFF EXIF data don't match for tag {tag_id}: "
                                f"{original_data} != {written_data}")
                            assert False
                        continue
                    except (TypeError, ValueError):
                        logger.error(
                            f"TIFF EXIF type mismatch for tag {tag_id}: "
                            f"{type(original_data)} != {type(written_data)}")
                        assert False
                if not values_equal(original_data, written_data):
                    logger.error(
                        f"TIFF EXIF data don't match for tag {tag_id}: "
                        f"{original_data} != {written_data}")
                    assert False
        logger.info("Skipped tags comparison for:")
        for tag_id in TIFF_SKIP_TAGS:
            if tag_id in exif:
                tag_name = TAGS.get(tag_id, tag_id)
                logger.info(f"  {tag_name} (tag {tag_id})")
        logger.info("TIFF write test passed successfully")
    except Exception as e:
        logger.error(f"TIFF write test failed: {str(e)}")
        assert False


def test_write_image_with_exif_data_png():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing write_image_with_exif_data (PNG) ========")
        png_out_filename = output_dir + "/0001_write_test.png"
        png_file = "examples/input/img-png-8/0000.png"
        if not os.path.exists(png_file):
            logger.warning("Test PNG file not found, skipping PNG write test")
            assert False
        exif = get_exif(png_file)
        logger.info("*** Source PNG EXIF ***")
        print_exif(exif)
        image_array = read_img(png_file)
        write_image_with_exif_data(exif, image_array, png_out_filename, verbose=True)
        logger.info("*** Verifying PNG file integrity ***")
        try:
            with Image.open(png_out_filename) as verify_img:
                verify_img.verify()
            logger.info("✓ PNG file verification passed")
        except Exception as e:
            logger.error(f"PNG verification failed: {e}")
            assert False, "PNG file verification failed"
        logger.info("*** Checking written PNG metadata with PIL ***")
        with Image.open(png_out_filename) as written_img:
            if hasattr(written_img, 'text') and written_img.text:
                logger.info("Written PNG text chunks (PIL):")
                for key, value in written_img.text.items():
                    logger.info(f"  {key}: {str(value)[:100]}...")
                    if 'xmp' in key.lower():
                        logger.info("✓ Found XMP metadata in written PNG!")
            else:
                logger.info("No text chunks found in written PNG (PIL)")
        logger.info("*** Checking written PNG metadata with get_exif ***")
        written_exif = get_exif(png_out_filename)
        if written_exif:
            logger.info("Written PNG EXIF (get_exif):")
            print_exif(written_exif)
        else:
            logger.info("No EXIF found in written PNG (get_exif)")
        logger.info("PNG write test completed successfully")
    except Exception as e:
        logger.error(f"PNG write test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_get_exif_from_png_with_metadata():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing get_exif_from_png with metadata ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        test_png = output_dir + "/test_metadata.png"
        img = Image.new('RGB', (100, 100), color='red')
        pnginfo = PngInfo()
        pnginfo.add_text("Title", "Test Image")
        pnginfo.add_text("Author", "Test Author")
        pnginfo.add_text("Description", "A test image for metadata")
        pnginfo.add_text("Software", "Test Software")
        img.save(test_png, pnginfo=pnginfo)
        exif = get_exif(test_png)
        logger.info("*** PNG Metadata extracted ***")
        print_exif(exif)
        assert exif is not None, "Should extract metadata from PNG"
        logger.info("✓ PNG metadata extraction test passed")
    except Exception as e:
        logger.error(f"PNG metadata test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_extract_enclosed_data_for_jpg():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing extract_enclosed_data_for_jpg ========")
        test_data = b'Some header data <?xpacket begin="test"?>' \
                    b'XMP content here<?xpacket end="w"?> trailer data'
        result = extract_enclosed_data_for_jpg(test_data, b'<?xpacket', b'<?xpacket end="w"?>')
        assert result is not None, "Should extract XMP data"
        assert b'XMP content here' in result, "Should contain the XMP content"
        logger.info("✓ Valid XMP extraction test passed")
        test_data = b'Just some regular data without XMP'
        result = extract_enclosed_data_for_jpg(test_data, b'<?xpacket', b'<?xpacket end="w"?>')
        assert result is None, "Should return None when no XMP found"
        logger.info("✓ No XMP data test passed")
        test_data = b'Data with <?xpacket begin but no end'
        result = extract_enclosed_data_for_jpg(test_data, b'<?xpacket', b'<?xpacket end="w"?>')
        assert result is None, "Should return None when only start marker found"
        logger.info("✓ Partial XMP data test passed")
        logger.info("All extract_enclosed_data_for_jpg tests passed")
    except Exception as e:
        logger.error(f"XMP extraction test failed: {str(e)}")
        assert False


def test_exif_extra_tags_for_tif():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing exif_extra_tags_for_tif ========")
        test_exif = {
            256: 1000,
            257: 2000,
            282: IFDRational(72, 1),
            283: IFDRational(72, 1),
            296: 2,
            305: b'Test Software',
            270: 'Test Image Description',
            271: 'Test Camera Make',
            272: 'Test Camera Model',
            306: '2023:01:01 12:00:00',
            33432: 'Test Copyright',
            700: b'Test XML data',
        }
        extra_tags, exif_tags = exif_extra_tags_for_tif(test_exif)
        logger.info(f"Generated {len(extra_tags)} extra tags")
        logger.info(f"EXIF tags: {exif_tags}")
        assert 'resolution' in exif_tags
        assert 'resolutionunit' in exif_tags
        assert 'software' in exif_tags
        assert 'photometric' in exif_tags
        res_x, res_y = exif_tags['resolution']
        assert isinstance(res_x, tuple) and len(res_x) == 2
        assert isinstance(res_y, tuple) and len(res_y) == 2
        included_tags = [270, 271, 272, 306, 33432]
        found_tags = [tag_id for tag_id, dtype, count, value, write_once in extra_tags]
        for tag_id in included_tags:
            assert tag_id in found_tags, f"Tag {tag_id} should be included but was not found"
        logger.info("✓ exif_extra_tags_for_tif test passed")
    except Exception as e:
        logger.error(f"exif_extra_tags_for_tif test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_write_image_with_exif_data_png_edge_cases():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing PNG EXIF edge cases ========")
        empty_exif = {}
        test_img = np.ones((50, 50, 3), dtype=np.uint8) * 128
        out_file = output_dir + "/test_empty_exif.png"
        write_image_with_exif_data(empty_exif, test_img, out_file, verbose=True)
        assert os.path.exists(out_file), "Should create file with empty EXIF"
        logger.info("✓ Empty EXIF test passed")
        special_exif = {
            270: 'Test with special chars: ñáéíóú',
            305: 'Test Software v1.0',
            315: 'Test Artist',
        }
        out_file2 = output_dir + "/test_special_chars.png"
        write_image_with_exif_data(special_exif, test_img, out_file2, verbose=True)
        assert os.path.exists(out_file2), "Should create file with special chars"
        logger.info("✓ Special characters test passed")
        long_exif = {
            270: 'A' * 500,
            305: 'B' * 200,
        }
        out_file3 = output_dir + "/test_long_values.png"
        write_image_with_exif_data(long_exif, test_img, out_file3, verbose=True)
        assert os.path.exists(out_file3), "Should create file with long values"
        logger.info("✓ Long values test passed")
        logger.info("All PNG edge case tests passed")
    except Exception as e:
        logger.error(f"PNG edge cases test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_save_exif_data_different_formats():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing save_exif_data with different formats ========")
        source_file = "examples/input/img-jpg/0000.jpg"
        if not os.path.exists(source_file):
            logger.warning("Source file not found, skipping test")
            assert False
        exif = get_exif(source_file)
        jpg_out = output_dir + "/test_save_exif.jpg"
        if os.path.exists("examples/input/img-jpg/0001.jpg"):
            save_exif_data(exif, "examples/input/img-jpg/0001.jpg", jpg_out, verbose=True)
            assert os.path.exists(jpg_out), "Should save JPG with EXIF"
            logger.info("✓ JPG save_exif_data test passed")
        tiff_out = output_dir + "/test_save_exif.tif"
        if os.path.exists("examples/input/img-tif/0001.tif"):
            save_exif_data(exif, "examples/input/img-tif/0001.tif", tiff_out, verbose=True)
            assert os.path.exists(tiff_out), "Should save TIFF with EXIF"
            logger.info("✓ TIFF save_exif_data test passed")
        png_out = output_dir + "/test_save_exif.png"
        if os.path.exists("examples/input/img-png-8/0000.png"):
            save_exif_data(exif, "examples/input/img-png-8/0000.png", png_out, verbose=True)
            assert os.path.exists(png_out), "Should save PNG with EXIF"
            logger.info("✓ PNG save_exif_data test passed")
        logger.info("All save_exif_data format tests passed")
    except Exception as e:
        logger.error(f"save_exif_data test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_exif_dict_functionality():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing exif_dict functionality ========")
        result_none = exif_dict(None)
        assert result_none is None, "Should return None for None input"
        logger.info("✓ exif_dict with None input test passed")
        logger.info("All exif_dict functionality tests passed")
    except Exception as e:
        logger.error(f"exif_dict test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_error_handling():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing error handling ========")
        try:
            get_exif("non_existent_file.jpg")
            assert False, "Should raise exception for non-existent file"
        except RuntimeError as e:
            assert "File does not exist" in str(e)
            logger.info("✓ Non-existent file error handling works")
        try:
            copy_exif_from_file_to_file("non_existent.jpg", "examples/input/img-jpg/0001.jpg")
            assert False, "Should raise exception for non-existent source"
        except RuntimeError as e:
            assert "File does not exist" in str(e)
            logger.info("✓ Non-existent source error handling works")
        try:
            copy_exif_from_file_to_file("examples/input/img-jpg/0000.jpg", "non_existent.jpg")
            assert False, "Should raise exception for non-existent input"
        except RuntimeError as e:
            assert "File does not exist" in str(e)
            logger.info("✓ Non-existent input error handling works")
        try:
            save_exif_data(None, "examples/input/img-jpg/0001.jpg")
            assert False, "Should raise exception for None EXIF"
        except RuntimeError as e:
            assert "No exif data provided" in str(e)
            logger.info("✓ None EXIF error handling works")
        logger.info("All error handling tests passed")
    except Exception as e:
        logger.error(f"Error handling test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_print_exif_edge_cases():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing print_exif edge cases ========")
        rational_exif = {
            282: IFDRational(72, 1),
            283: IFDRational(96, 1),
        }
        print_exif(rational_exif)
        logger.info("✓ IFDRational printing test passed")
        string_exif = {
            "CustomTag1": "Custom Value 1",
            "CustomTag2": "Custom Value 2",
        }
        print_exif(string_exif)
        logger.info("✓ String tag IDs printing test passed")
        empty_exif = {}
        print_exif(empty_exif)
        logger.info("✓ Empty EXIF printing test passed")
        logger.info("All print_exif edge case tests passed")
    except Exception as e:
        logger.error(f"print_exif edge cases test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_exif_decoding_error():
    test_exif = {
        270: b'\xff\xfe\x00\x01',
        305: b'Valid ASCII',
    }
    extra_tags, exif_tags = exif_extra_tags_for_tif(test_exif)
    assert extra_tags is not None


def test_safe_decode_bytes():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing safe_decode_bytes ========")
        test_cases = [
            (b"Hello World", "Hello World"),
            (b"Caf\xe9", "Café"),
            (b"Test \xa9 2024", "Test © 2024"),
            (b"\xe9", "é"),
            (b"Invalid \xff\xfe bytes", "Invalid ÿþ bytes"),
        ]
        for input_bytes, expected in test_cases:
            result = safe_decode_bytes(input_bytes)
            logger.info(f"Testing {input_bytes!r} => Expected: {expected!r}, Got: {result!r}")
            assert result == expected, f"Failed for {input_bytes!r}"
        assert safe_decode_bytes("Already a string") == "Already a string"
        assert safe_decode_bytes(123) == 123
        assert safe_decode_bytes(None) is None
        logger.info("✓ All safe_decode_bytes tests passed")
    except Exception as e:
        logger.error(f"safe_decode_bytes test failed: {str(e)}")
        assert False


def test_exif_exposure_data_detection():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing EXIF Exposure Data Detection (Including SubIFD) ========")
        source_file = "examples/input/img-exif/0000.jpg"
        if not os.path.exists(source_file):
            logger.warning(f"Test file not found: {source_file}")
            assert False
        original_exif = get_exif(source_file)
        logger.info("*** All EXIF Tags Found ***")
        print_exif(original_exif)
        exposure_tags = {
            33434: "ExposureTime",
            33437: "FNumber",
            34855: "ISOSpeedRatings",
            34850: "ExposureProgram",
            37377: "ShutterSpeedValue",
            37378: "ApertureValue",
            37379: "BrightnessValue",
            37380: "ExposureBiasValue",
            37381: "MaxApertureValue",
            37382: "SubjectDistance",
            37383: "MeteringMode",
            37384: "LightSource",
            37385: "Flash",
            37386: "FocalLength",
            41986: "ExposureMode",
            41987: "WhiteBalance",
            41493: "ExposureIndex"
        }
        found_exposure_data = {}
        for tag_id, tag_name in exposure_tags.items():
            if tag_id in original_exif:
                found_exposure_data[tag_name] = original_exif[tag_id]
        if found_exposure_data:
            logger.info("=== FOUND EXPOSURE DATA ===")
            for tag_name, value in found_exposure_data.items():
                logger.info(f"  {tag_name}: {value}")
            out_file = output_dir + "/test_exposure_preservation.jpg"
            test_target = "examples/input/img-jpg/0001.jpg"
            if os.path.exists(test_target):
                copy_exif_from_file_to_file(source_file, test_target, out_file, verbose=True)
                copied_exif = get_exif(out_file)
                logger.info("=== VERIFYING COPIED EXPOSURE DATA ===")
                preserved_count = 0
                for tag_name in found_exposure_data.keys():
                    tag_id = [k for k, v in exposure_tags.items() if v == tag_name][0]
                    if tag_id in copied_exif:
                        preserved_count += 1
                        logger.info(f"  ✓ {tag_name} preserved: {copied_exif[tag_id]}")
                    else:
                        logger.warning(f"  ✗ {tag_name} NOT preserved")
                        assert False
                logger.info(
                    f"=== RESULT: {preserved_count}/{len(found_exposure_data)} "
                    "exposure tags preserved ===")
        else:
            logger.warning("=== NO EXPOSURE DATA FOUND ===")
            logger.warning("Even with SubIFD extraction, no exposure data was found.")
            logger.warning("This could mean:")
            logger.warning("1. The file was heavily processed and exposure data was stripped")
            logger.warning("2. The camera didn't write exposure data to this particular file")
            logger.warning("3. There's an issue with the EXIF SubIFD extraction")
            assert False
    except Exception as e:
        logger.error(f"Exposure data detection test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_exif_subifd_exposure_preservation():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing EXIF SubIFD Exposure Data Preservation ========")
        source_file = "examples/input/img-exif/0000.jpg"
        if not os.path.exists(source_file):
            logger.warning("Test file not found, skipping SubIFD test")
            assert False
        original_exif = get_exif(source_file)
        subifd_exposure_tags = {
            33434: "ExposureTime",
            33437: "FNumber",
            34855: "ISOSpeedRatings",
            37377: "ShutterSpeedValue",
            37378: "ApertureValue",
            37386: "FocalLength"
        }
        found_tags = []
        for tag_id, tag_name in subifd_exposure_tags.items():
            if tag_id in original_exif:
                found_tags.append(tag_name)
                logger.info(f"✓ Found SubIFD tag: {tag_name} = {original_exif[tag_id]}")
            else:
                logger.warning(f"✗ Missing SubIFD tag: {tag_name}")
                assert False
        out_file = output_dir + "/test_subifd_preservation.jpg"
        test_target = "examples/input/img-jpg/0001.jpg"
        if os.path.exists(test_target):
            copy_exif_from_file_to_file(source_file, test_target, out_file, verbose=False)
            copied_exif = get_exif(out_file)
            preserved_count = 0
            for tag_id, tag_name in subifd_exposure_tags.items():
                if tag_id in original_exif and tag_id in copied_exif:
                    if original_exif[tag_id] == copied_exif[tag_id]:
                        preserved_count += 1
                    else:
                        logger.warning(
                            f"SubIFD tag {tag_name} not preserved: "
                            f"{original_exif[tag_id]} -> {copied_exif[tag_id]}")
                        assert False
            logger.info(
                f"=== RESULT: {preserved_count}/{len(subifd_exposure_tags)} "
                "SubIFD exposure tags preserved ===")
            if preserved_count != len(subifd_exposure_tags):
                logger.warning(f"Preserved {preserved_count}/{len(subifd_exposure_tags)} tags")
            else:
                logger.info("✓ EXIF SubIFD exposure preservation test passed")
    except Exception as e:
        logger.warning(f"SubIFD exposure test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_exif_tiff_with_subifd_data():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing TIFF Writing with SubIFD EXIF Data ========")
        source_file = "examples/input/img-exif/0000.jpg"
        if not os.path.exists(source_file):
            logger.warning("Test file not found, skipping TIFF SubIFD test")
            assert False
        exif = get_exif(source_file)
        logger.info("*** Source EXIF with SubIFD ***")
        exposure_tags = [33434, 33437, 34855, 37377, 37378, 37386]
        found_exposure = [tag for tag in exposure_tags if tag in exif]
        logger.info(f"Found {len(found_exposure)} exposure tags in source")
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        out_file = output_dir + "/test_tiff_subifd.tif"
        write_image_with_exif_data(exif, test_image, out_file)
        assert os.path.exists(out_file), "TIFF file was not created"
        tiff_exif = get_exif(out_file)
        logger.info("*** TIFF EXIF (should preserve exposure data) ***")
        preserved_count = 0
        for tag_id in found_exposure:
            if tag_id in tiff_exif:
                preserved_count += 1
                logger.info(f"✓ TIFF preserved: {TAGS.get(tag_id, tag_id)} = {tiff_exif[tag_id]}")
            else:
                logger.warning(f"✗ TIFF missing: {TAGS.get(tag_id, tag_id)}")
                assert False
        logger.info(
            f"=== RESULT: {preserved_count}/{len(found_exposure)} "
            "exposure tags preserved in TIFF ===")
        if preserved_count == 0:
            logger.warning(
                "No exposure data was preserved in TIFF - "
                "this is a known limitation with tifffile library")
        elif preserved_count < len(found_exposure):
            logger.warning(
                f"Only {preserved_count}/{len(found_exposure)} "
                "exposure tags preserved in TIFF")
            assert False
        else:
            logger.info("✓ TIFF writing with SubIFD data test passed")
    except Exception as e:
        logger.error(f"TIFF SubIFD test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        logger.warning("TIFF SubIFD test encountered an error but continuing...")
        assert False


def test_real_world_tiff_with_exif():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing Real-World TIFF with EXIF ========")
        source_file = "examples/input/img-exif/0000.jpg"
        if not os.path.exists(source_file):
            logger.warning("Test file not found, skipping real-world test")
            assert False
        exif = get_exif(source_file)
        logger.info(f"*** EXIF extracted from {os.path.basename(source_file)} ***")
        logger.info("=== Testing TIFF write with write_image_with_exif_data ===")
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        out_file = output_dir + "/real_world_test.tif"
        write_image_with_exif_data(exif, test_image, out_file, verbose=False)
        assert os.path.exists(out_file), "TIFF file was not created"
        tiff_exif = get_exif(out_file)
        logger.info("*** TIFF EXIF (should preserve exposure data) ***")
        exposure_tags = {
            33434: "ExposureTime",
            33437: "FNumber",
            34855: "ISOSpeedRatings",
            37377: "ShutterSpeedValue",
            37378: "ApertureValue",
            37386: "FocalLength"
        }
        preserved_count = 0
        for tag_id, tag_name in exposure_tags.items():
            if tag_id in tiff_exif:
                preserved_count += 1
                logger.info(f"✓ TIFF preserved: {tag_name} = {tiff_exif[tag_id]}")
            else:
                logger.warning(f"✗ TIFF missing: {tag_name}")
                assert False
        logger.info(
            f"=== RESULT: {preserved_count}/{len(exposure_tags)}"
            " exposure tags preserved in TIFF ===")
        try:
            with Image.open(out_file) as img:
                img.verify()
            logger.info("✓ TIFF file verification passed")
        except Exception as e:
            logger.error(f"TIFF verification failed: {e}")
            assert False
        logger.info("✓ Real-world TIFF test passed")
    except Exception as e:
        logger.error(f"Real-world TIFF test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_exif_round_trip_tiff_to_jpg():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing EXIF Round-Trip: TIFF -> JPEG ========")
        source_jpg = "examples/input/img-exif/0000.jpg"
        if not os.path.exists(source_jpg):
            logger.warning(f"Source file not found: {source_jpg}")
            assert False
        original_exif = get_exif(source_jpg)
        logger.info("*** Original JPG EXIF ***")
        print_exif(original_exif)
        exposure_tags = {
            33434: "ExposureTime",
            33437: "FNumber",
            34855: "ISOSpeedRatings",
            37377: "ShutterSpeedValue",
            37378: "ApertureValue",
            37386: "FocalLength",
            271: "Make",
            272: "Model",
            306: "DateTime",
            315: "Artist",
            33432: "Copyright"
        }
        original_exposure_count = sum(1 for tag_id in exposure_tags if tag_id in original_exif)
        logger.info(f"Found {original_exposure_count} exposure tags in original JPG")
        temp_tiff = output_dir + "/roundtrip_temp.tif"
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        logger.info("*** Writing TIFF with original EXIF ***")
        write_image_with_exif_data(original_exif, test_image, temp_tiff, verbose=False)
        assert os.path.exists(temp_tiff), "TIFF file was not created"
        tiff_exif = get_exif(temp_tiff)
        logger.info("*** TIFF EXIF (after writing) ***")
        print_exif(tiff_exif)
        tiff_exposure_count = sum(1 for tag_id in exposure_tags if tag_id in tiff_exif)
        logger.info(
            f"Preserved {tiff_exposure_count}/{original_exposure_count} "
            "exposure tags in TIFF")

        def normalize_exif_types(exif_dict):
            normalized = {}
            integer_tags = {
                274,  # Orientation
                296,  # ResolutionUnit
                259,  # Compression
                262,  # PhotometricInterpretation
                284,  # PlanarConfiguration
                277,  # SamplesPerPixel
                258,  # BitsPerSample
                273,  # StripOffsets
                278,  # RowsPerStrip
                279,  # StripByteCounts
                305,  # Software
                306,  # DateTime
                315,  # Artist
                271,  # Make
                272,  # Model
                33432,  # Copyright
                34855,  # ISOSpeedRatings
                37383,  # MeteringMode
                37385,  # Flash
                41985,  # CustomRendered
                41986,  # ExposureMode
                41987,  # WhiteBalance
                41990,  # SceneCaptureType
                40961,  # ColorSpace
                41488,  # FocalPlaneResolutionUnit,
            }
            for tag_id, value in exif_dict.items():
                if tag_id in integer_tags and isinstance(value, float) and value.is_integer():
                    normalized[tag_id] = int(value)
                else:
                    normalized[tag_id] = value
            return normalized
        normalized_tiff_exif = normalize_exif_types(tiff_exif)
        temp_jpg = output_dir + "/roundtrip_final.jpg"
        logger.info("*** Writing JPG with normalized TIFF EXIF ***")
        write_image_with_exif_data(normalized_tiff_exif, test_image, temp_jpg, verbose=False)
        assert os.path.exists(temp_jpg), "Final JPG file was not created"
        final_exif = get_exif(temp_jpg)
        logger.info("*** Final JPG EXIF (after TIFF->JPG round-trip) ***")
        print_exif(final_exif)
        final_exposure_count = sum(1 for tag_id in exposure_tags if tag_id in final_exif)
        logger.info(
            f"Preserved {final_exposure_count}/{original_exposure_count} "
            "exposure tags in final JPG")
        logger.info("=== Detailed EXIF Preservation Analysis ===")
        preserved_tags = []
        lost_tags = []

        def values_equal(v1, v2, rel_tol=1e-9, abs_tol=1e-12):
            if v1 == v2:
                return True
            try:
                f1, f2 = float(v1), float(v2)
                return abs(f1 - f2) <= max(rel_tol * max(abs(f1), abs(f2)), abs_tol)
            except (TypeError, ValueError):
                return False

        for tag_id, tag_name in exposure_tags.items():
            if tag_id in original_exif:
                original_value = original_exif[tag_id]
                final_value = final_exif.get(tag_id)
                if final_value is not None:
                    if hasattr(original_value, 'numerator') and hasattr(final_value, 'numerator'):
                        if values_equal(original_value, final_value):
                            preserved_tags.append((tag_name, original_value, final_value))
                        else:
                            lost_tags.append(
                                (tag_name, original_value, final_value, "value changed"))
                    elif values_equal(original_value, final_value):
                        preserved_tags.append((tag_name, original_value, final_value))
                    else:
                        lost_tags.append((tag_name, original_value, final_value, "value changed"))
                else:
                    lost_tags.append((tag_name, original_value, None, "tag missing"))
        logger.info("✓ PRESERVED TAGS:")
        for tag_name, orig_val, final_val in preserved_tags:
            logger.info(f"  {tag_name}: {orig_val} -> {final_val}")
        if lost_tags:
            logger.info("✗ LOST/CHANGED TAGS:")
            for tag_name, orig_val, final_val, reason in lost_tags:
                logger.info(f"  {tag_name}: {orig_val} -> {final_val} ({reason})")
        else:
            logger.info("✓ All exposure tags perfectly preserved!")
        total_tags = len(preserved_tags) + len(lost_tags)
        if total_tags > 0:
            preservation_rate = len(preserved_tags) / total_tags * 100
            logger.info(f"=== FINAL RESULT: {preservation_rate:.1f}% preservation rate ===")
            if preservation_rate >= 80:  # Allow 20% loss due to format limitations
                logger.info("✓ TIFF->JPEG EXIF round-trip test PASSED")
            else:
                logger.warning(
                    "⚠ TIFF->JPEG EXIF round-trip test: "
                    f"Low preservation rate ({preservation_rate:.1f}%)")
                assert False
        else:
            logger.warning("No exposure tags found to compare")
        for temp_file in [temp_tiff, temp_jpg]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.info(f"Cleaned up: {temp_file}")
    except Exception as e:
        logger.error(f"TIFF->JPEG round-trip test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_pil_exif_basic():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing Basic PIL EXIF Writing ========")
        test_image = Image.new('RGB', (100, 100), color='red')
        exif_obj = Image.Exif()
        exif_obj[271] = "Test Make"  # Make
        exif_obj[272] = "Test Model"  # Model
        exif_obj[306] = "2024:01:01 12:00:00"  # DateTime
        out_file = output_dir + "/test_pil_basic.jpg"
        test_image.save(out_file, "JPEG", exif=exif_obj.tobytes(), quality=100)
        written_exif = get_exif(out_file)
        logger.info("*** Written EXIF with basic PIL ***")
        print_exif(written_exif)
        if 271 in written_exif and 272 in written_exif and 306 in written_exif:
            logger.info("✓ Basic PIL EXIF writing works")
        else:
            logger.error("✗ Basic PIL EXIF writing FAILED")
            assert False
    except Exception as e:
        logger.error(f"Basic PIL test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_jpg_to_jpg_vs_tiff_to_jpg():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Comparing JPG→JPG vs JPG→TIFF→JPG ========")
        source_jpg = "examples/input/img-exif/0000.jpg"
        if not os.path.exists(source_jpg):
            logger.warning("Source file not found")
            assert False
        logger.info("*** Test 1: Direct JPG→JPG ***")
        direct_out = output_dir + "/direct_jpg_to_jpg.jpg"
        exif = get_exif(source_jpg)
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        write_image_with_exif_data(exif, test_image, direct_out, verbose=False)
        direct_exif = get_exif(direct_out)
        exposure_tags = [33434, 33437, 34855, 37377, 37378, 37386, 271, 272, 306]
        direct_preserved = sum(1 for tag_id in exposure_tags if tag_id in direct_exif)
        logger.info(
            f"Direct JPG→JPG preserved {direct_preserved}/{len(exposure_tags)} exposure tags")
        logger.info("*** Test 2: JPG→TIFF→JPG ***")
        temp_tiff = output_dir + "/temp_for_comparison.tif"
        write_image_with_exif_data(exif, test_image, temp_tiff, verbose=False)
        tiff_exif = get_exif(temp_tiff)

        def normalize_exif_types(exif_dict):
            normalized = {}
            integer_tags = {
                274,  # Orientation
                296,  # ResolutionUnit
                259,  # Compression
                262,  # PhotometricInterpretation
                284,  # PlanarConfiguration
                277,  # SamplesPerPixel
                258,  # BitsPerSample
                273,  # StripOffsets
                278,  # RowsPerStrip
                279,  # StripByteCounts
                305,  # Software
                306,  # DateTime
                315,  # Artist
                271,  # Make
                272,  # Model
                33432,  # Copyright
                34855,  # ISOSpeedRatings
                37383,  # MeteringMode
                37385,  # Flash
                41985,  # CustomRendered
                41986,  # ExposureMode
                41987,  # WhiteBalance
                41990,  # SceneCaptureType
                40961,  # ColorSpace
                41488,  # FocalPlaneResolutionUnit,
            }
            for tag_id, value in exif_dict.items():
                if tag_id in integer_tags and isinstance(value, float) and value.is_integer():
                    normalized[tag_id] = int(value)
                else:
                    normalized[tag_id] = value
            return normalized

        normalized_tiff_exif = normalize_exif_types(tiff_exif)
        final_jpg = output_dir + "/tiff_to_jpg.jpg"
        write_image_with_exif_data(normalized_tiff_exif, test_image, final_jpg, verbose=False)
        final_exif = get_exif(final_jpg)
        final_preserved = sum(1 for tag_id in exposure_tags if tag_id in final_exif)
        logger.info(f"JPG→TIFF→JPG preserved {final_preserved}/{len(exposure_tags)} exposure tags")
        logger.info(f"=== RESULT: Direct={direct_preserved}, Via TIFF={final_preserved} ===")
        if direct_preserved >= final_preserved:
            logger.info("✓ Direct JPG→JPG preserves at least as many tags as JPG→TIFF→JPG")
        else:
            logger.warning(
                f"⚠ Unexpected: Direct preserves {direct_preserved}, "
                f"but via TIFF preserves {final_preserved}")
        for f in [temp_tiff, direct_out, final_jpg]:
            if os.path.exists(f):
                os.remove(f)
                logger.info(f"Cleaned up: {f}")
    except Exception as e:
        logger.error(f"Comparison test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_png_metadata_enhancement():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing Enhanced PNG Metadata ========")
        source_jpg = "examples/input/img-exif/0000.jpg"
        if not os.path.exists(source_jpg):
            logger.warning("Source file not found, skipping test")
            assert False
        original_exif = get_exif(source_jpg)
        logger.info("*** Original EXIF ***")
        print_exif(original_exif)
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        png_out = output_dir + "/enhanced_metadata.png"
        write_image_with_exif_data(original_exif, test_image, png_out, verbose=True)
        png_exif = get_exif(png_out)
        logger.info("*** PNG EXIF (should have enhanced metadata) ***")
        print_exif(png_exif)
        with Image.open(png_out) as img:
            if hasattr(img, 'text') and img.text:
                logger.info("*** PNG Text Chunks Found ***")
                for key, value in img.text.items():
                    if 'xmp' in key.lower() or 'exif' in key.lower():
                        logger.info(f"  {key}: {str(value)[:200]}...")
        logger.info("✓ Enhanced PNG metadata test completed")
    except Exception as e:
        logger.error(f"Enhanced PNG metadata test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_enhanced_png_exif():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing Enhanced PNG EXIF Extraction ========")
        source_jpg = "examples/input/img-exif/0000.jpg"
        if not os.path.exists(source_jpg):
            logger.warning("Source file not found")
            assert False
        original_exif = get_exif(source_jpg)
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        png_out = output_dir + "/test_enhanced.png"
        write_image_with_exif_data(original_exif, test_image, png_out, verbose=False)
        with Image.open(png_out) as png_image:
            basic_exif = get_exif_from_png(png_image)
            enhanced_exif = get_enhanced_exif_from_png(png_image)
        logger.info("*** Basic PNG EXIF ***")
        print_exif(basic_exif)
        logger.info("*** Enhanced PNG EXIF ***")
        print_exif(enhanced_exif)
        key_tags = [271, 272, 33434, 33437, 34855, 37386, 42036]
        basic_count = sum(1 for tag in key_tags
                          if tag in basic_exif and basic_exif[tag] is not None)
        enhanced_count = sum(1 for tag in key_tags
                             if tag in enhanced_exif and enhanced_exif[tag] is not None)
        logger.info(f"Key tags found: Basic={basic_count}, Enhanced={enhanced_count}")
        if enhanced_count > basic_count:
            logger.info("✓ Enhanced EXIF extraction successful")
        else:
            logger.info("⚠ No improvement with enhanced extraction")
            assert False
    except Exception as e:
        logger.error(f"Enhanced PNG EXIF test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_unified_exif_with_enhanced_png():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing Unified EXIF with Enhanced PNG ========")
        source_jpg = "examples/input/img-exif/0000.jpg"
        if not os.path.exists(source_jpg):
            logger.warning("Source file not found")
            assert False
        original_exif = get_exif(source_jpg)
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        png_out = output_dir + "/test_unified.png"
        write_image_with_exif_data(original_exif, test_image, png_out, verbose=False)
        logger.info("*** Standard get_exif() (enhanced PNG parsing) ***")
        unified_exif = get_exif(png_out)
        print_exif(unified_exif)
        logger.info("*** Legacy get_exif() (no enhanced parsing) ***")
        legacy_exif = get_exif(png_out, enhanced_png_parsing=False)
        print_exif(legacy_exif)
        key_tags = [271, 272, 33434, 33437, 34855, 37386, 42036]
        unified_count = sum(1 for tag in key_tags
                            if tag in unified_exif and unified_exif[tag] is not None)
        legacy_count = sum(1 for tag in key_tags
                           if tag in legacy_exif and legacy_exif[tag] is not None)
        logger.info(f"Key tags found: Unified={unified_count}, Legacy={legacy_count}")
        if unified_count > legacy_count:
            logger.info("✓ Unified EXIF with enhanced PNG parsing successful")
            logger.info("*** Testing PNG→JPG round-trip with enhanced EXIF ***")
            jpg_out = output_dir + "/test_png_to_jpg.jpg"
            write_image_with_exif_data(unified_exif, test_image, jpg_out, verbose=False)
            roundtrip_exif = get_exif(jpg_out)
            roundtrip_count = sum(1 for tag in key_tags
                                  if tag in roundtrip_exif and roundtrip_exif[tag] is not None)
            logger.info(f"Key tags preserved in PNG→JPG: {roundtrip_count}/{unified_count}")
        else:
            logger.info("⚠ No improvement with unified EXIF")
            assert False
    except Exception as e:
        logger.error(f"Unified EXIF test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_exif_round_trip_jpg_to_png_to_jpg():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing EXIF Round-Trip: JPG -> PNG -> JPG ========")
        source_jpg = "examples/input/img-exif/0000.jpg"
        if not os.path.exists(source_jpg):
            logger.error(f"Source file not found: {source_jpg}")
            assert False, f"Source file not found: {source_jpg}"
        original_exif = get_exif(source_jpg)
        logger.info("*** Original JPG EXIF ***")
        print_exif(original_exif)
        key_exif_tags = {
            271: "Make",
            272: "Model",
            306: "DateTime",
            315: "Artist",
            33432: "Copyright",
            33434: "ExposureTime",
            33437: "FNumber",
            34855: "ISOSpeedRatings",
            37377: "ShutterSpeedValue",
            37378: "ApertureValue",
            37386: "FocalLength",
            42036: "LensModel",
            36867: "DateTimeOriginal",
            37385: "Flash",
            41987: "WhiteBalance"
        }
        original_count = sum(1 for tag_id in key_exif_tags if tag_id in original_exif)
        logger.info(f"Found {original_count}/{len(key_exif_tags)} key EXIF tags in original JPG")
        assert original_count > 0, "No key EXIF tags found in original JPG"
        temp_png = output_dir + "/roundtrip_temp.png"
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        logger.info("*** Writing PNG with original EXIF ***")
        write_image_with_exif_data(original_exif, test_image, temp_png, verbose=False)
        assert os.path.exists(temp_png), "PNG file was not created"
        png_exif = get_exif(temp_png)
        logger.info("*** PNG EXIF (after JPG->PNG) ***")
        print_exif(png_exif)
        png_count = sum(1 for tag_id in key_exif_tags if tag_id in png_exif)
        logger.info(f"Preserved {png_count}/{original_count} key tags in PNG")
        assert png_count > 0, "No EXIF tags preserved in PNG"
        final_jpg = output_dir + "/roundtrip_final.jpg"
        logger.info("*** Writing JPG with PNG EXIF ***")
        write_image_with_exif_data(png_exif, test_image, final_jpg, verbose=False)
        assert os.path.exists(final_jpg), "Final JPG file was not created"
        final_exif = get_exif(final_jpg)
        logger.info("*** Final JPG EXIF (after PNG->JPG) ***")
        print_exif(final_exif)
        final_count = sum(1 for tag_id in key_exif_tags if tag_id in final_exif)
        logger.info(f"Preserved {final_count}/{original_count} key tags in final JPG")
        assert final_count > 0, "No EXIF tags preserved in final JPG"
        logger.info("=== Detailed JPG->PNG->JPG EXIF Preservation Analysis ===")
        preserved_tags = []
        lost_tags = []
        value_changed_tags = []
        for tag_id, tag_name in key_exif_tags.items():
            if tag_id in original_exif:
                original_value = original_exif[tag_id]
                png_exif.get(tag_id)
                final_value = final_exif.get(tag_id)
                if final_value is not None:
                    if (hasattr(original_value, 'numerator') and hasattr(final_value, 'numerator')):
                        if abs(float(original_value) - float(final_value)) < 0.001:
                            preserved_tags.append((tag_name, original_value, final_value))
                        else:
                            value_changed_tags.append(
                                (tag_name, original_value, final_value,
                                 f"value changed: {original_value} -> {final_value}")
                            )
                    elif (isinstance(original_value, (str, bytes)) and
                          isinstance(final_value, (str, bytes))):
                        orig_str = safe_decode_bytes(original_value)
                        final_str = safe_decode_bytes(final_value)
                        if orig_str == final_str:
                            preserved_tags.append((tag_name, original_value, final_value))
                        else:
                            value_changed_tags.append(
                                (tag_name, original_value, final_value,
                                 f"value changed: {orig_str} -> {final_str}")
                            )
                    elif original_value == final_value:
                        preserved_tags.append((tag_name, original_value, final_value))
                    else:
                        value_changed_tags.append(
                            (tag_name, original_value, final_value,
                             f"value changed: {original_value} -> {final_value}")
                        )
                else:
                    lost_tags.append((tag_name, original_value, None, "tag missing in final JPG"))
        logger.info("✓ PERFECTLY PRESERVED TAGS:")
        for tag_name, orig_val, final_val in preserved_tags:
            logger.info(f"  {tag_name}: {orig_val}")
        if value_changed_tags:
            logger.info("⚠ VALUE CHANGED TAGS:")
            for tag_name, orig_val, final_val, reason in value_changed_tags:
                logger.info(f"  {tag_name}: {reason}")
        if lost_tags:
            logger.info("✗ COMPLETELY LOST TAGS:")
            for tag_name, orig_val, final_val, reason in lost_tags:
                logger.info(f"  {tag_name}: {reason}")
        total_tested = len(preserved_tags) + len(value_changed_tags) + len(lost_tags)
        assert total_tested > 0, "No EXIF tags were tested in round-trip"
        perfect_preservation_rate = len(preserved_tags) / total_tested * 100
        any_preservation_rate = (len(preserved_tags) + len(value_changed_tags)) / total_tested * 100
        logger.info("=== ROUND-TRIP PRESERVATION RESULTS ===")
        logger.info(
            f"Perfect preservation: {perfect_preservation_rate:.1f}% "
            f"({len(preserved_tags)}/{total_tested})")
        logger.info(
            f"Any preservation: {any_preservation_rate:.1f}% "
            f"({len(preserved_tags) + len(value_changed_tags)}/{total_tested})")
        logger.info(
            f"Completely lost: {len(lost_tags)}/{total_tested}")
        png_preservation = sum(1 for tag_id in key_exif_tags
                               if tag_id in original_exif and tag_id in png_exif)
        png_preservation_rate = png_preservation / total_tested * 100
        logger.info(
            f"PNG preservation: {png_preservation_rate:.1f}% ({png_preservation}/{total_tested})")
        assert perfect_preservation_rate >= 60, \
            f"Perfect preservation rate too low: {perfect_preservation_rate:.1f}%"
        assert any_preservation_rate >= 70, \
            f"Any preservation rate too low: {any_preservation_rate:.1f}%"
        for temp_file in [temp_png, final_jpg]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.info(f"Cleaned up: {temp_file}")
        logger.info("✓ JPG->PNG->JPG round-trip test completed")
    except Exception as e:
        logger.error(f"JPG->PNG->JPG round-trip test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False, f"JPG->PNG->JPG round-trip test failed: {str(e)}"


def test_png_string_tags():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing PNG String Tags ========")
        test_img = np.ones((50, 50, 3), dtype=np.uint8) * 128
        exif_with_string_tags = {
            "CustomTag1": "Custom Value 1",
            "PNG_CustomTag2": "Custom Value 2",  # Should be cleaned to "CustomTag2"
            "AnotherStringTag": "Another Value",
            "Description": "Test description for PNG",
            "Author": "Test Author",
            "xmp:SomeTag": "XMP Value",
            "XML:AnotherTag": "XML Value",
            "xmlpacket": "XML Packet Value",
            271: "Test Make",  # Make
            272: "Test Model",  # Model
            305: "Test Software",  # Software
        }
        out_filename = output_dir + "/test_png_string_tags.png"
        write_image_with_exif_data(exif_with_string_tags, test_img, out_filename, verbose=True)
        assert os.path.exists(out_filename), "PNG file with string tags was not created"
        written_exif = get_exif(out_filename)
        logger.info("*** Written PNG EXIF with string tags ***")
        print_exif(written_exif)
        with Image.open(out_filename) as img:
            if hasattr(img, 'text') and img.text:
                logger.info("*** PNG Text Chunks Found ***")
                found_string_tags = []
                for key, value in img.text.items():
                    logger.info(f"  {key}: {str(value)[:100]}")
                    if key in ["CustomTag1", "CustomTag2",
                               "AnotherStringTag", "Description", "Author"]:
                        found_string_tags.append(key)
                logger.info(f"Found {len(found_string_tags)} string tags in PNG text chunks")
                assert "CustomTag1" in img.text, "CustomTag1 should be in PNG text"
                assert "CustomTag2" in img.text, \
                    "CustomTag2 (cleaned from PNG_CustomTag2) should be in PNG text"
                assert "AnotherStringTag" in img.text, "AnotherStringTag should be in PNG text"
                assert "Description" in img.text, "Description should be in PNG text"
                assert "Author" in img.text, "Author should be in PNG text"
                xmp_tags = [key for key in img.text.keys()
                            if key.lower().startswith(('xmp', 'xml'))]
                logger.info(f"XMP/XML tags found: {len(xmp_tags)}")
                assert img.text["CustomTag1"] == "Custom Value 1", \
                    "CustomTag1 value mismatch"
                assert img.text["CustomTag2"] == "Custom Value 2", \
                    "CustomTag2 value mismatch"
                assert img.text["AnotherStringTag"] == "Another Value", \
                    "AnotherStringTag value mismatch"
                logger.info("✓ All string tag values match expected values")
            else:
                logger.error(
                    "No text chunks found in PNG - _add_png_text_tag may not have been called")
                assert False, "No text chunks found in PNG"
        assert 271 in written_exif or "Make" in str(written_exif), "Make tag should be preserved"
        assert 272 in written_exif or "Model" in str(written_exif), "Model tag should be preserved"
        logger.info("✓ PNG string tags test passed - _add_png_text_tag was successfully called")
    except Exception as e:
        logger.error(f"PNG string tags test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_add_exif_data_to_jpg_file_error_handling():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing add_exif_data_to_jpg_file Error Handling ========")
        logger.info("*** Testing same file with corrupt EXIF data ***")
        test_source = "examples/input/img-jpg/0001.jpg"
        if not os.path.exists(test_source):
            logger.warning("Test source file not found, skipping error handling test")
            assert False
        same_file_test = output_dir + "/test_same_file_error.jpg"
        import shutil
        shutil.copy2(test_source, same_file_test)
        corrupt_exif = {
            # Very long string that might cause buffer issues
            270: 'A' * 10000,
            # Invalid data types
            271: object(),  # Non-serializable object
            # Nested structure that PIL might not handle
            272: {'nested': 'data'},
        }
        try:
            add_exif_data_to_jpg_file(corrupt_exif, same_file_test, same_file_test, verbose=True)
            logger.warning("Expected exception was not raised with corrupt EXIF data")
        except Exception as e:
            logger.info(f"✓ Correctly caught exception with corrupt EXIF: {str(e)}")
            temp_file = same_file_test + ".tmp"
            if os.path.exists(temp_file):
                logger.error(f"Temp file was not cleaned up: {temp_file}")
                assert False, "Temp file should have been cleaned up"
            else:
                logger.info("✓ Temp file was properly cleaned up")
            if os.path.exists(same_file_test):
                try:
                    test_img = Image.open(same_file_test)
                    test_img.verify()
                    test_img.close()
                    logger.info("✓ Original file is still valid after exception")
                except Exception as img_error:
                    logger.error(f"Original file corrupted after exception: {img_error}")
                    assert False, "Original file should remain valid"
            else:
                logger.error("Original file was deleted after exception")
                assert False, "Original file should not be deleted"
        logger.info("*** Testing different files with problematic EXIF ***")
        different_out = output_dir + "/test_different_file_error.jpg"
        problematic_exif = {
            270: b'\xff\xfe\x00\x01\x02\x03',  # Binary data that's not valid UTF-8
            305: 'Normal string',
            315: 'Another normal string',
        }
        try:
            add_exif_data_to_jpg_file(problematic_exif, test_source, different_out, verbose=True)
            if os.path.exists(different_out):
                try:
                    test_img = Image.open(different_out)
                    test_img.verify()
                    test_img.close()
                    logger.info(
                        "✓ Different files: Output file created and valid despite potential issues")
                except Exception as img_error:
                    logger.error(f"Different files: Output file is invalid: {img_error}")
            else:
                logger.warning("Different files: Output file was not created")
        except Exception as e:
            logger.info(f"✓ Different files: Exception caught as expected: {str(e)}")
            if os.path.exists(different_out):
                try:
                    test_img = Image.open(different_out)
                    test_img.verify()
                    test_img.close()
                    logger.info("✓ Different files: Fallback worked - output file is valid image")
                except Exception as img_error:
                    logger.error(f"Different files: Fallback produced invalid file: {img_error}")
                    assert False, "Fallback should produce valid image file"
        logger.info("*** Testing non-existent input file ***")
        non_existent_input = "non_existent_input.jpg"
        non_existent_output = output_dir + "/test_nonexistent_output.jpg"
        try:
            add_exif_data_to_jpg_file({}, non_existent_input, non_existent_output, verbose=True)
            logger.error("Should have raised exception for non-existent input file")
            assert False
        except Exception as e:
            logger.info(f"✓ Correctly caught exception for non-existent input: {str(e)}")
        logger.info("*** Testing valid EXIF with edge cases ***")
        edge_case_exif = {
            # IFDRational values
            282: IFDRational(72, 1),
            283: IFDRational(96, 1),
            # Empty strings
            270: '',
            305: '',
            # Normal values
            271: 'Test Make',
            272: 'Test Model',
        }
        edge_case_out = output_dir + "/test_edge_cases.jpg"
        try:
            add_exif_data_to_jpg_file(edge_case_exif, test_source, edge_case_out, verbose=True)
            if os.path.exists(edge_case_out):
                written_exif = get_exif(edge_case_out)
                logger.info("✓ Edge case EXIF: File created successfully")
                if written_exif:
                    logger.info("✓ Edge case EXIF: EXIF data found in output")
                else:
                    logger.warning(
                        "Edge case EXIF: No EXIF data found in output (might be expected)")
            else:
                logger.error("Edge case EXIF: Output file was not created")
                assert False
        except Exception as e:
            logger.error(f"Edge case EXIF: Unexpected exception: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            assert False
        logger.info("✓ All add_exif_data_to_jpg_file error handling tests passed")
    except Exception as e:
        logger.error(f"add_exif_data_to_jpg_file error handling test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_write_image_with_exif_data_error_handling():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing write_image_with_exif_data Error Handling ========")
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        logger.info("*** Testing None EXIF data ***")
        none_exif_out = output_dir + "/test_none_exif.jpg"
        try:
            result = write_image_with_exif_data(None, test_image, none_exif_out, verbose=True)
            assert result is None, "Should return None when EXIF is None"
            assert os.path.exists(none_exif_out), "File should be created with None EXIF"
            logger.info("✓ None EXIF test passed - file created with write_img fallback")
        except Exception as e:
            logger.error(f"None EXIF test failed: {str(e)}")
            assert False
        logger.info("*** Testing invalid image data ***")
        invalid_image_out = output_dir + "/test_invalid_image.jpg"
        invalid_exif = {271: 'Test Make', 272: 'Test Model'}
        try:
            write_image_with_exif_data(invalid_exif, None, invalid_image_out, verbose=True)
            logger.error("Should have failed with invalid image data")
            assert False
        except Exception as e:
            logger.info(f"✓ Correctly caught exception for invalid image: {str(e)}")
        logger.info("*** Testing unsupported file format ***")
        unsupported_out = output_dir + "/test_unsupported.bmp"
        normal_exif = {271: 'Test Make', 272: 'Test Model'}
        try:
            write_image_with_exif_data(normal_exif, test_image, unsupported_out, verbose=True)
            if os.path.exists(unsupported_out):
                logger.info("✓ Unsupported format: File created (write_img handled it)")
            else:
                logger.warning("Unsupported format: File not created (might be expected)")
        except Exception as e:
            logger.info(f"Unsupported format: Exception caught: {str(e)}")
        logger.info("✓ All write_image_with_exif_data error handling tests passed")
    except Exception as e:
        logger.error(f"write_image_with_exif_data error handling test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_copy_exif_error_handling():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing copy_exif_from_file_to_file Error Handling ========")
        logger.info("*** Testing non-existent source EXIF file ***")
        non_existent_source = "non_existent_source.jpg"
        valid_target = "examples/input/img-jpg/0001.jpg" \
            if os.path.exists("examples/input/img-jpg/0001.jpg") else None
        if valid_target:
            try:
                copy_exif_from_file_to_file(non_existent_source, valid_target)
                logger.error("Should have raised exception for non-existent source")
                assert False
            except RuntimeError as e:
                assert "File does not exist" in str(e)
                logger.info("✓ Correctly caught exception for non-existent source")
        logger.info("*** Testing non-existent input file ***")
        valid_source = "examples/input/img-jpg/0000.jpg" \
            if os.path.exists("examples/input/img-jpg/0000.jpg") else None
        non_existent_input = "non_existent_input.jpg"
        if valid_source:
            try:
                copy_exif_from_file_to_file(valid_source, non_existent_input)
                logger.error("Should have raised exception for non-existent input")
                assert False
            except RuntimeError as e:
                assert "File does not exist" in str(e)
                logger.info("✓ Correctly caught exception for non-existent input")
        logger.info("✓ All copy_exif_from_file_to_file error handling tests passed")
    except Exception as e:
        logger.error(f"copy_exif_from_file_to_file error handling test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_exif_subifd_exception_handling():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing EXIF SubIFD Exception Handling ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        test_img = np.ones((100, 100, 3), dtype=np.uint8) * 128
        test_jpg = output_dir + "/test_no_subifd.jpg"
        cv2.imwrite(test_jpg, test_img)
        get_exif(test_jpg)
        logger.info("✓ EXIF SubIFD exception handling test passed")
    except Exception as e:
        logger.error(f"EXIF SubIFD exception handling test failed: {str(e)}")
        assert False


def test_get_exif_fallback():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing get_exif Fallback ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        test_img = np.ones((100, 100, 3), dtype=np.uint8) * 128
        test_bmp = output_dir + "/test_fallback.bmp"
        cv2.imwrite(test_bmp, test_img)
        exif = get_exif(test_bmp)
        logger.info(f"Fallback EXIF type: {type(exif)}")
        logger.info("✓ get_exif fallback test passed")
    except Exception as e:
        logger.error(f"get_exif fallback test failed: {str(e)}")
        assert False


def test_get_exif_from_png_no_data():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing get_exif_from_png with No Data ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        img = Image.new('RGB', (100, 100), color='blue')
        test_png = output_dir + "/test_no_exif.png"
        img.save(test_png)
        exif = get_exif_from_png(Image.open(test_png))
        assert exif == {}, "Should return empty dict for PNG with no EXIF"
        logger.info("✓ get_exif_from_png no data test passed")
    except Exception as e:
        logger.error(f"get_exif_from_png no data test failed: {str(e)}")
        assert False


def test_xmp_data_decoding():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing XMP Data Decoding ========")
        test_cases = [
            b'<?xpacket begin="test"?><test>normal utf8</test>',
            b'\xff\xfe<?xpacket begin="test"?><test>utf16</test>',  # UTF-16 BOM
            b'<?xpacket begin="test"?><test>\xc3\xa9</test>',  # UTF-8 with accented char
        ]
        for i, xmp_bytes in enumerate(test_cases):
            result = parse_xmp_to_exif(xmp_bytes)
            logger.info(f"XMP test case {i + 1}: {len(result)} tags extracted")
        xmp_str = '<?xpacket begin="test"?><test>string input</test>'
        result = parse_xmp_to_exif(xmp_str)
        logger.info("✓ XMP data decoding test passed")
    except Exception as e:
        logger.error(f"XMP data decoding test failed: {str(e)}")
        assert False


def test_rational_parsing_edge_cases():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing Rational Parsing Edge Cases ========")
        test_cases = [
            (33434, "invalid/rational"),  # Missing denominator
            (33434, "1/0"),  # Zero division
            (33434, "not_a_number/also_not"),  # Value error
            (33434, ""),  # Empty string
        ]
        for tag_id, value in test_cases:
            result = _parse_xmp_value(tag_id, value)
            logger.info(f"Rational edge case {value} -> {result}")
        png_test_cases = [
            "RATIONAL:invalid/format",
            "RATIONAL:1/0",  # Zero division
            "RATIONAL:not_num/not_den",
        ]
        for value in png_test_cases:
            result = parse_typed_png_text(value)
            logger.info(f"PNG rational edge case {value} -> {result}")
        logger.info("✓ Rational parsing edge cases test passed")
    except Exception as e:
        logger.error(f"Rational parsing edge cases test failed: {str(e)}")
        assert False


def test_iso_parsing_error():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing ISO Parsing Errors ========")
        invalid_iso_cases = [
            "<rdf:li>not_a_number</rdf:li>",
            "invalid",
            "",
            "12.5",  # Float as string
        ]
        for iso_value in invalid_iso_cases:
            result = _parse_xmp_value(34855, iso_value)  # 34855 is ISO tag
            logger.info(f"ISO parsing {iso_value} -> {result}")
        logger.info("✓ ISO parsing error test passed")
    except Exception as e:
        logger.error(f"ISO parsing error test failed: {str(e)}")
        assert False


def test_typed_png_text_parsing():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing Typed PNG Text Parsing ========")
        test_cases = [
            ("INT:123", 123),
            ("INT:not_a_number", "not_a_number"),
            ("FLOAT:3.14", 3.14),
            ("FLOAT:not_a_float", "not_a_float"),
            ("STRING:test string", "test string"),
            ("BYTES:test bytes", b"test bytes"),
            ("ARRAY:item1,item2,item3", ["item1", "item2", "item3"]),
            ("UNKNOWN:format", "UNKNOWN:format"),
        ]
        for input_val, expected_type in test_cases:
            result = parse_typed_png_text(input_val)
            logger.info(f"Typed PNG text {input_val} -> {result} (type: {type(result)})")
        logger.info("✓ Typed PNG text parsing test passed")
    except Exception as e:
        logger.error(f"Typed PNG text parsing test failed: {str(e)}")
        assert False


def test_enhanced_exif_xmp_from_basic():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing Enhanced EXIF with XMP in Basic ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        img = Image.new('RGB', (100, 100), color='green')
        test_png = output_dir + "/test_xmp_in_basic.png"
        basic_exif = Image.Exif()
        xmp_data = '<?xpacket begin="test"?><test>XMP in basic EXIF</test>'
        basic_exif[700] = xmp_data.encode('utf-8')
        img.save(test_png, exif=basic_exif.tobytes())
        with Image.open(test_png) as png_img:
            enhanced_exif = get_enhanced_exif_from_png(png_img)
        logger.info(f"Enhanced EXIF with XMP in basic: {len(enhanced_exif)} tags")
        logger.info("✓ Enhanced EXIF with XMP in basic test passed")
    except Exception as e:
        logger.error(f"Enhanced EXIF with XMP in basic test failed: {str(e)}")
        assert False


def test_safe_decode_bytes_edge_cases():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing safe_decode_bytes Edge Cases ========")
        test_cases = [
            b'\xff\xfe\x00\x01\x02\x03',  # Invalid UTF-8 that fails all encodings
            b'\x80\x81\x82\x83',  # Non-ASCII bytes
            b'',  # Empty bytes
        ]
        for i, test_bytes in enumerate(test_cases):
            result = safe_decode_bytes(test_bytes)
            logger.info(f"safe_decode_bytes case {i + 1}: {test_bytes} -> {result}")
        logger.info("✓ safe_decode_bytes edge cases test passed")
    except Exception as e:
        logger.error(f"safe_decode_bytes edge cases test failed: {str(e)}")
        assert False


def test_add_exif_data_to_jpg_file_none_exif():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing add_exif_data_to_jpg_file with None EXIF ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        source_file = "examples/input/img-jpg/0001.jpg"
        if not os.path.exists(source_file):
            logger.warning("Source file not found, skipping test")
            assert False
        out_file = output_dir + "/test_none_exif.jpg"
        try:
            add_exif_data_to_jpg_file(None, source_file, out_file)
            assert False, "Should have raised RuntimeError for None EXIF"
        except RuntimeError as e:
            assert "No exif data provided" in str(e)
            logger.info("✓ Correctly caught None EXIF error")
    except Exception as e:
        logger.error(f"add_exif_data_to_jpg_file None EXIF test failed: {str(e)}")
        assert False


def test_add_exif_data_to_jpg_file_same_file():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing add_exif_data_to_jpg_file Same File ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        source_file = "examples/input/img-jpg/0001.jpg"
        if not os.path.exists(source_file):
            logger.warning("Source file not found, skipping test")
            assert False
        test_file = output_dir + "/test_same_file.jpg"
        import shutil
        shutil.copy2(source_file, test_file)
        exif = get_exif(source_file)
        add_exif_data_to_jpg_file(exif, test_file, test_file, verbose=True)
        assert os.path.exists(test_file), "File should exist after same-file operation"
        with Image.open(test_file) as img:
            img.verify()
        logger.info("✓ add_exif_data_to_jpg_file same file test passed")
    except Exception as e:
        logger.error(f"add_exif_data_to_jpg_file same file test failed: {str(e)}")
        assert False


def test_add_exif_data_to_jpg_file_invalid_tags():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing add_exif_data_to_jpg_file with Invalid Tags ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        source_file = "examples/input/img-jpg/0001.jpg"
        if not os.path.exists(source_file):
            logger.warning("Source file not found, skipping test")
            assert False
        out_file = output_dir + "/test_invalid_tags.jpg"
        problematic_exif = {
            # Very large binary data that might be problematic
            700: b'x' * 10000,
            # Complex object that might not serialize well
            315: {'nested': 'data'},
            # Normal tags that should work
            271: "Test Make",
            272: "Test Model",
        }
        add_exif_data_to_jpg_file(problematic_exif, source_file, out_file, verbose=True)
        assert os.path.exists(out_file), "Output file should be created"
        logger.info("✓ add_exif_data_to_jpg_file invalid tags test passed")
    except Exception as e:
        logger.error(f"add_exif_data_to_jpg_file invalid tags test failed: {str(e)}")
        assert False


def test_insert_xmp_no_soi_marker():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing XMP Insertion with No SOI Marker ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        invalid_jpeg = output_dir + "/test_no_soi.jpg"
        with open(invalid_jpeg, 'wb') as f:
            f.write(b'This is not a JPEG file')
        _insert_xmp_into_jpeg(
            invalid_jpeg, b'<?xpacket begin="test"?><test>XMP</test>', verbose=True)
        logger.info("✓ XMP insertion no SOI marker test passed")
    except Exception as e:
        logger.error(f"XMP insertion no SOI marker test failed: {str(e)}")
        assert False


def test_insert_xmp_da_marker():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing XMP Insertion with 0xDA Marker ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        source_file = "examples/input/img-jpg/0001.jpg"
        if not os.path.exists(source_file):
            logger.warning("Source file not found, skipping test")
            assert False
        test_file = output_dir + "/test_da_marker.jpg"
        import shutil
        shutil.copy2(source_file, test_file)
        xmp_data = b'<?xpacket begin="test"?><test>XMP Data</test>'
        _insert_xmp_into_jpeg(test_file, xmp_data, verbose=True)
        with Image.open(test_file) as img:
            img.verify()
        logger.info("✓ XMP insertion with 0xDA marker test passed")
    except Exception as e:
        logger.error(f"XMP insertion with 0xDA marker test failed: {str(e)}")
        assert False


def test_png_16bit_warning():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing 16-bit PNG Warning ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        test_img = np.ones((100, 100, 3), dtype=np.uint16) * 32768
        out_file = output_dir + "/test_16bit.png"
        exif_data = {271: "Test Make", 272: "Test Model"}
        write_image_with_exif_data_png(exif_data, test_img, out_file)
        assert os.path.exists(out_file), "16-bit PNG should be created"
        logger.info("✓ 16-bit PNG warning test passed")
    except Exception as e:
        logger.error(f"16-bit PNG warning test failed: {str(e)}")
        assert False


def test_png_icc_profile():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing PNG ICC Profile ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        test_img = np.ones((100, 100, 3), dtype=np.uint8) * 128
        out_file = output_dir + "/test_icc_profile.png"
        icc_profile_data = b"fake_icc_profile_data_here"
        exif_with_icc = {
            271: "Test Make",
            272: "Test Model",
            "ICC_Profile": icc_profile_data,
            "icc_profile": icc_profile_data,  # Alternative key
        }
        write_image_with_exif_data_png(exif_with_icc, test_img, out_file)
        assert os.path.exists(out_file), "PNG with ICC profile should be created"
        with Image.open(out_file) as img:
            img.verify()
        logger.info("✓ PNG ICC profile test passed")
    except Exception as e:
        logger.error(f"PNG ICC profile test failed: {str(e)}")
        assert False


def test_xmp_bytes_decoding():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing XMP Bytes Decoding ========")
        test_cases = [
            {b'xmp_data': b'<?xpacket begin="test"?><test>bytes xmp</test>'},
            {'XML:com.adobe.xmp': b'<?xpacket begin="test"?><test>bytes xml</test>'},
            {'xml:com.adobe.xmp': 'string xmp data'},  # String input
        ]
        for exif_data in test_cases:
            test_img = np.ones((50, 50, 3), dtype=np.uint8) * 128
            output_dir = "output/img-exif"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            out_file = output_dir + "/test_xmp_bytes.png"
            write_image_with_exif_data_png(exif_data, test_img, out_file)
        logger.info("✓ XMP bytes decoding test passed")
    except Exception as e:
        logger.error(f"XMP bytes decoding test failed: {str(e)}")
        assert False


def test_add_exif_tags_to_pnginfo_skip_icc():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing PNG Info ICC Profile Skipping ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        test_img = np.ones((50, 50, 3), dtype=np.uint8) * 128
        exif_with_icc_keys = {
            "ICC_Profile": b"fake_icc_data",
            "icc_profile": b"more_fake_icc",
            "ICCPROFILE": "should be skipped",
            "Color Profile": "skip this too",
            "normal_tag": "this should be included",
            271: "Camera Make",  # Should be included
        }
        out_file = output_dir + "/test_icc_skip.png"
        write_image_with_exif_data_png(exif_with_icc_keys, test_img, out_file)
        assert os.path.exists(out_file), "Output file should exist"
        with Image.open(out_file) as img:
            if hasattr(img, 'text') and img.text:
                icc_tags = [key for key in img.text.keys()
                            if 'icc' in key.lower() or 'profile' in key.lower()]
                assert len(icc_tags) == 0, f"ICC tags should be skipped but found: {icc_tags}"
                assert "normal_tag" in img.text, "Normal tag should be included"
        logger.info("✓ ICC profile skipping test passed")
    except Exception as e:
        logger.error(f"ICC profile skipping test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_typed_tag_exception_handling():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing Typed Tag Exception Handling ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        test_img = np.ones((50, 50, 3), dtype=np.uint8) * 128
        problematic_exif = {
            # Bytes that will cause decode error
            "TestBytes": b'\xff\xfe\x00\x01\x02\x03',
            # Very large array that might cause issues
            "TestArray": list(range(1000)),
            # Normal values for array, int, float
            "TestInt": 42,
            "TestFloat": 3.14159,
            "TestArraySmall": [1, 2, 3],
        }
        out_file = output_dir + "/test_typed_tag_exceptions.png"
        write_image_with_exif_data_png(problematic_exif, test_img, out_file)
        assert os.path.exists(out_file), "Output file should be created despite exceptions"
        with Image.open(out_file) as img:
            img.verify()
        logger.info("✓ Typed tag exception handling test passed")
    except Exception as e:
        logger.error(f"Typed tag exception handling test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_add_exif_tag_exceptions():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing Add EXIF Tag Exceptions ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        test_img = np.ones((50, 50, 3), dtype=np.uint8) * 128
        problematic_exif = {
            # Very large binary data that might be rejected
            700: b'x' * 10000,  # XMLPACKET
            # Complex object that can't be easily serialized
            315: object(),  # Artist tag with invalid type
            # Normal values that should work
            271: "Test Make",
            272: "Test Model",
        }
        out_file = output_dir + "/test_exif_tag_exceptions.png"
        write_image_with_exif_data_png(problematic_exif, test_img, out_file)
        assert os.path.exists(out_file), "Output file should be created"
        logger.info("✓ Add EXIF tag exceptions test passed")
    except Exception as e:
        logger.error(f"Add EXIF tag exceptions test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_png_text_tag_exceptions():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing PNG Text Tag Exceptions ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        test_img = np.ones((50, 50, 3), dtype=np.uint8) * 128
        edge_case_exif = {
            "PNG_TestTag": "Value with PNG_ prefix",  # Should be cleaned
            "TestBinary": b'\xff\xfe\x00\x01',  # Binary data that's hard to decode
            "TestLongValue": "A" * 1000,  # Very long string
            "TestNormal": "Normal value",
        }
        out_file = output_dir + "/test_png_text_exceptions.png"
        write_image_with_exif_data_png(edge_case_exif, test_img, out_file)
        assert os.path.exists(out_file), "Output file should be created"
        with Image.open(out_file) as img:
            if hasattr(img, 'text') and img.text:
                assert "TestTag" in img.text, "PNG_ prefix should be removed"
                assert "PNG_TestTag" not in img.text, "Original PNG_ prefixed key should not exist"
        logger.info("✓ PNG text tag exceptions test passed")
    except Exception as e:
        logger.error(f"PNG text tag exceptions test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_extract_icc_profile_non_profile():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing Extract ICC Profile Non-Profile ========")
        test_exif = {
            "not_icc": b"some random data",
            "also_not_profile": "string data",
            271: "Camera Make",
        }
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        test_img = np.ones((50, 50, 3), dtype=np.uint8) * 128
        out_file = output_dir + "/test_no_icc.png"
        write_image_with_exif_data_png(test_exif, test_img, out_file)
        assert os.path.exists(out_file), "Output file should be created"
        logger.info("✓ Extract ICC profile non-profile test passed")
    except Exception as e:
        logger.error(f"Extract ICC profile non-profile test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_clean_data_for_tiff_rational():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing Clean Data for TIFF with Rational ========")
        rational = IFDRational(3, 4)
        result = clean_data_for_tiff(rational)
        assert result == (3, 4), f"IFDRational should be converted to tuple: {result}"
        assert clean_data_for_tiff("test") == "test"
        assert clean_data_for_tiff(b"test") == "test"
        assert clean_data_for_tiff(123) == 123
        logger.info("✓ Clean data for TIFF rational test passed")
    except Exception as e:
        logger.error(f"Clean data for TIFF rational test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_process_tiff_data_edge_cases():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing Process TIFF Data Edge Cases ========")
        zero_rational = IFDRational(1, 0)
        result = _process_tiff_data_safe(zero_rational)
        assert result == (3, 1, 1), f"Zero denominator should be converted to integer: {result}"
        normal_rational = IFDRational(2, 3)
        result = _process_tiff_data_safe(normal_rational)
        assert result == (5, 1, (2, 3)), f"Normal rational should work: {result}"
        integer_rational = IFDRational(5, 1)
        result = _process_tiff_data_safe(integer_rational)
        assert result == (3, 1, 5), f"Integer rational should be converted to integer: {result}"
        problematic_iterable = [1, "not_a_number", 3]
        result = _process_tiff_data_safe(problematic_iterable)
        assert result is None, f"Problematic iterable should return None: {result}"

        class UnserializableObject:
            def __str__(self):
                raise Exception("Can't serialize")

        bad_object = UnserializableObject()
        result = _process_tiff_data_safe(bad_object)
        assert result is None, f"Unserializable object should return None: {result}"
        logger.info("✓ Process TIFF data edge cases test passed")
    except Exception as e:
        logger.error(f"Process TIFF data edge cases test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_tiff_write_fallback():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing TIFF Write Fallback ========")
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        test_img = np.ones((100, 100, 3), dtype=np.uint8) * 128
        problematic_exif = {
            # Very large binary data that might cause issues with tifffile
            700: b'x' * 100000,  # Very large XML packet
            271: "Test Make",
            272: "Test Model",
        }
        out_file = output_dir + "/test_tiff_fallback.tif"
        write_image_with_exif_data_tif(problematic_exif, test_img, out_file)
        assert os.path.exists(out_file), "TIFF file should be created (possibly via fallback)"
        with Image.open(out_file) as img:
            img.verify()
        logger.info("✓ TIFF write fallback test passed")
    except Exception as e:
        logger.error(f"TIFF write fallback test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_exif_dict_exif_prefix():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing EXIF Dict with EXIF_ Prefix ========")
        test_exif = {
            "EXIF_CameraMake": "Test Make",
            "EXIF_CameraModel": "Test Model",
            "EXIF_ExposureTime": "1/100",
            "PNG_SomeTag": "Should be skipped",  # PNG_ prefixed should be skipped
            "normal_tag": "Should be included",
        }
        result = exif_dict(test_exif)
        assert "CameraMake" in result, "EXIF_ prefix should be removed"
        assert "CameraModel" in result, "EXIF_ prefix should be removed"
        assert "ExposureTime" in result, "EXIF_ prefix should be removed"
        assert "SomeTag" not in result, "PNG_ prefixed tags should be skipped"
        assert "normal_tag" in result, "Normal tags should be included"
        logger.info("✓ EXIF dict EXIF_ prefix test passed")
    except Exception as e:
        logger.error(f"EXIF dict EXIF_ prefix test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_print_exif_none():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("======== Testing Print EXIF with None ========")
        try:
            print_exif(None)
            assert False, "Should have raised RuntimeError for None EXIF"
        except RuntimeError as e:
            assert "Image has no exif data" in str(e)
            logger.info("✓ Correctly caught None EXIF in print_exif")
    except Exception as e:
        logger.error(f"Print EXIF with None test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def test_exif_round_trip_tiff_to_png():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing EXIF Round-Trip: TIFF -> PNG ========")
        source_tiff = "examples/input/img-exif/0000.tif"
        if not os.path.exists(source_tiff):
            logger.warning(f"Source file not found: {source_tiff}")
            assert False
        original_exif = get_exif(source_tiff)
        logger.info("*** Original TIFF EXIF ***")
        print_exif(original_exif)
        critical_tags = {
            271: "Make",
            272: "Model",
            306: "DateTime",
            315: "Artist",
            33432: "Copyright",
            33434: "ExposureTime",
            33437: "FNumber",
            34855: "ISOSpeedRatings",
            37386: "FocalLength",
            42036: "LensModel"
        }
        filtered_critical_tags = {
            tag_id: tag_name for tag_id, tag_name in critical_tags.items()
            if tag_id not in NO_COPY_TIFF_TAGS_ID
        }
        original_tag_count = sum(1 for tag_id in filtered_critical_tags if tag_id in original_exif)
        logger.info(f"Found {original_tag_count} critical tags in original TIFF")
        temp_png = output_dir + "/roundtrip_temp.png"
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        logger.info("*** Writing PNG with TIFF EXIF ***")
        write_image_with_exif_data(
            original_exif, test_image, temp_png, verbose=False, color_order='bgr')
        assert os.path.exists(temp_png), "PNG file was not created"
        png_exif = get_exif(temp_png, enhanced_png_parsing=True)
        logger.info("*** PNG EXIF (after writing) ***")
        print_exif(png_exif)
        png_tag_count = sum(1 for tag_id in filtered_critical_tags if tag_id in png_exif)
        logger.info(f"Preserved {png_tag_count}/{original_tag_count} critical tags in PNG")
        temp_tiff_roundtrip = output_dir + "/roundtrip_final.tif"
        logger.info("*** Writing TIFF with PNG EXIF ***")
        write_image_with_exif_data(png_exif, test_image, temp_tiff_roundtrip, verbose=False)
        assert os.path.exists(temp_tiff_roundtrip), "Final TIFF file was not created"
        final_exif = get_exif(temp_tiff_roundtrip)
        logger.info("*** Final TIFF EXIF (after PNG->TIFF round-trip) ***")
        print_exif(final_exif)
        final_tag_count = sum(1 for tag_id in filtered_critical_tags if tag_id in final_exif)
        logger.info(f"Preserved {final_tag_count}/{original_tag_count} critical tags in final TIFF")
        logger.info("=== Detailed EXIF Preservation Analysis ===")
        preserved_tags = []
        lost_tags = []
        for tag_id, tag_name in filtered_critical_tags.items():
            if tag_id in original_exif:
                original_value = original_exif[tag_id]
                png_value = png_exif.get(tag_id)
                final_value = final_exif.get(tag_id)
                if png_value is not None:
                    if _values_equal(original_value, png_value):
                        preserved_tags.append((f"PNG:{tag_name}", original_value, png_value))
                    else:
                        lost_tags.append(
                            (f"PNG:{tag_name}", original_value, png_value, "value changed in PNG"))
                else:
                    lost_tags.append(
                        (f"PNG:{tag_name}", original_value, None, "tag missing in PNG"))
                if final_value is not None:
                    if _values_equal(original_value, final_value):
                        preserved_tags.append(
                            (f"FINAL:{tag_name}", original_value, final_value))
                    else:
                        lost_tags.append(
                            (f"FINAL:{tag_name}", original_value, final_value,
                             "value changed in final"))
                else:
                    lost_tags.append(
                        (f"FINAL:{tag_name}", original_value, None, "tag missing in final"))
        logger.info("✓ PRESERVED TAGS:")
        for tag_name, orig_val, final_val in preserved_tags:
            logger.info(f"  {tag_name}: {orig_val} -> {final_val}")
        if lost_tags:
            logger.info("✗ LOST/CHANGED TAGS:")
            for tag_name, orig_val, final_val, reason in lost_tags:
                logger.info(f"  {tag_name}: {orig_val} -> {final_val} ({reason})")
        total_possible_preservations = 0
        actual_preservations = 0
        for tag_id, tag_name in filtered_critical_tags.items():
            if tag_id in original_exif:
                total_possible_preservations += 2
                if tag_id in png_exif and \
                        _values_equal(original_exif[tag_id], png_exif[tag_id]):
                    actual_preservations += 1
                if tag_id in final_exif and \
                        _values_equal(original_exif[tag_id], final_exif[tag_id]):
                    actual_preservations += 1
        if total_possible_preservations > 0:
            preservation_rate = (actual_preservations / total_possible_preservations) * 100
            logger.info(f"=== FINAL RESULT: {preservation_rate:.1f}% preservation rate ===")
            logger.info(f"({actual_preservations}/{total_possible_preservations} checks passed)")
            if preservation_rate >= 90:
                logger.info("✓ TIFF->PNG EXIF round-trip test PASSED")
            else:
                logger.warning(
                    msg="⚠ TIFF->PNG EXIF round-trip test: "
                    "Low preservation rate ({preservation_rate:.1f}%)")
                assert False
        else:
            logger.warning("No critical tags found to compare")
        for temp_file in [temp_png, temp_tiff_roundtrip]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.info(f"Cleaned up: {temp_file}")
    except Exception as e:
        logger.error(f"TIFF->PNG round-trip test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


def _values_equal(val1, val2):
    if hasattr(val1, 'numerator') and hasattr(val2, 'numerator'):
        return float(val1) == float(val2)
    elif isinstance(val1, bytes) and isinstance(val2, bytes):
        return val1 == val2
    else:
        return str(val1) == str(val2)


def test_exif_jpg_icc_profile():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        output_dir = "output/img-exif"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        logger.info("======== Testing JPG ICC Profile ========")
        dummy_icc = b"fake_icc_profile_data_" + b"x" * 100
        logger.info("*** Test 1: Writing JPEG with ICC profile ***")
        out_filename = output_dir + "/test_icc.jpg"
        test_exif = {
            271: "Test Camera",  # Make
            272: "Test Model",   # Model
            305: "Test Software",
            34675: dummy_icc,    # INTERCOLORPROFILE
        }
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        write_image_with_exif_data(test_exif, test_image, out_filename, verbose=True)
        written_exif = get_exif(out_filename)
        logger.info("*** Written JPG EXIF ***")
        print_exif(written_exif)
        if 34675 in written_exif:
            icc_data = written_exif[34675]
            logger.info(f"ICC profile found in written JPEG: {len(icc_data)} bytes")
            assert isinstance(icc_data, bytes), "ICC profile should be bytes"
            assert len(icc_data) > 0, "ICC profile should not be empty"
        else:
            logger.warning("No ICC profile found in written JPEG")
        logger.info("*** Test 2: Round-trip ICC profile preservation ***")
        if os.path.exists("examples/input/img-jpg/0000.jpg"):
            source_exif = get_exif("examples/input/img-jpg/0000.jpg")
            source_image = read_img("examples/input/img-jpg/0000.jpg")
            if 34675 not in source_exif:
                source_exif[34675] = dummy_icc
            roundtrip_file = output_dir + "/test_icc_roundtrip.jpg"
            write_image_with_exif_data(source_exif, source_image, roundtrip_file, verbose=True)
            roundtrip_exif = get_exif(roundtrip_file)
            if 34675 in roundtrip_exif:
                logger.info(f"ICC preserved in round-trip: {len(roundtrip_exif[34675])} bytes")
            else:
                logger.warning("ICC not preserved in round-trip")
        logger.info("✓ JPG ICC profile test completed")
    except Exception as e:
        logger.error(f"JPG ICC profile test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        assert False


if __name__ == '__main__':
    test_exif_tiff()
    test_exif_jpg()
    test_exif_png()
    test_write_image_with_exif_data_jpg()
    test_write_image_with_exif_data_tiff()
    test_write_image_with_exif_data_png()
    test_get_exif_from_png_with_metadata()
    test_extract_enclosed_data_for_jpg()
    test_exif_extra_tags_for_tif()
    test_write_image_with_exif_data_png_edge_cases()
    test_save_exif_data_different_formats()
    test_exif_dict_functionality()
    test_error_handling()
    test_print_exif_edge_cases()
    test_exif_decoding_error()
    test_safe_decode_bytes()
    test_exif_exposure_data_detection()
    test_exif_subifd_exposure_preservation()
    test_exif_tiff_with_subifd_data()
    test_real_world_tiff_with_exif()
    test_exif_round_trip_tiff_to_jpg()
    test_pil_exif_basic()
    test_jpg_to_jpg_vs_tiff_to_jpg()
    test_png_metadata_enhancement()
    test_enhanced_png_exif()
    test_unified_exif_with_enhanced_png()
    test_exif_round_trip_jpg_to_png_to_jpg()
    test_png_string_tags()
    test_add_exif_data_to_jpg_file_error_handling()
    test_write_image_with_exif_data_error_handling()
    test_copy_exif_error_handling()
    test_exif_subifd_exception_handling()
    test_get_exif_fallback()
    test_get_exif_from_png_no_data()
    test_xmp_data_decoding()
    test_rational_parsing_edge_cases()
    test_iso_parsing_error()
    test_typed_png_text_parsing()
    test_enhanced_exif_xmp_from_basic()
    test_safe_decode_bytes_edge_cases()
    test_add_exif_data_to_jpg_file_none_exif()
    test_add_exif_data_to_jpg_file_same_file()
    test_add_exif_data_to_jpg_file_invalid_tags()
    test_insert_xmp_no_soi_marker()
    test_insert_xmp_da_marker()
    test_png_16bit_warning()
    test_png_icc_profile()
    test_xmp_bytes_decoding()
    test_add_exif_tags_to_pnginfo_skip_icc()
    test_typed_tag_exception_handling()
    test_add_exif_tag_exceptions()
    test_png_text_tag_exceptions()
    test_extract_icc_profile_non_profile()
    test_clean_data_for_tiff_rational()
    test_process_tiff_data_edge_cases()
    test_tiff_write_fallback()
    test_exif_dict_exif_prefix()
    test_print_exif_none()
    test_exif_round_trip_tiff_to_png()
    test_exif_jpg_icc_profile()


def test_tiff_exif_tags_in_exif_ifd(tmp_path):
    """Exif-only tags (exposure, f-number, ISO, lens, ...) are written to the
    Exif IFD that tag 34665 points to, not to the image IFD, where libtiff and
    OpenCV report them as unknown fields."""
    import numpy as np
    import tifffile
    from PIL.TiffImagePlugin import IFDRational
    from shinestacker.algorithms.exif_tiff import write_image_with_exif_data_tif
    exif = {271: "Sony", 272: "ILCE-7RM5", 306: "2026:10:19 16:06:49",
            33434: IFDRational(1, 20), 33437: IFDRational(90, 10), 34855: 100,
            36867: "2026:10:19 16:06:49", 37386: IFDRational(1000, 10),
            42036: "FE 100mm F2.8 Macro GM OSS"}
    img = np.random.default_rng(0).integers(0, 65535, (32, 48, 3), dtype=np.uint16)
    out = str(tmp_path / "out.tif")
    write_image_with_exif_data_tif(exif, img, out)
    with tifffile.TiffFile(out) as tif:
        page = tif.pages[0]
        assert not any(33434 <= t <= 33437 or 34850 <= t <= 34867 or t >= 36864 and t != 34675
                       for t in page.tags.keys() if t != 34665 and t != 34675)
        sub = page.tags[34665].value
        assert sub["ExposureTime"] == (1, 20) and sub["FNumber"] == (90, 10)
        assert sub["ISOSpeedRatings"] == 100 and sub["LensModel"] == "FE 100mm F2.8 Macro GM OSS"
        assert page.tags[271].value == "Sony"
        assert np.array_equal(page.asarray()[..., ::-1], img)
