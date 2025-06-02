import sys
sys.path.append('../')
from focus_stack.stack_framework import StackJob
from focus_stack.stack import FocusStack, FocusStackBunch
from focus_stack.pyramid import PyramidStack
from focus_stack.pyramid_sequential import PyramidSequentialStack
from focus_stack.depth_map import DepthMapStack


def test_jpg():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-pyramid", PyramidStack(),
                                  output_path="output/img-jpg-stack", postfix='_pyr'))
        job.run()
    except Exception:
        assert False


def test_tif():
    try:
        job = StackJob("job", "./", input_path="input/img-tif")
        job.add_action(FocusStack("stack-pyramid", PyramidStack(),
                                  output_path="output/img-tif-stack", postfix='_pyr'))
        job.run()
    except Exception:
        assert False


def test_jpg_dm():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-depthmap", DepthMapStack(),
                                  output_path="output/img-jpg-stack", postfix='_dm'))
        job.run()
    except Exception:
        assert False


def test_jpg_seq():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-sequential", PyramidSequentialStack(),
                                  output_path="output/img-jpg-stack-seq", postfix='_pyr'))
        job.run()
    except Exception:
        assert False


def test_tif_seq():
    try:
        job = StackJob("job", "./", input_path="input/img-tif")
        job.add_action(FocusStack("stack-sequential", PyramidSequentialStack(),
                                  output_path="output/img-tif-stack-seq", postfix='_pyr'))
        job.run()
    except Exception:
        assert False


def test_bunches():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(FocusStackBunch("stack-pyramid", PyramidStack(),
                                       output_path="output/img-jpg-bunches", frames=3))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_jpg()
    test_tif()
    test_jpg_seq()
    test_tif_seq()
    test_jpg_dm()
    test_bunches()
