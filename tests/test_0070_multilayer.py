import sys
sys.path.append('../')
from focus_stack import StackJob, MultiLayer


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
    test_jpg()
    test_tif()
