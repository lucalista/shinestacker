
import os
from shinestacker.algorithms.white_balance import white_balance_from_rgb
from shinestacker.algorithms.utils import read_img, write_img

out_path = "tests/output/white-balance"

target_rgb = (246, 233, 178)


def test_wb_8bit():
    img = read_img("examples/input/img-jpg/0002.jpg")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        wb = white_balance_from_rgb(img, target_rgb)
        write_img(f"{out_path}/test-wb.jpg", wb)
        assert True
    except Exception:
        assert False


def test_wb_16bit():
    img = read_img("examples/input/img-tif/0002.tif")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        wb = white_balance_from_rgb(img, target_rgb)
        write_img(f"{out_path}/test-wb.tif", wb)
        assert True
    except Exception:
        assert False


if __name__ == '__main__':
    test_wb_8bit()
    test_wb_16bit()
