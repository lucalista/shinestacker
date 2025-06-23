import sys
sys.path.append('../')
from config.constants import constants
from focus_stack.utils import read_img
from focus_stack.stack_framework import StackJob, CombinedActions
from focus_stack.align import align_images, AlignFrames, RAISE_ORB_ORB_HAMMING


def test_align():
    try:
        img_1, img_2 = [read_img(f"input/img-jpg/000{i}.jpg") for i in (2, 3)]
        n_good_matches, img_warp = align_images(img_1, img_2)
        assert img_warp is not None
        assert n_good_matches > 100
    except Exception:
        assert False


def test_align_2():
    try:
        img_1, img_2 = [read_img(f"input/img-jpg/000{i}.jpg") for i in (2, 3)]
        n_good_matches, img_warp = align_images(img_1, img_2,
                                                feature_config={'detector': constants.DETECTOR_ORB,
                                                                'descriptor': constants.DESCRIPTOR_SIFT})
        assert img_warp is not None
        assert n_good_matches > 100
    except Exception:
        assert False


def test_align_3():
    try:
        img_1, img_2 = [read_img(f"input/img-jpg/000{i}.jpg") for i in (2, 3)]
        n_good_matches, img_warp = align_images(img_1, img_2,
                                                feature_config={'detector': constants.DETECTOR_ORB,
                                                                'descriptor': constants.DESCRIPTOR_ORB},
                                                matching_config={'method': constants.MATCHING_NORM_HAMMING})
        assert img_warp is not None
        assert n_good_matches > 100
    except Exception:
        assert False


def test_align_4():
    try:
        img_1, img_2 = [read_img(f"input/img-jpg/000{i}.jpg") for i in (2, 3)]
        n_good_matches, img_warp = align_images(img_1, img_2,
                                                feature_config={'detector': constants.DETECTOR_ORB,
                                                                'descriptor': constants.DESCRIPTOR_ORB},
                                                matching_config={'method': constants.MATCHING_KNN})
        assert img_warp is not None
        assert n_good_matches > 100
    except RuntimeError as e:
        assert str(e) == RAISE_ORB_ORB_HAMMING
    except Exception:
        assert False


def test_jpg():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg", callbacks='tqdm')
        job.add_action(CombinedActions("align-jpg", [AlignFrames(plot_summary=True)],
                                       output_path="output/img-jpg-align"))
        job.run()
    except Exception:
        assert False


def test_tif():
    try:
        job = StackJob("job", "./", input_path="input/img-tif", callbacks='tqdm')
        job.add_action(CombinedActions("align-tif", [AlignFrames(plot_summary=True)],
                                       output_path="output/img-tif-align"))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_align()
    test_align_2()
    test_align_3()
    test_align_4()
    test_jpg()
    test_tif()
