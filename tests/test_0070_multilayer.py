import sys
import os
sys.path.append('../')
from algorithms.stack_framework import StackJob
from algorithms.multilayer import MultiLayer, write_multilayer_tiff

def test_function():
    try:
        output_dir = "output/img-tif-multi"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        write_multilayer_tiff([f"input/img-tif/000{i}.tif" for i in range(5)],
                              output_dir + "/multi-out.tif",
                              exif_path="input/img-tif")
    except Exception:
        assert False


def test_jpg():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(MultiLayer("multi", output_path="output/img-jpg-multilayer",
                                  input_path=["input/img-jpg", "output/img-jpg-stack"],
                                  reverse_order=True))
        job.run()
    except Exception:
        assert False


def test_tif():
    try:
        job = StackJob("job", "./", input_path="input/img-tif")
        job.add_action(MultiLayer("multi", output_path="output/img-tiff-multilayer",
                                  input_path=["input/img-tif", "output/img-tif-stack"],
                                  exif_path='input/img-tif',
                                  reverse_order=True))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_function()
    test_jpg()
    test_tif()
