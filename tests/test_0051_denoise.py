import os
from shinestacker.algorithms.denoise import denoise
from shinestacker.algorithms.utils import read_img, write_img

out_path = "tests/output/denoise"


def test_denoise_8bit():
    img = read_img("examples/input/img-jpg/0002.jpg")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        den = denoise(img, 10)
        write_img(f"{out_path}/test-denoise.jpg", den)
        assert True
    except Exception:
        assert False


def test_denoise_16bit():
    img = read_img("examples/input/img-tif/0002.tif")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        den = denoise(img, 10)
        write_img(f"{out_path}/test-denoise.tif", den)
        assert True
    except Exception:
        assert False


if __name__ == '__main__':
    test_denoise_8bit()
    test_denoise_16bit()
