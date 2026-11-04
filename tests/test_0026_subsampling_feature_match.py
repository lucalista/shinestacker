# pylint: disable=W0212
import cv2
import numpy as np
import pytest
from unittest.mock import patch
from shinestacker.config.constants import constants
from shinestacker.algorithms.utils import img_subsample
from shinestacker.algorithms.feature_match import (
    FeatureCache, FeatureMatcher, SubsamplingFeatureMatcher, DEFAULT_FEATURE_CONFIG,
    DEFAULT_MATCHING_CONFIG, DEFAULT_ALIGNMENT_CONFIG)


def create_test_images():
    img1 = np.zeros((400, 400, 3), dtype=np.uint8)
    img2 = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.rectangle(img1, (100, 100), (150, 150), (255, 255, 255), -1)
    cv2.rectangle(img2, (120, 120), (170, 170), (255, 255, 255), -1)  # Translated
    cv2.circle(img1, (300, 300), 25, (200, 200, 200), -1)
    cv2.circle(img2, (315, 315), 25, (200, 200, 200), -1)  # Translated
    return img1, img2


def test_basic_matching():
    print("Testing basic feature matching...")
    img1, img2 = create_test_images()
    matcher = SubsamplingFeatureMatcher(
        DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG, DEFAULT_ALIGNMENT_CONFIG)
    result, final_subsample = matcher.match_images_with_fallback(img1, img2)
    print(f"Number of good matches: {result.n_good_matches()}")
    print(f"Final subsample used: {final_subsample}")
    print(f"Has sufficient matches (min=4): {result.has_sufficient_matches(4)}")
    if result.n_good_matches() > 0:
        src_pts = result.get_src_points()
        dst_pts = result.get_dst_points()
        print(f"Source points shape: {src_pts.shape}")
        print(f"Target points shape: {dst_pts.shape}")
        transform, _ = cv2.estimateAffinePartial2D(src_pts, dst_pts)
        if transform is not None:
            print(f"Estimated translation: dx={transform[0, 2]:.1f}, dy={transform[1, 2]:.1f}")


def test_subsampling():
    print("\nTesting subsampling...")
    img1, img2 = create_test_images()
    matcher = SubsamplingFeatureMatcher(
        DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG, DEFAULT_ALIGNMENT_CONFIG)
    for subsample in [1, 2, 4]:
        result, final_subsample = matcher.match_images_with_fallback(
            img1, img2, subsample=subsample)
        print(f"Requested subsample {subsample}: "
              f"{result.n_good_matches()} matches, final subsample: {final_subsample}")
        img_ref_sub, img_0_sub = matcher.get_last_subsampled_images()
        print(f"  Subsampled image shapes: {img_ref_sub.shape}, {img_0_sub.shape}")


def test_fallback_behavior():
    print("\nTesting fallback behavior...")
    img1, img2 = create_test_images()
    alignment_config = DEFAULT_ALIGNMENT_CONFIG.copy()
    alignment_config['min_good_matches'] = 1000  # Impossible to reach
    matcher = SubsamplingFeatureMatcher(
        DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG, alignment_config)
    result, final_subsample = matcher.match_images_with_fallback(
        img1, img2, subsample=4,
        warning_callback=lambda msg: print(f"  Fallback warning: {msg}"))
    print(f"After fallback: {result.n_good_matches()} matches, final subsample: {final_subsample}")
    print(f"Expected fallback to 1: {final_subsample == 1}")


def test_different_detectors():
    print("\nTesting different detectors...")
    img1, img2 = create_test_images()
    detectors = ['SIFT', 'ORB', 'AKAZE']
    for detector in detectors:
        try:
            config = DEFAULT_FEATURE_CONFIG.copy()
            config['detector'] = detector
            config['descriptor'] = detector
            matcher = SubsamplingFeatureMatcher(
                config, DEFAULT_MATCHING_CONFIG, DEFAULT_ALIGNMENT_CONFIG)
            result, final_subsample = matcher.match_images_with_fallback(img1, img2)
            print(f"{detector}: {result.n_good_matches()} matches, subsample: {final_subsample}")
        except Exception as e:
            print(f"{detector}: Failed - {e}")


def test_no_features():
    print("\nTesting with featureless images...")
    img1 = np.zeros((200, 200, 3), dtype=np.uint8)
    img2 = np.zeros((200, 200, 3), dtype=np.uint8)
    matcher = SubsamplingFeatureMatcher(
        DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG, DEFAULT_ALIGNMENT_CONFIG)
    result, final_subsample = matcher.match_images_with_fallback(img1, img2)
    print(f"Featureless images: {result.n_good_matches()} matches")
    print(f"Has sufficient matches (min=1): {result.has_sufficient_matches(1)}")
    print(f"Final subsample: {final_subsample}")


def test_coordinate_consistency():
    print("\nTesting coordinate consistency...")
    img1, img2 = create_test_images()
    matcher = SubsamplingFeatureMatcher(
        DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG, DEFAULT_ALIGNMENT_CONFIG)
    for subsample in [1, 2, 4]:
        result, final_subsample = matcher.match_images_with_fallback(
            img1, img2, subsample=subsample)
        if result.n_good_matches() > 0:
            src_pts = result.get_src_points()
            max_coord = max(src_pts.flatten()) if len(src_pts) > 0 else 0
            print(f"Subsample {subsample}: max coordinate = {max_coord:.1f}")
            if subsample > 1:
                print(f"  Coordinates scaled to original image space: {max_coord <= 400}")


def test_frame_keys_compute_the_features_of_a_frame_once():
    img1, img2 = create_test_images()
    img3 = np.roll(img2, 7, axis=1)
    matcher = SubsamplingFeatureMatcher(
        DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG, DEFAULT_ALIGNMENT_CONFIG)
    plain, _ = matcher.match_images_with_fallback(img1, img2)
    feature_matcher = matcher.feature_matcher
    feature_matcher.cache = FeatureCache()
    with patch.object(feature_matcher, '_detect_and_compute',
                      wraps=feature_matcher._detect_and_compute) as spy:
        first, _ = matcher.match_images_with_fallback(img1, img2, frame_keys=(0, 1))
        second, _ = matcher.match_images_with_fallback(img2, img3, frame_keys=(1, 2))
        assert spy.call_count == 3                       # three frames, four images matched
    assert first.n_good_matches() == plain.n_good_matches()
    assert [m.distance for m in first.good_matches] == [m.distance for m in plain.good_matches]
    assert second.n_good_matches() > 0


def test_frame_keys_keep_an_entry_per_resolution_and_do_not_change_the_features():
    img1, img2 = create_test_images()
    img3 = np.roll(img2, 7, axis=1)
    alignment_config = {**DEFAULT_ALIGNMENT_CONFIG,
                        'min_good_matches': 10 ** 6}     # always retry at full size
    plain = SubsamplingFeatureMatcher(
        DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG, alignment_config)
    cached = SubsamplingFeatureMatcher(
        DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG, alignment_config)
    feature_matcher = cached.feature_matcher
    feature_matcher.cache = FeatureCache()

    def points(result):
        return (result.get_src_points(), result.get_dst_points(),
                [m.distance for m in result.good_matches])

    with patch.object(feature_matcher, '_detect_and_compute',
                      wraps=feature_matcher._detect_and_compute) as spy:
        first, sub_first = cached.match_images_with_fallback(
            img1, img2, subsample=2, frame_keys=(0, 1))
        assert sub_first == 1                            # retried without subsampling
        assert spy.call_count == 4                       # two frames, two resolutions each
        items = feature_matcher.cache._items
        snapshot = {key: ([k.pt for k in kp], des.tobytes()) for key, (kp, des) in items.items()}
        assert sorted(snapshot) == [(0, 1), (0, 2), (1, 1), (1, 2)]
        second, _ = cached.match_images_with_fallback(
            img2, img3, subsample=2, frame_keys=(1, 2))
        assert spy.call_count == 6                       # only frame 2 is new, at both resolutions
    for key, (pts, des_bytes) in snapshot.items():       # the shared features are untouched
        kp, des = feature_matcher.cache._items[key]
        assert [k.pt for k in kp] == pts and des.tobytes() == des_bytes
        assert not des.flags.writeable
    for result, (ref, other) in ((first, (img1, img2)), (second, (img2, img3))):
        expected, _ = plain.match_images_with_fallback(ref, other, subsample=2)
        for got, want in zip(points(result), points(expected)):
            np.testing.assert_array_equal(got, want)


def textured_chain(n_frames=3):
    rng = np.random.default_rng(4)
    base = cv2.GaussianBlur(rng.integers(0, 255, (500, 600), dtype=np.uint8), (0, 0), 2.0)
    base = cv2.normalize(base, None, 0, 255, cv2.NORM_MINMAX)
    return [cv2.cvtColor(np.roll(base, (3 * i, 5 * i), axis=(0, 1)), cv2.COLOR_GRAY2BGR)
            for i in range(n_frames)]


@pytest.mark.parametrize('detector, match_method', [
    (constants.DETECTOR_AKAZE, constants.MATCHING_NORM_HAMMING),
    (constants.DETECTOR_SIFT, constants.MATCHING_KNN)])
def test_frame_keys_subsampled_matches_reuse_the_interior_frame_unchanged(
        detector, match_method):
    frames = textured_chain()
    feature_config = {'detector': detector, 'descriptor': detector}
    matching_config = {**DEFAULT_MATCHING_CONFIG, 'match_method': match_method}
    alignment_config = {**DEFAULT_ALIGNMENT_CONFIG, 'fast_subsampling': False}
    plain = SubsamplingFeatureMatcher(feature_config, matching_config, alignment_config)
    cached = SubsamplingFeatureMatcher(feature_config, matching_config, alignment_config)
    feature_matcher = cached.feature_matcher
    feature_matcher.cache = FeatureCache()
    # the features of each frame found on their own, before any cached match
    alone = [FeatureMatcher(feature_config, matching_config).detect_and_compute(
        img_subsample(frame, 2, False)) for frame in frames]
    with patch.object(feature_matcher, '_detect_and_compute',
                      wraps=feature_matcher._detect_and_compute) as spy:
        pairs = []
        for ref, other in ((0, 1), (1, 2)):
            result, sub = cached.match_images_with_fallback(
                frames[ref], frames[other], subsample=2, frame_keys=(ref, other))
            assert sub == 2                              # the subsampled match was enough
            expected, sub_expected = plain.match_images_with_fallback(
                frames[ref], frames[other], subsample=2)
            assert sub_expected == 2
            pairs.append((result, expected))
        assert spy.call_count == 3                       # three frames, once each
    cache = feature_matcher.cache._items
    assert sorted(cache) == [(0, 2), (1, 2), (2, 2)]     # no entry at full size
    for result, expected in pairs:
        assert result.n_good_matches() > 0
        if match_method == constants.MATCHING_NORM_HAMMING:
            np.testing.assert_array_equal(result.get_src_points(), expected.get_src_points())
            np.testing.assert_array_equal(result.get_dst_points(), expected.get_dst_points())
            assert ([m.distance for m in result.good_matches]
                    == [m.distance for m in expected.good_matches])
        else:       # FLANN's randomized trees give slightly different matches from run to run
            assert (abs(result.n_good_matches() - expected.n_good_matches())
                    <= 0.02 * expected.n_good_matches())
    for i, (kp_alone, des_alone) in enumerate(alone):    # cached features: those of the frame alone
        kp, des = cache[(i, 2)]
        assert [k.pt for k in kp] == [k.pt for k in kp_alone]
        assert np.array_equal(des, des_alone)


if __name__ == "__main__":
    test_basic_matching()
    test_subsampling()
    test_fallback_behavior()
    test_different_detectors()
    test_no_features()
    test_coordinate_consistency()
