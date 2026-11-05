import threading
import time
from unittest.mock import patch
import numpy as np
import cv2
from shinestacker.config.constants import constants
from shinestacker.algorithms.feature_match import (
    FeatureCache, FeatureMatcher, DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG)


def test_constructor_default():
    print("Testing FeatureMatcher constructor with default parameters...")
    matcher = FeatureMatcher(
        feature_config=DEFAULT_FEATURE_CONFIG, matching_config=DEFAULT_MATCHING_CONFIG)
    assert matcher.feature_config == DEFAULT_FEATURE_CONFIG
    assert matcher.matching_config == DEFAULT_MATCHING_CONFIG
    assert matcher.callbacks == {}
    assert matcher.detector is not None
    assert matcher.descriptor is not None
    print("✓ Constructor with default parameters: PASS")


def test_constructor_custom_config():
    print("Testing FeatureMatcher constructor with custom parameters...")
    custom_feature_config = {
        'detector': constants.DETECTOR_SIFT,
        'descriptor': constants.DESCRIPTOR_SIFT
    }
    custom_matching_config = {
        'match_method': constants.MATCHING_KNN,
        'threshold': 0.7
    }

    def dummy_callback(msg):
        print(f"Callback: {msg}")

    callbacks = {'warning': dummy_callback}
    matcher = FeatureMatcher(
        feature_config=custom_feature_config,
        matching_config=custom_matching_config,
        callbacks=callbacks
    )
    assert matcher.feature_config['detector'] == constants.DETECTOR_SIFT
    assert matcher.feature_config['descriptor'] == constants.DESCRIPTOR_SIFT
    assert matcher.matching_config['match_method'] == constants.MATCHING_KNN
    assert matcher.matching_config['threshold'] == 0.7
    assert 'warning' in matcher.callbacks
    assert matcher.detector is not None
    assert matcher.descriptor is not None
    print("✓ Constructor with custom parameters: PASS")


def test_constructor_invalid_config():
    print("Testing FeatureMatcher constructor with invalid configuration...")
    invalid_feature_config = {
        'detector': constants.DETECTOR_SIFT,
        'descriptor': constants.DESCRIPTOR_ORB  # Invalid combo
    }
    try:
        matcher = FeatureMatcher(
            feature_config=invalid_feature_config, matching_config=DEFAULT_MATCHING_CONFIG)
        assert False, "Should have raised an exception for invalid config"
        assert matcher is not None
    except ValueError as e:
        assert "Detector SIFT requires descriptor SIFT" in str(e)
        print("✓ Constructor with invalid config correctly raised exception: PASS")


def test_constructor_edge_cases():
    print("Testing FeatureMatcher constructor edge cases...")
    matcher = FeatureMatcher(feature_config={}, matching_config={})
    assert matcher.feature_config == DEFAULT_FEATURE_CONFIG
    assert matcher.matching_config == DEFAULT_MATCHING_CONFIG
    matcher = FeatureMatcher(feature_config=None, matching_config=None)
    assert matcher.feature_config == DEFAULT_FEATURE_CONFIG
    assert matcher.matching_config == DEFAULT_MATCHING_CONFIG
    print("✓ Constructor edge cases: PASS")


def test_detect_and_compute_basic():
    print("Testing detect_and_compute with basic image...")
    test_image = np.zeros((100, 100, 3), dtype=np.uint8)
    # Create an "L" shape which should produce corners
    test_image[20:80, 20:40] = 255  # Vertical bar
    test_image[20:40, 20:80] = 255  # Horizontal bar
    matcher = FeatureMatcher(
        feature_config=DEFAULT_FEATURE_CONFIG, matching_config=DEFAULT_MATCHING_CONFIG)
    kp, des = matcher.detect_and_compute(test_image)
    assert kp is not None, "Keypoints should not be None"
    if len(kp) > 0:
        assert des is not None, f"Should have descriptors for {len(kp)} keypoints"
        assert des.shape[0] == len(kp), "Number of descriptors should match number of keypoints"
    else:
        print("  Note: No keypoints found in test image (this can happen with some detectors)")
    print(f"✓ Found {len(kp)} keypoints: PASS")


def test_detect_and_compute_different_detectors():
    print("Testing detect_and_compute with different detector/descriptor combinations...")
    test_image = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
    combinations = [
        {'detector': constants.DETECTOR_SIFT, 'descriptor': constants.DESCRIPTOR_SIFT},
        {'detector': constants.DETECTOR_ORB, 'descriptor': constants.DESCRIPTOR_ORB},
    ]
    for combo in combinations:
        try:
            matcher = FeatureMatcher(
                feature_config=combo, matching_config=DEFAULT_MATCHING_CONFIG)
            kp, des = matcher.detect_and_compute(test_image)
            assert kp is not None, f"Keypoints should not be None for {combo}"
            assert des is None or des.shape[0] == len(kp), \
                f"Descriptor count should match keypoints for {combo}"
            print(f"✓ {combo['detector']}-{combo['descriptor']}: {len(kp)} keypoints: PASS")
        except Exception as e:
            print(f"✗ {combo['detector']}-{combo['descriptor']}: {e}")


def test_detect_and_compute_grayscale():
    print("Testing detect_and_compute with grayscale image...")
    test_image = np.zeros((100, 100), dtype=np.uint8)
    test_image[20:80, 20:40] = 255  # Vertical bar
    test_image[20:40, 20:80] = 255  # Horizontal bar
    matcher = FeatureMatcher(
        feature_config=DEFAULT_FEATURE_CONFIG, matching_config=DEFAULT_MATCHING_CONFIG)
    kp, des = matcher.detect_and_compute(test_image)
    assert kp is not None, "Should work with grayscale images"
    if len(kp) > 0:
        assert des is not None, "Should have descriptors when keypoints are found"
        if hasattr(des, 'shape'):
            assert des.shape[0] == len(kp), "Descriptor count should match keypoints"
    else:
        assert des is None, "Descriptors should be None when no keypoints found"
    print("✓ Grayscale image handling: PASS")


def test_detect_and_compute_empty_image():
    print("Testing detect_and_compute with empty image...")
    test_image = np.zeros((50, 50, 3), dtype=np.uint8)  # All black
    matcher = FeatureMatcher(
        feature_config=DEFAULT_FEATURE_CONFIG, matching_config=DEFAULT_MATCHING_CONFIG)
    kp, des = matcher.detect_and_compute(test_image)
    assert kp is not None, "Should handle empty image without crashing"
    assert len(kp) == 0, "Empty image should have 0 keypoints"
    assert des is None, "Descriptors should be None when no keypoints found"
    print("✓ Empty image handling: PASS")


def test_detect_and_compute_with_real_image():
    print("Testing detect_and_compute with real image pattern...")
    test_image = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(0, 100, 20):
        for j in range(0, 100, 20):
            if (i // 20 + j // 20) % 2 == 0:
                test_image[i:i + 10, j:j + 10] = 255
    matcher = FeatureMatcher(
        feature_config=DEFAULT_FEATURE_CONFIG, matching_config=DEFAULT_MATCHING_CONFIG)
    kp, des = matcher.detect_and_compute(test_image)
    assert kp is not None, "Keypoints should not be None"
    assert len(kp) > 0, "Chessboard pattern should produce keypoints"
    assert des is not None, "Should have descriptors when keypoints are found"
    assert des.shape[0] == len(kp), "Descriptor count should match keypoints"
    print(f"✓ Real image pattern: {len(kp)} keypoints found: PASS")


def test_match_images_basic():
    print("Testing match_images with basic images...")
    img1 = np.zeros((100, 100, 3), dtype=np.uint8)
    img2 = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(img1, (20, 20), (40, 40), (255, 255, 255), -1)
    cv2.rectangle(img2, (25, 25), (45, 45), (255, 255, 255), -1)
    matcher = FeatureMatcher(
        feature_config=DEFAULT_FEATURE_CONFIG, matching_config=DEFAULT_MATCHING_CONFIG)
    match_result = matcher.match_images(img1, img2)
    assert match_result is not None
    assert hasattr(match_result, 'kp_0')
    assert hasattr(match_result, 'kp_ref')
    assert hasattr(match_result, 'good_matches')
    assert hasattr(match_result, 'n_good_matches')
    print(f"✓ Match images basic: {match_result.n_good_matches()} matches found: PASS")


def test_match_images_no_features():
    print("Testing match_images with images having no features...")
    img1 = np.zeros((100, 100, 3), dtype=np.uint8)
    img2 = np.zeros((100, 100, 3), dtype=np.uint8)
    matcher = FeatureMatcher(
        feature_config=DEFAULT_FEATURE_CONFIG, matching_config=DEFAULT_MATCHING_CONFIG)
    match_result = matcher.match_images(img1, img2)
    assert match_result is not None
    assert match_result.n_good_matches() == 0
    assert len(match_result.good_matches) == 0
    print("✓ Match images no features: PASS")


def test_match_features_knn():
    print("Testing match_features with KNN method...")
    matcher = FeatureMatcher(
        feature_config={
            'detector': constants.DETECTOR_SIFT,
            'descriptor': constants.DESCRIPTOR_SIFT
        },
        matching_config={
            'match_method': constants.MATCHING_KNN
        })
    des1 = np.random.random((10, 128)).astype(np.float32)
    des2 = np.random.random((10, 128)).astype(np.float32)
    good_matches = matcher.match_features(des1, des2)
    assert good_matches is not None
    print(f"✓ Match features KNN: {len(good_matches)} matches: PASS")


def test_match_features_hamming():
    print("Testing match_features with Hamming method...")
    matcher = FeatureMatcher(
        feature_config=DEFAULT_FEATURE_CONFIG,
        matching_config={'match_method': constants.MATCHING_NORM_HAMMING})
    des1 = np.random.randint(0, 255, (10, 32), dtype=np.uint8)
    des2 = np.random.randint(0, 255, (10, 32), dtype=np.uint8)
    good_matches = matcher.match_features(des1, des2)
    assert good_matches is not None
    print(f"✓ Match features Hamming: {len(good_matches)} matches: PASS")


def test_match_features_empty_descriptors():
    print("Testing match_features with empty descriptors...")
    matcher = FeatureMatcher(
        feature_config=DEFAULT_FEATURE_CONFIG, matching_config=DEFAULT_MATCHING_CONFIG)
    des1 = np.array([]).reshape(0, 128).astype(np.float32)
    des2 = np.random.random((10, 128)).astype(np.float32)
    good_matches = matcher.match_features(des1, des2)
    assert len(good_matches) == 0
    des1 = np.random.random((10, 128)).astype(np.float32)
    des2 = np.array([]).reshape(0, 128).astype(np.float32)
    good_matches = matcher.match_features(des1, des2)
    assert len(good_matches) == 0
    print("✓ Match features empty descriptors: PASS")


def test_match_features_different_sizes():
    print("Testing match_features with different descriptor sizes...")
    matcher = FeatureMatcher(
        feature_config=DEFAULT_FEATURE_CONFIG, matching_config=DEFAULT_MATCHING_CONFIG)
    des1 = np.random.random((5, 128)).astype(np.float32)
    des2 = np.random.random((8, 128)).astype(np.float32)
    good_matches = matcher.match_features(des1, des2)
    assert good_matches is not None
    print(f"✓ Match features different sizes: {len(good_matches)} matches: PASS")


def test_feature_cache_computes_once_per_key():
    cache = FeatureCache()
    calls = []
    results = []

    def compute():
        calls.append(1)
        time.sleep(0.05)
        return object()

    def ask():
        results.append(cache.get_or_compute((3, 2), compute))

    threads = [threading.Thread(target=ask) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(calls) == 1
    assert all(r is results[0] for r in results)
    assert cache.get_or_compute((4, 2), lambda: "other") == "other"


def test_feature_cache_drop_and_clear():
    cache = FeatureCache()
    for key in [(0, 1), (0, 2), (1, 1)]:
        cache.get_or_compute(key, lambda key=key: key)
    cache.drop(0)
    assert cache.get_or_compute((0, 1), lambda: "again") == "again"
    assert cache.get_or_compute((1, 1), lambda: "again") == (1, 1)
    cache.clear()
    assert cache.get_or_compute((1, 1), lambda: "again") == "again"


def test_detect_and_compute_with_cache_key():
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (120, 120), (255, 255, 255), -1)
    cv2.circle(img, (150, 150), 20, (180, 180, 180), -1)
    matcher = FeatureMatcher(DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG)
    kp_ref, des_ref = matcher.detect_and_compute(img)
    matcher.cache = FeatureCache()
    with patch.object(matcher, '_detect_and_compute', wraps=matcher._detect_and_compute) as spy:
        kp_1, des_1 = matcher.detect_and_compute(img, (0, 1))
        kp_2, des_2 = matcher.detect_and_compute(img, (0, 1))
        assert spy.call_count == 1
        matcher.detect_and_compute(img)                 # no key: not cached
        matcher.detect_and_compute(img, (1, 1))         # another frame
        assert spy.call_count == 3
    assert kp_2 is kp_1 and des_2 is des_1
    assert len(kp_1) == len(kp_ref)
    assert np.array_equal(des_1, des_ref)


if __name__ == "__main__":
    print("Running FeatureMatcher tests...")
    test_constructor_default()
    test_constructor_custom_config()
    test_constructor_invalid_config()
    test_constructor_edge_cases()
    test_detect_and_compute_basic()
    test_detect_and_compute_different_detectors()
    test_detect_and_compute_grayscale()
    test_detect_and_compute_empty_image()
    test_detect_and_compute_with_real_image()
    test_match_images_basic()
    test_match_images_no_features()
    test_match_features_knn()
    test_match_features_hamming()
    test_match_features_empty_descriptors()
    test_match_features_different_sizes()
