from shinestacker.algorithms.denoise import denoise
from shinestacker.algorithms.utils import read_img


def test_denoise_8bit():
    img = read_img("examples/input/img-jpg/0002.jpg")
    try:
        denoise(img, 0.8, 0.8)
        assert True
    except Exception:
        assert False


def test_denoise_16bit():
    img = read_img("examples/input/img-tif/0002.tif")
    try:
        denoise(img, 0.8, 0.8)
        assert False
    except Exception as e:
        assert str(e) == "denoise only supports 8 bit images"


if __name__ == '__main__':
    test_denoise_8bit()
    test_denoise_16bit()
