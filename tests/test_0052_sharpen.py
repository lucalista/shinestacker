import os
from shinestacker.algorithms.sharpen import unsharp_mask
from shinestacker.algorithms.utils import read_img, write_img

out_path = "tests/output/sharpen"


def test_unsharpen_mask_8bit():
    img = read_img("examples/input/img-jpg/0002.jpg")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        sharp = unsharp_mask(img, radius=2.0, amount=1.5, threshold=10)
        write_img(f"{out_path}/test-unsharpen-mask.jpg", sharp)
        assert True
    except Exception:
        assert False


def test_unsharpen_mask_16bit():
    img = read_img("examples/input/img-tif/0002.tif")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        sharp = unsharp_mask(img, radius=3.0, amount=2.0, threshold=10)
        write_img(f"{out_path}/test-unsharpen-mask.tif", sharp)
        assert True
    except Exception:
        assert False


if __name__ == '__main__':
    test_unsharpen_mask_8bit()
    test_unsharpen_mask_16bit()
