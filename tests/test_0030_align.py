import matplotlib
matplotlib.use('Agg')
from shinestacker.config.constants import constants
from shinestacker.algorithms.utils import read_img
from shinestacker.algorithms.stack_framework import StackJob, CombinedActions
from shinestacker.algorithms.align import align_images, AlignFrames
from shinestacker.algorithms.align_parallel import AlignFramesParallel
from shinestacker.algorithms.align_auto import AlignFramesAuto


def test_align():
    try:
        img_1, img_2 = [read_img(f"examples/input/img-jpg/000{i}.jpg") for i in (2, 3)]
        n_good_matches, m, img_warp = align_images(img_1, img_2)
        assert img_warp is not None
        assert n_good_matches > 100
    except Exception:
        assert False


def test_align_homo():
    try:
        img_1, img_2 = [read_img(f"examples/input/img-jpg/000{i}.jpg") for i in (2, 3)]
        n_good_matches, m, img_warp = align_images(
            img_1, img_2, alignment_config={'transform': constants.ALIGN_HOMOGRAPHY})
        assert img_warp is not None
        assert n_good_matches > 10
    except Exception:
        assert False


def test_align_rescale():
    try:
        img_1, img_2 = [read_img(f"examples/input/img-jpg/000{i}.jpg") for i in (2, 3)]
        n_good_matches, m, img_warp = align_images(
            img_1, img_2, alignment_config={'subsample': 4})
        assert img_warp is not None
        assert n_good_matches > 10
    except Exception:
        assert False


def test_jpg():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg", callbacks='tqdm')
        job.add_action(CombinedActions("align-jpg", [AlignFrames(plot_summary=True,
                                                                 plot_matches=True)],
                                       output_path="output/img-jpg-align",
                                       delete_output_at_end=True))
        job.run()
    except Exception:
        assert False


def test_jpg_homo():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg", callbacks='tqdm')
        job.add_action(
            CombinedActions(
                "align-jpg",
                [AlignFrames(
                    alignment_config={'transform': constants.ALIGN_HOMOGRAPHY},
                    plot_summary=True)],
                output_path="output/img-jpg-align",
                delete_output_at_end=True))
        job.run()
    except Exception:
        assert False


def test_jpg_quality_plots():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg", callbacks='tqdm')
        job.add_action(
            CombinedActions(
                "align-jpg",
                [AlignFrames(
                    alignment_config={'compute_rans_quality': True},
                    plot_summary=True,
                    plot_matches=True)],
                output_path="output/img-jpg-align",
                delete_output_at_end=True))
        job.run()
    except Exception:
        assert False


def test_tif():
    try:
        job = StackJob("job", "examples", input_path="input/img-tif", callbacks='tqdm')
        job.add_action(CombinedActions("align-tif", [AlignFrames(plot_summary=True)],
                                       output_path="output/img-tif-align",
                                       delete_output_at_end=True))
        job.run()
    except Exception:
        assert False


def test_parallel():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg", callbacks='tqdm')
        job.add_action(CombinedActions("align-jpg", [AlignFramesParallel(plot_summary=False)],
                                       output_path="output/img-jpg-align",
                                       delete_output_at_end=True))
        job.run()
    except Exception:
        assert False


def test_parallel_sift():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg", callbacks='tqdm')
        job.add_action(
            CombinedActions(
                "align-jpg",
                [AlignFramesParallel(
                    feature_config={
                        'detector': constants.DETECTOR_SIFT,
                        'descriptor': constants.DESCRIPTOR_SIFT
                    },
                    matching_config={
                        'match_method': constants.MATCHING_KNN,
                    },
                    plot_summary=False)],
                output_path="output/img-jpg-align",
                delete_output_at_end=True))
        job.run()
    except Exception:
        assert False


def test_auto():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg", callbacks='tqdm')
        job.add_action(CombinedActions("align-jpg", [AlignFramesAuto(plot_summary=False)],
                                       output_path="output/img-jpg-align",
                                       delete_output_at_end=True))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_align()
    test_align_homo()
    test_align_rescale()
    test_jpg()
    test_tif()
    test_parallel()
    test_parallel_sift()
    test_auto()
    test_jpg_quality_plots()


def test_resolution_target_option_reaches_subsampling(monkeypatch):
    """resolution_target used to be read from the defaults only: an option
    given to AlignFrames / align_images had no effect."""
    import numpy as np
    from shinestacker.algorithms import align as align_module
    seen = []

    class StopMatcher:
        def __init__(self, *args, **kwargs):
            pass

        def match_images_with_fallback(self, _img_ref, _img_0, subsample, warning_callback=None):
            seen.append(subsample)
            raise StopIteration

    monkeypatch.setattr(align_module, "SubsamplingFeatureMatcher", StopMatcher)
    img = np.zeros((4680, 7020, 3), dtype=np.uint8)
    for target, factor in ((2, 4), (8, 2), (40, 1)):
        try:
            align_images(img, img, alignment_config={'resolution_target': target})
        except StopIteration:
            pass
        assert seen[-1] == factor
    assert AlignFrames(resolution_target=8).alignment_config['resolution_target'] == 8
