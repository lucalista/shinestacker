import sys
sys.path.append('../')
from algorithms.stack_framework import StackJob
from algorithms.stack import FocusStack, FocusStackBunch
from algorithms.pyramid import PyramidStack
from algorithms.pyramid_block import PyramidBlock
from algorithms.depth_map import DepthMapStack


def test_jpg():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-pyramid", PyramidStack(),
                                  output_path="output/img-jpg-stack", prefix='pyr_'))
        job.run()
    except Exception:
        assert False


def test_jpg_block():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-pyramid-block", PyramidBlock(),
                                  output_path="output/img-jpg-block", prefix='pyr_'))
        job.run()
    except Exception:
        assert False


def test_tif():
    try:
        job = StackJob("job", "./", input_path="input/img-tif")
        job.add_action(FocusStack("stack-pyramid-tiff", PyramidStack(),
                                  output_path="output/img-tif-stack", prefix='pyr_'))
        job.run()
    except Exception:
        assert False


def test_jpg_dm():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-depthmap", DepthMapStack(),
                                  output_path="output/img-jpg-stack", prefix='dm_'))
        job.run()
    except Exception:
        assert False


def test_bunches():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(FocusStackBunch("stack-pyramid-bunch", PyramidStack(),
                                       output_path="output/img-jpg-bunches", frames=3))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_jpg()
    test_jpg_block()
    test_tif()
    test_jpg_dm()
    test_bunches()
