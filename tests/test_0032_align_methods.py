from time import perf_counter
from shinestacker.config.constants import constants
from shinestacker.algorithms.utils import read_img
from shinestacker.algorithms.align import align_images

trap_exceptions = {
    ('AKAZE', 'AKAZE', 'KNN'): 'Detector AKAZE and descriptor AKAZE require matching method Hamming distance',
    ('AKAZE', 'BRISK', 'KNN'): 'Detector AKAZE and descriptor BRISK require matching method Hamming distance',
    ('AKAZE', 'ORB', 'KNN'): 'Detector AKAZE and descriptor ORB require matching method Hamming distance',
    ('AKAZE', 'SIFT', 'NORM_HAMMING'): 'Descriptor SIFT requires matching method KNN',
    ('BRISK', 'AKAZE', 'KNN'): 'Detector BRISK is incompatible with descriptor AKAZE',
    ('BRISK', 'AKAZE', 'NORM_HAMMING'): 'Detector BRISK is incompatible with descriptor AKAZE',
    ('BRISK', 'BRISK', 'KNN'): 'Detector BRISK and descriptor BRISK require matching method Hamming distance',
    ('BRISK', 'SIFT', 'NORM_HAMMING'): 'Descriptor SIFT requires matching method KNN',
    ('BRISK', 'ORB', 'KNN'): 'Detector BRISK and descriptor ORB require matching method Hamming distance',
    ('ORB', 'AKAZE', 'KNN'): 'Detector ORB and descriptor AKAZE require matching method Hamming distance',
    ('ORB', 'AKAZE', 'NORM_HAMMING'): 'Detector ORB and descriptor AKAZE require matching method KNN',
    ('ORB', 'BRISK', 'KNN'): 'Detector ORB and descriptor BRISK require matching method Hamming distance',
    ('ORB', 'ORB', 'KNN'): 'Detector ORB and descriptor ORB require matching method Hamming distance',
    ('ORB', 'SIFT', 'NORM_HAMMING'): 'Descriptor SIFT requires matching method KNN',
    ('SIFT', 'AKAZE', 'KNN'): 'Detector SIFT requires descriptor SIFT',
    ('SIFT', 'AKAZE', 'NORM_HAMMING'): 'Detector SIFT requires descriptor SIFT',
    ('SIFT', 'BRISK', 'KNN'): 'Detector SIFT requires descriptor SIFT',
    ('SIFT', 'BRISK', 'NORM_HAMMING'): 'Detector SIFT requires descriptor SIFT',
    ('SIFT', 'ORB', 'KNN'): 'Detector SIFT requires descriptor SIFT',
    ('SIFT', 'ORB', 'NORM_HAMMING'): 'Detector SIFT requires descriptor SIFT',
    ('SIFT', 'SIFT', 'NORM_HAMMING'): 'Descriptor SIFT requires matching method KNN',
    ('SURF', 'AKAZE', 'KNN'): 'Detector SURF is incompatible with descriptor AKAZE',
    ('SURF', 'AKAZE', 'NORM_HAMMING'): 'Detector SURF is incompatible with descriptor AKAZE',
    ('SURF', 'BRISK', 'KNN'): 'Detector SURF and descriptor BRISK require matching method Hamming distance',
    ('SURF', 'ORB', 'KNN'): 'Detector SURF and descriptor ORB require matching method Hamming distance',
    ('SURF', 'SIFT', 'NORM_HAMMING'): 'Descriptor SIFT requires matching method KNN'
}


def test_align():
    perf_map = {}
    for detector in constants.VALID_DETECTORS:
        for descriptor in constants.VALID_DESCRIPTORS:
            for match_method in constants.VALID_MATCHING_METHODS:
                try:
                    print(f"detector: {detector}, descriptor: {descriptor}, match method: {match_method}")
                    img_1, img_2 = [read_img(f"../examples/input/img-jpg/000{i}.jpg") for i in (2, 3)]
                    t_start = perf_counter()
                    n_good_matches, M, img_warp = align_images(img_1, img_2,
                                                               feature_config={'detector': detector,
                                                                               'descriptor': descriptor},
                                                               matching_config={'match_method': match_method})
                    t_elapsed = perf_counter() - t_start
                    assert img_warp is not None
                    assert n_good_matches > 100
                    perf_map[t_elapsed] = (detector, descriptor, match_method)
                except Exception as e:
                    k = (detector, descriptor, match_method)
                    if k in trap_exceptions.keys():
                        print(f"exception: {str(e)}")
                        assert str(e) == trap_exceptions[k]
                    else:
                        assert False
    perf_map = dict(sorted(perf_map.items()))
    print("== time performance ==")
    for t, v in perf_map.items():
        print(f"{t:.4f}s: {v[0]}-{v[1]}-{v[2]}")
    print("======================")


if __name__ == '__main__':
    test_align()
