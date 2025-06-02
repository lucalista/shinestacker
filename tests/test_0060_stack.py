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
        job.add_action(FocusStack("stack", PyramidStack(),
                                  output_path="output/img-jpg-stack", postfix='_pyr'))
        job.run()
    except Exception:
        assert False


def test_tif():
    try:
        job = StackJob("job", "./", input_path="input/img-tif")
        job.add_action(FocusStack("stack", PyramidStack(),
                                  output_path="output/img-tif-stack", postfix='_pyr'))
        job.run()
    except Exception:
        assert False


def test_jpg_dm():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(FocusStack("stack", DepthMapStack(),
                                  output_path="output/img-jpg-stack", postfix='_dm'))
        job.run()
    except Exception:
        assert False


def test_jpg_seq():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(FocusStack("stack", PyramidSequentialStack(),
                                  output_path="output/img-jpg-stack-seq", postfix='_pyr'))
        job.run()
    except Exception:
        assert False


def test_bunches():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(FocusStackBunch("stack", PyramidStack(),
                                       output_path="output/img-jpg-bunches", frames=3))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_jpg_seq()
    test_jpg()
    test_tif()
    test_jpg_dm()
    test_bunches()
