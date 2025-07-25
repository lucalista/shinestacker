import matplotlib
matplotlib.use('Agg')
from focusstack.config.constants import constants
from focusstack.algorithms.utils import read_img
from focusstack.algorithms.stack_framework import StackJob, CombinedActions
from focusstack.algorithms.align import align_images, AlignFrames


def test_align():
    try:
        img_1, img_2 = [read_img(f"../examples/input/img-jpg/000{i}.jpg") for i in (2, 3)]
        n_good_matches, M, img_warp = align_images(img_1, img_2)
        assert img_warp is not None
        assert n_good_matches > 100
    except Exception:
        assert False


def test_align_2():
    try:
        img_1, img_2 = [read_img(f"../examples/input/img-jpg/000{i}.jpg") for i in (2, 3)]
        n_good_matches, M, img_warp = align_images(img_1, img_2,
                                                   feature_config={'detector': constants.DETECTOR_ORB,
                                                                   'descriptor': constants.DESCRIPTOR_SIFT})
        assert img_warp is not None
        assert n_good_matches > 100
    except Exception:
        assert False


def test_align_3():
    try:
        img_1, img_2 = [read_img(f"../examples/input/img-jpg/000{i}.jpg") for i in (2, 3)]
        n_good_matches, M, img_warp = align_images(img_1, img_2,
                                                   feature_config={'detector': constants.DETECTOR_ORB,
                                                                   'descriptor': constants.DESCRIPTOR_ORB},
                                                   matching_config={'match_method': constants.MATCHING_NORM_HAMMING})
        assert img_warp is not None
        assert n_good_matches > 100
    except Exception:
        assert False


def test_align_4():
    try:
        img_1, img_2 = [read_img(f"../examples/input/img-jpg/000{i}.jpg") for i in (2, 3)]
        n_good_matches, M, img_warp = align_images(img_1, img_2,
                                                   feature_config={'detector': constants.DETECTOR_ORB,
                                                                   'descriptor': constants.DESCRIPTOR_ORB},
                                                   matching_config={'match_method': constants.MATCHING_KNN})
        assert img_warp is not None
        assert n_good_matches > 100
    except ValueError as e:
        assert str(e) == "Detector ORB and descriptor ORB require matching method Hamming distance"

    except Exception:
        assert False


def test_align_rescale():
    try:
        img_1, img_2 = [read_img(f"../examples/input/img-jpg/000{i}.jpg") for i in (2, 3)]
        n_good_matches, M, img_warp = align_images(img_1, img_2, alignment_config={'subsample': 4})
        assert img_warp is not None
        assert n_good_matches > 10
    except Exception:
        assert False


def test_align_ecc():
    try:
        img_1, img_2 = [read_img(f"../examples/input/img-jpg/000{i}.jpg") for i in (2, 3)]
        n_good_matches, M, img_warp = align_images(img_1, img_2, alignment_config={'ecc_refinement': True})
        assert img_warp is not None
        assert n_good_matches > 10
    except Exception:
        assert False


def test_jpg():
    try:
        job = StackJob("job", "../examples", input_path="input/img-jpg", callbacks='tqdm')
        job.add_action(CombinedActions("align-jpg", [AlignFrames(plot_summary=True)],
                                       output_path="output/img-jpg-align"))
        job.run()
    except Exception:
        assert False


def test_tif():
    try:
        job = StackJob("job", "../examples", input_path="input/img-tif", callbacks='tqdm')
        job.add_action(CombinedActions("align-tif", [AlignFrames(plot_summary=True)],
                                       output_path="output/img-tif-align"))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_align()
    test_align_rescale()
    test_align_2()
    test_align_3()
    test_align_4()
    test_jpg()
    test_tif()
