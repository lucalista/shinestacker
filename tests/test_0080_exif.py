import sys
sys.path.append('../')
import os
from PIL import Image, ExifTags
import logging
from focus_stack.utils import copy_exif, print_exif
from focus_stack.logging import setup_logging

def test_exif():
    try:
        setup_logging()
        output_dir = "./img-exif";
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        out_filename = output_dir + "/0001.jpg"
        logging.getLogger(__name__).info("*** Source EXIF ***" )
        exif = copy_exif("./img-jpg/0000.jpg", "./img-jpg/0001.jpg", out_filename=out_filename, verbose=True)
        image = Image.open(out_filename)
        exif_copy = image.tag_v2 if hasattr(image, 'tag_v2') else image.getexif()
        ext = out_filename.split(".")[-1]
        logging.getLogger(__name__).info("*** Copy EXIF ***" )
        print_exif(exif_copy, ext)
        for tag, tag_copy in zip(exif, exif_copy):
            data = exif.get(tag)
            data_copy = exif_copy.get(tag_copy)
            if isinstance(data, bytes): data=data.decode()
            if isinstance(data_copy, bytes): data_copy=data_copy.decode()
            if not (tag == tag_copy and data==data_copy):
                logging.getLogger(__name__).error(f"EXIF data don't match: {tag}=>{data}, {tag_copy}=>{data_copy}" )
            assert tag == tag_copy and data==data_copy
    except:
        assert False

if __name__ == '__main__':
    test_exif()
