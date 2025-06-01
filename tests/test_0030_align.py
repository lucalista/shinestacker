import sys
sys.path.append('../')
from focus_stack.utils import read_img
from focus_stack.align import align_images
from focus_stack import StackJob, Actions, AlignFrames

def test_align():
    img_1, img_2 = [read_img(f"input/img-jpg/000{i}.jpg") for i in (2, 3)]
    n_good_matches, img_warp = align_images(img_1, img_2)
    assert img_warp is not None
    assert n_good_matches > 100

def test_jpg():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(Actions("align-jpg", output_path="output/img-jpg-align",
                               actions=[AlignFrames(plot_config={'enabled': True})]))
        job.run()
    except Exception:
        assert False


def test_tif():
    try:
        job = StackJob("job", "./", input_path="input/img-tif")
        job.add_action(Actions("align-tif", output_path="output/img-tif-align",
                               actions=[AlignFrames(plot_config={'enabled': True})]))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_align()
    test_jpg()
    test_tif()
