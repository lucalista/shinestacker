import os
from shinestacker.algorithms.stack_framework import StackJob
from shinestacker.algorithms.multilayer import MultiLayer, write_multilayer_tiff, read_multilayer_tiff

test_path = "output/img-tif-multi"
test_file = "/multi-out.tif"
N_LAYERS = 6


def test_write_tif():
    try:
        output_dir = test_path
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        filenames = [f"examples/input/img-tif/000{i}.tif" for i in range(N_LAYERS)]
        labels = [f'Layer {i + 1}' for i in range(N_LAYERS)]
        write_multilayer_tiff(filenames, output_dir + test_file, labels=labels,
                              exif_path="examples/input/img-tif")
    except Exception:
        assert False


def test_write_jpg():
    try:
        output_dir = test_path
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        filenames = [f"examples/input/img-jpg/000{i}.jpg" for i in range(N_LAYERS)]
        labels = [f'Layer {i + 1}' for i in range(N_LAYERS)]
        write_multilayer_tiff(filenames, output_dir + test_file, labels=labels,
                              exif_path="examples/input/img-jpg")
    except Exception:
        assert False


def test_read():
    try:
        input_dir = test_path
        isd = read_multilayer_tiff(input_dir + test_file)
        assert isd is not None
        assert len(isd.layers.layers) == N_LAYERS
    except Exception:
        assert False


def test_jpg():
    try:
        job = StackJob("job", "examples/", input_path="input/img-jpg")
        job.add_action(MultiLayer("multi", output_path="output/img-jpg-multilayer",
                                  input_path=["output/img-jpg-stack", "input/img-jpg"],
                                  reverse_order=True))
        job.run()
    except Exception:
        assert False


def test_tif():
    try:
        job = StackJob("job", "examples/", input_path="input/img-tif")
        job.add_action(MultiLayer("multi", output_path="output/img-tif-multilayer",
                                  input_path=["output/img-tif-stack", "input/img-tif"],
                                  exif_path='input/img-tif',
                                  reverse_order=True))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_write_tif()
    test_write_jpg()
    test_read()
    test_jpg()
    test_tif()
