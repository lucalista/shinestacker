import os
from focusstack.algorithms.stack_framework import StackJob
from focusstack.algorithms.multilayer import MultiLayer, write_multilayer_tiff, read_multilayer_tiff

test_path = "output/img-tif-multi"
test_file = "/multi-out.tif"
N_LAYERS = 6


def test_write():
    try:
        output_dir = test_path
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        filenames = ["output/img-tif-stack/0000_pyr.tif"] + [f"input/img-tif/000{i}.tif" for i in range(N_LAYERS)]
        labels = ['Pyramid'] + [f'Layer {i + 1}' for i in range(N_LAYERS)]
        write_multilayer_tiff(filenames, output_dir + test_file, labels=labels, exif_path="input/img-tif")
    except Exception:
        assert False


def test_read():
    try:
        input_dir = test_path
        isd = read_multilayer_tiff(input_dir + test_file)
        assert isd is not None
        assert len(isd.layers.layers) == N_LAYERS + 1
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
        job.add_action(MultiLayer("multi", output_path="output/img-tif-multilayer",
                                  input_path=["output/img-tif-stack", "input/img-tif"],
                                  exif_path='input/img-tif',
                                  reverse_order=True))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_write()
    test_read()
    test_jpg()
    test_tif()
