import sys
sys.path.append('../')
from focus_stack import StackJob, NoiseDetection, Actions, MaskNoise
from focus_stack.noise_detection import mean_image
from focus_stack.exceptions import ShapeError, BitDepthError
from focus_stack.logging import setup_logging
import logging


def check_fail_size(p):
    logger = logging.getLogger()
    shape_err = False
    try:
        mean_image([f"output/img-jpg-wrong-size/image{i}.jpg" for i in (1, 2)],
                   update_message_callback=lambda msg: logger.info(msg))
    except ShapeError:
        shape_err = True
    assert shape_err


def test_detect_fail_1():
    setup_logging(
        console_level=logging.DEBUG,
        file_level=logging.DEBUG,
        log_file="logs/focusstack.log"
    )
    check_fail_size("jpg")


def test_detect_fail_2():
    check_fail_size("tif")


def test_fail_type():
    logger = logging.getLogger()
    type_err = False
    try:
        mean_image([f"output/img-tif-wrong-type/image_{i}bit.tif" for i in (8, 16)],
                   update_message_callback=lambda msg: logger.info(msg))
    except BitDepthError:
        type_err = True
    assert type_err


def test_detect():
    try:
        job = StackJob("job", "./", input_path="input/img-noise")
        job.add_action(NoiseDetection())
        job.run()
    except Exception:
        assert False


def test_correct():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(Actions("noise", output_path="output/img-noise-corr", actions=[MaskNoise()]))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_detect_fail_1()
    test_detect_fail_2()
    test_fail_type()
    test_detect()
    test_correct()
