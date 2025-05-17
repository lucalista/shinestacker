import sys
sys.path.append('../')
import os
from PIL import Image, ExifTags
from PIL.ExifTags import TAGS
import tifffile
import logging
from focus_stack.utils import copy_exif, print_exif, NO_COPY_TIFF_TAGS
from focus_stack.logging import setup_logging

def test_exif_jpg():
    try:
        setup_logging()
        output_dir = "./img-exif";
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        out_filename = output_dir + "/0001.jpg"
        logging.getLogger(__name__).info("*** Source JPG EXIF ***" )
        exif = copy_exif("./img-jpg/0000.jpg", "./img-jpg/0001.jpg", out_filename=out_filename, verbose=True)
        image = Image.open(out_filename)
        exif_copy = image.tag_v2 if hasattr(image, 'tag_v2') else image.getexif()
        ext = out_filename.split(".")[-1]
        logging.getLogger(__name__).info("*** Copy JPG EXIF ***" )
        print_exif(exif_copy, ext)
        for tag, tag_copy in zip(exif, exif_copy):
            data = exif.get(tag)
            data_copy = exif_copy.get(tag_copy)
            if isinstance(data, bytes): data=data.decode()
            if isinstance(data_copy, bytes): data_copy=data_copy.decode()
            if not (tag == tag_copy and data==data_copy):
                logging.getLogger(__name__).error(f"JPG EXIF data don't match: {tag}=>{data}, {tag_copy}=>{data_copy}" )
                assert False
    except:
        assert False

def common_entries(*dcts):
    if not dcts:
        return
    for i in set(dcts[0]).intersection(*dcts[1:]):
        yield (i,) + tuple(d[i] for d in dcts)

def test_exif_tiff():
    try:
        setup_logging()
        output_dir = "./img-exif";
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        out_filename = output_dir + "/0001.tif"
        logging.getLogger(__name__).info("*** Source TIFF EXIF ***" )
        exif = copy_exif("./img-tif/0000.tif", "./img-tif/0001.tif", out_filename=out_filename, verbose=True)
        image = Image.open(out_filename)
        exif_copy = image.tag_v2 if hasattr(image, 'tag_v2') else image.getexif()
        ext = out_filename.split(".")[-1]
        logging.getLogger(__name__).info("*** Copy TIFF EXIF ***" )
        print_exif(exif_copy, ext)
        meta, meta_copy = {}, {}
        for tag_id, tag_id_copy in zip(exif, exif_copy):
            tag = TAGS.get(tag_id, tag_id)
            tag_copy = TAGS.get(tag_id_copy, tag_id_copy)
            data = exif.get(tag_id)
            data_copy = exif_copy.get(tag_id_copy)
            if isinstance(data, bytes):
                try:
                    data = data.decode()
                except:
                    logging.getLogger(__name__).warning(f"Can't decode EXIF tag {tag:25} [#{tag_id}]")
                    data = '<<< decode error >>>'
            if isinstance(data_copy, bytes): data_copy=data_copy.decode()
            meta[tag] = data
            meta_copy[tag_copy] = data_copy
        for (tag, data, data_copy) in list(common_entries(meta, meta_copy)):
            if tag not in NO_COPY_TIFF_TAGS:
                if not data==data_copy:
                    logging.getLogger(__name__).error(f"TIFF EXIF data don't match: {tag}: {data}=>{data_copy}" )
                    assert False
    except:
        assert False

if __name__ == '__main__':
    test_exif_tiff()
    test_exif_jpg()
