from shinestacker.algorithms.stack_framework import StackJob
from shinestacker.algorithms.stack import FocusStack, FocusStackBunch
from shinestacker.algorithms.pyramid import PyramidStack
from shinestacker.algorithms.pyramid_tiles import PyramidTilesStack
from shinestacker.algorithms.pyramid_auto import PyramidAutoStack
from shinestacker.algorithms.depth_map import DepthMapStack


def test_jpg():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-pyramid", PyramidStack(),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  prefix='pyr_'))
        job.run()
    except Exception:
        assert False


def test_jpg_filter():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-pyramid", PyramidStack(),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  denoise_amount=0.1, sharpen_amount_percent=10,
                                  prefix='pyr_'))
        job.run()
    except Exception:
        assert False


def test_tif():
    try:
        job = StackJob("job", "examples", input_path="input/img-tif")
        job.add_action(FocusStack("stack-pyramid-tiff", PyramidStack(),
                                  output_path="output/img-tif-stack",
                                  delete_output_at_end=True,
                                  prefix='pyr_'))
        job.run()
    except Exception:
        assert False


def test_jpg_dm():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-depthmap", DepthMapStack(),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  prefix='dm_'))
        job.run()
    except Exception:
        assert False


def test_jpg_dm_plot():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-depthmap", DepthMapStack(plot_depth_map=True),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  prefix='dm_'))
        job.run()
    except Exception:
        assert False


def test_jpg_pt_1():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-depthmap", PyramidTilesStack(),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  prefix='pyr_tiles_'))
        job.run()
    except Exception:
        assert False


def test_jpg_pt_2():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-depthmap", PyramidTilesStack(max_threads=1),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  prefix='pyr_tiles_'))
        job.run()
    except Exception:
        assert False


def test_jpg_auto_1():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-depthmap", PyramidAutoStack(),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  prefix='pyr_tiles_'))
        job.run()
    except Exception:
        assert False


def test_jpg_auto_2():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-depthmap", PyramidAutoStack(memory_limit=0.2),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  prefix='pyr_tiles_'))
        job.run()
    except Exception:
        assert False


def test_bunches():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStackBunch("stack-pyramid-bunch", PyramidStack(),
                                       output_path="output/img-jpg-bunches",
                                       delete_output_at_end=True,
                                       frames=3))
        job.run()
    except Exception:
        assert False


def test_jpg_template():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStack("stack-pyramid", PyramidStack(),
                                  output_path="output/img-jpg-stack",
                                  delete_output_at_end=True,
                                  output_file_template="{method}_{input_count}frames_stack"))
        job.run()
    except Exception:
        assert False


def test_bunches_template():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg")
        job.add_action(FocusStackBunch("stack-pyramid-bunch", PyramidStack(),
                                       output_path="output/img-jpg-bunches",
                                       delete_output_at_end=True,
                                       frames=3,
                                       output_file_template="{method}_{input_count}frames_bunch-{bunch_index:03d}"))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_jpg()
    test_jpg_filter()
    test_tif()
    test_jpg_dm()
    test_jpg_dm_plot()
    test_jpg_pt_1()
    test_jpg_pt_2()
    test_jpg_auto_1()
    test_jpg_auto_2()
    test_bunches()
    test_jpg_template()
    test_bunches_template()