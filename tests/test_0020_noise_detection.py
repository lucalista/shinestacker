import matplotlib
matplotlib.use('Agg')
import logging
from shinestacker.config.constants import constants
from shinestacker.core.logging import setup_logging
from shinestacker.core.exceptions import ShapeError, BitDepthError
from shinestacker.algorithms.stack_framework import StackJob, CombinedActions
from shinestacker.algorithms.noise_detection import mean_image, NoiseDetection, MaskNoise


def check_fail_size(extension, directory, ExepctionType, files):
    logger = logging.getLogger()
    shape_err = False
    try:
        mean_image(["output/" + directory + f"/image{i}." + extension for i in files],
                   message_callback=lambda msg: logger.info(msg))
    except ExepctionType:
        shape_err = True
    assert shape_err


def test_detect_fail_1():
    setup_logging(
        console_level=logging.DEBUG,
        file_level=logging.DEBUG,
        log_file=f"logs/{constants.APP_STRING.lower()}.log"
    )
    check_fail_size("jpg", "img-jpg-wrong-size", ShapeError, (1, 2))


def test_detect_fail_2():
    check_fail_size("tif", "img-tif-wrong-size", ShapeError, (1, 2))


def test_detect_fail_3():
    check_fail_size("tif", "img-tif-wrong-type", BitDepthError, ("_8bit", "_16bit"))


def test_detect():
    try:
        job = StackJob("job", "examples/", input_path="input/img-noise", callbacks='tqdm')
        job.add_action(NoiseDetection(plot_histograms=True))
        job.run()
    except Exception:
        assert False


def test_correct():
    try:
        job = StackJob("job", "examples/", input_path="input/img-jpg", callbacks='tqdm')
        job.add_action(CombinedActions("noise", [MaskNoise()], output_path="output/img-noise-corr"))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_detect_fail_1()
    test_detect_fail_2()
    test_detect_fail_3()
    test_detect()
    test_correct()
