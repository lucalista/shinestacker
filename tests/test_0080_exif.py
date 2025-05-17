import sys
sys.path.append('../')
import os
from focus_stack.utils import copy_exif
from focus_stack.logging import setup_logging

def test_exif():
    try:
        setup_logging()
        output_dir = "./img-exif";
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        copy_exif("./img-jpg/0000.jpg", "./img-jpg/0001.jpg", out_filename=output_dir + "/0001.jpg", verbose=True)
    except:
        assert False

if __name__ == '__main__':
    test_exif()
