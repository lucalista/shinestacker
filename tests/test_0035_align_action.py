# pylint: disable=W0212, E1101
import math
import logging
from unittest.mock import MagicMock
import numpy as np
from shinestacker.config import constants
from shinestacker.algorithms.align import (
    DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG,
    DEFAULT_ALIGNMENT_CONFIG, AlignFramesBase, AlignFrames
)
from shinestacker.algorithms.transform_estimate import (
    decompose_affine_matrix, check_affine_matrix, check_homography_distortion, check_transform,
    AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS
)


def test_identity_matrix():
    identity = np.array([[1, 0, 0], [0, 1, 0]], dtype=np.float64)
    scales, rotation, shear, translation = decompose_affine_matrix(identity)
    assert math.isclose(scales[0], 1.0, abs_tol=1e-10)
    assert math.isclose(scales[1], 1.0, abs_tol=1e-10)
    assert math.isclose(rotation, 0.0, abs_tol=1e-10)
    assert math.isclose(shear, 0.0, abs_tol=1e-10)
    assert math.isclose(translation[0], 0.0, abs_tol=1e-10)
    assert math.isclose(translation[1], 0.0, abs_tol=1e-10)


def test_translation_only():
    tx, ty = 50.0, -30.0
    translation_matrix = np.array([[1, 0, tx], [0, 1, ty]], dtype=np.float64)
    scales, rotation, shear, translation = decompose_affine_matrix(translation_matrix)
    assert math.isclose(scales[0], 1.0, abs_tol=1e-10)
    assert math.isclose(scales[1], 1.0, abs_tol=1e-10)
    assert math.isclose(rotation, 0.0, abs_tol=1e-10)
    assert math.isclose(shear, 0.0, abs_tol=1e-10)
    assert math.isclose(translation[0], tx, abs_tol=1e-10)
    assert math.isclose(translation[1], ty, abs_tol=1e-10)


def test_scale_only():
    scale_x, scale_y = 2.0, 0.5
    scale_matrix = np.array([[scale_x, 0, 0], [0, scale_y, 0]], dtype=np.float64)
    scales, rotation, shear, translation = decompose_affine_matrix(scale_matrix)
    assert math.isclose(scales[0], scale_x, abs_tol=1e-10)
    assert math.isclose(scales[1], scale_y, abs_tol=1e-10)
    assert math.isclose(rotation, 0.0, abs_tol=1e-10)
    assert math.isclose(shear, 0.0, abs_tol=1e-10)
    assert math.isclose(translation[0], 0.0, abs_tol=1e-10)
    assert math.isclose(translation[1], 0.0, abs_tol=1e-10)


def test_rotation_only():
    angle_deg = 45.0
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    rotation_matrix = np.array([[cos_a, sin_a, 0], [-sin_a, cos_a, 0]], dtype=np.float64)
    scales, rotation, shear, translation = decompose_affine_matrix(rotation_matrix)
    assert math.isclose(scales[0], 1.0, abs_tol=1e-10)
    assert math.isclose(scales[1], 1.0, abs_tol=1e-10)
    assert math.isclose(rotation, angle_deg, abs_tol=1e-10)
    assert math.isclose(shear, 0.0, abs_tol=1e-10)
    assert math.isclose(translation[0], 0.0, abs_tol=1e-10)
    assert math.isclose(translation[1], 0.0, abs_tol=1e-10)


def test_check_affine_matrix_valid():
    m = np.array([[1.0, 0.0, 10.0], [0.0, 1.0, 5.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape, AFFINE_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_affine_matrix_invalid_rotation():
    angle_rad = math.radians(25.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([[cos_a, sin_a, 0], [-sin_a, cos_a, 0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape, AFFINE_THRESHOLDS)
    assert not is_valid
    assert "rotation too large" in reason


def test_check_affine_matrix_invalid_scale():
    m = np.array([[0.8, 0.0, 0.0], [0.0, 1.2, 0.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape, AFFINE_THRESHOLDS)
    assert not is_valid
    assert "x-scale out of range" in reason


def test_check_affine_matrix_invalid_translation():
    m = np.array([[1.0, 0.0, 20.0], [0.0, 1.0, 15.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape, AFFINE_THRESHOLDS)
    assert not is_valid
    assert "translation too large" in reason


def test_check_homography_distortion_valid():
    m = np.eye(3, dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(
        m, img_shape, homography_thresholds=HOMOGRAPHY_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_homography_distortion_invalid_area():
    m = np.array([[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(
        m, img_shape, homography_thresholds=HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "area change too large" in reason


def test_check_homography_distortion_invalid_aspect():
    m = np.array([[2.0, 0.0, 0.0], [0.0, 0.5, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(
        m, img_shape, homography_thresholds=HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "aspect ratio change too large" in reason


def test_check_homography_distortion_skew():
    m = np.array([[1.0, 0.5, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(
        m, img_shape, homography_thresholds=HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "angle distortion too large" in reason


def test_check_affine_matrix_valid_rotation():
    angle_rad = math.radians(5.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([[cos_a, sin_a, 0], [-sin_a, cos_a, 0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape, AFFINE_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_affine_matrix_valid_scale():
    m = np.array([[0.95, 0.0, 0.0], [0.0, 1.05, 0.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape, AFFINE_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_affine_matrix_valid_translation():
    m = np.array([[1.0, 0.0, 5.0], [0.0, 1.0, 5.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape, AFFINE_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_affine_matrix_valid_shear():
    m = np.array([[1.0, 0.0, 0.0], [0.0857, 1.0, 0.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape, AFFINE_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_affine_matrix_combined_valid():
    angle_rad = math.radians(3.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([[0.95 * cos_a, 0.95 * sin_a, 4.0],
                  [-0.95 * sin_a, 1.05 * cos_a, -3.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape, AFFINE_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_homography_distortion_valid_scale():
    m = np.array([[1.2, 0.0, 0.0], [0.0, 1.2, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(
        m, img_shape, homography_thresholds=HOMOGRAPHY_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_homography_distortion_valid_aspect():
    m = np.array([[1.5, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(
        m, img_shape, homography_thresholds=HOMOGRAPHY_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_homography_distortion_valid_skew():
    m = np.array([[1.0, 0.1, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(
        m, img_shape, homography_thresholds=HOMOGRAPHY_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_affine_matrix_combined_invalid():
    angle_rad = math.radians(15.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([[0.8 * cos_a, 0.8 * sin_a, 20.0],
                  [-0.8 * sin_a, 1.2 * cos_a, 15.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape, AFFINE_THRESHOLDS)
    assert not is_valid
    assert "rotation too large" in reason
    assert "x-scale out of range" in reason
    assert "y-scale out of range" in reason
    assert "translation too large" in reason


def test_check_transform_rigid_valid():
    m = np.array([[1.0, 0.0, 5.0], [0.0, 1.0, 5.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_RIGID, AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_transform_homography_valid():
    m = np.eye(3, dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_HOMOGRAPHY, AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_transform_homography_invalid_area():
    m = np.array([[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_HOMOGRAPHY, AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "area change too large" in reason


def test_check_transform_homography_invalid_aspect():
    m = np.array([[2.0, 0.0, 0.0], [0.0, 0.5, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_HOMOGRAPHY, AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "aspect ratio change too large" in reason


def test_check_transform_invalid_type():
    m = np.eye(3, dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, 'invalid_type', AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "invalid transfrom option" in reason


def test_check_transform_rigid_invalid_rotation():
    angle_rad = math.radians(25.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([[cos_a, sin_a, 0], [-sin_a, cos_a, 0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_RIGID, AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "rotation too large" in reason


def test_check_transform_rigid_invalid_translation():
    m = np.array([[1.0, 0.0, 20.0], [0.0, 1.0, 15.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_RIGID, AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "translation too large" in reason


def test_check_transform_rigid_invalid_scale():
    m = np.array([[0.8, 0.0, 0.0], [0.0, 1.2, 0.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_RIGID, AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "x-scale out of range" in reason


def test_check_transform_homography_invalid_skew():
    m = np.array([[1.0, 0.5, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_HOMOGRAPHY, AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "angle distortion too large" in reason


def test_check_transform_rigid_combined_invalid():
    angle_rad = math.radians(15.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([[0.8 * cos_a, 0.8 * sin_a, 20.0],
                  [-0.8 * sin_a, 1.2 * cos_a, 15.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_RIGID, AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "rotation too large" in reason
    assert "x-scale out of range" in reason
    assert "y-scale out of range" in reason
    assert "translation too large" in reason


def test_check_transform_none_thresholds():
    m = np.array([[2.0, 0.0, 100.0], [0.0, 2.0, 100.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(m, img_shape, constants.ALIGN_RIGID, None, None)
    assert is_valid
    assert "No thresholds provided" in reason


def test_check_transform_homography_none_thresholds():
    m = np.array([[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(m, img_shape, constants.ALIGN_HOMOGRAPHY, None, None)
    assert is_valid
    assert "No thresholds provided" in reason


def test_decompose_affine_matrix_shear():
    m = np.array([[1.0, 0.2, 0.0], [0.1, 1.0, 0.0]], dtype=np.float64)
    scales, rotation, shear, translation = decompose_affine_matrix(m)
    assert math.isclose(scales[0], 1.0198039, abs_tol=1e-6)
    assert math.isclose(scales[1], 1.0049875, abs_tol=1e-6)
    assert math.isclose(rotation, 11.309932, abs_tol=1e-6)
    assert math.isclose(shear, -17.020525, abs_tol=1e-6)
    assert math.isclose(translation[0], 0.0, abs_tol=1e-10)
    assert math.isclose(translation[1], 0.0, abs_tol=1e-10)


def test_decompose_affine_matrix_combined():
    angle_rad = math.radians(30.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([[1.5 * cos_a, 1.5 * sin_a, 25.0],
                  [-0.8 * sin_a, 0.8 * cos_a, -15.0]], dtype=np.float64)
    scales, rotation, shear, translation = decompose_affine_matrix(m)
    assert math.isclose(scales[0], 1.5, abs_tol=1e-6)
    assert math.isclose(scales[1], 0.8, abs_tol=1e-6)
    assert math.isclose(rotation, 30.0, abs_tol=1e-6)
    assert math.isclose(shear, 0.0, abs_tol=1e-6)
    assert math.isclose(translation[0], 25.0, abs_tol=1e-10)
    assert math.isclose(translation[1], -15.0, abs_tol=1e-10)


def test_check_affine_matrix_zero_matrix():
    m = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape, AFFINE_THRESHOLDS)
    assert not is_valid
    assert "x-scale out of range" in reason
    assert "y-scale out of range" in reason


def test_check_homography_distortion_identity():
    m = np.eye(3, dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(
        m, img_shape, homography_thresholds=HOMOGRAPHY_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason
    area_ratio, aspect_ratio, max_angle_dev = result
    assert math.isclose(area_ratio, 1.0, abs_tol=1e-10)
    assert math.isclose(aspect_ratio, 1.0, abs_tol=1e-10)
    assert math.isclose(max_angle_dev, 0.0, abs_tol=1e-10)


def test_check_homography_distortion_translation():
    m = np.array([[1.0, 0.0, 10.0], [0.0, 1.0, 5.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(
        m, img_shape, homography_thresholds=HOMOGRAPHY_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason
    area_ratio, aspect_ratio, max_angle_dev = result
    assert math.isclose(area_ratio, 1.0, abs_tol=1e-10)
    assert math.isclose(aspect_ratio, 1.0, abs_tol=1e-10)
    assert math.isclose(max_angle_dev, 0.0, abs_tol=1e-10)


def test_check_homography_distortion_rotation_scale():
    angle = 5.0
    scale = 1.2
    angle_rad = math.radians(angle)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([
        [scale * cos_a, -scale * sin_a, 0],
        [scale * sin_a, scale * cos_a, 0],
        [0, 0, 1]
    ], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(
        m, img_shape, homography_thresholds=HOMOGRAPHY_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason
    area_ratio, aspect_ratio, max_angle_dev = result
    assert math.isclose(area_ratio, scale * scale, abs_tol=1e-6)
    assert math.isclose(aspect_ratio, 1.0, abs_tol=1e-6)
    assert math.isclose(max_angle_dev, 0.0, abs_tol=1e-5)


def test_align_frames_base_initialization():
    align_base = AlignFramesBase()
    assert align_base.enabled
    assert align_base.feature_config == DEFAULT_FEATURE_CONFIG
    assert align_base.matching_config == DEFAULT_MATCHING_CONFIG
    assert align_base.alignment_config == DEFAULT_ALIGNMENT_CONFIG
    assert align_base.min_matches == 3


def test_align_frames_base_custom_initialization():
    custom_feature = {'detector': 'ORB', 'descriptor': 'ORB'}
    custom_matching = {'match_method': 'NORM_HAMMING', 'threshold': 0.8}
    custom_alignment = {'transform': 'rigid', 'align_method': 'RANSAC'}
    align_base = AlignFramesBase(
        enabled=False,
        feature_config=custom_feature,
        matching_config=custom_matching,
        alignment_config=custom_alignment
    )
    assert not align_base.enabled
    assert align_base.feature_config['detector'] == 'ORB'
    assert align_base.feature_config['descriptor'] == 'ORB'
    assert align_base.matching_config['match_method'] == 'NORM_HAMMING'
    assert align_base.matching_config['threshold'] == 0.8
    assert align_base.alignment_config['transform'] == 'rigid'
    assert align_base.alignment_config['align_method'] == 'RANSAC'
    assert align_base.min_matches == 3


def test_align_frames_base_homography_initialization():
    custom_alignment = {'transform': constants.ALIGN_HOMOGRAPHY}
    align_base = AlignFramesBase(alignment_config=custom_alignment)
    assert align_base.min_matches == 4


def test_align_frames_base_get_transform_thresholds():
    align_base = AlignFramesBase()
    affine_thresholds, homography_thresholds = align_base.get_transform_thresholds()
    assert affine_thresholds == AFFINE_THRESHOLDS
    assert homography_thresholds == HOMOGRAPHY_THRESHOLDS


def test_align_frames_base_save_transform_result_rigid():
    align_base = AlignFramesBase(alignment_config={'transform': constants.ALIGN_RIGID})
    align_base._scale_x = np.ones(5)
    align_base._scale_y = np.ones(5)
    align_base._translation_x = np.zeros(5)
    align_base._translation_y = np.zeros(5)
    align_base._rotation = np.zeros(5)
    align_base._shear = np.zeros(5)
    align_base._subsamples = np.ones(5)
    result = (1.1, 0.9, 10.0, -5.0, 2.0, 1.0)
    align_base.save_transform_result(2, result)
    assert align_base._scale_x[2] == 1.1
    assert align_base._scale_y[2] == 0.9
    assert align_base._translation_x[2] == 10.0
    assert align_base._translation_y[2] == -5.0
    assert align_base._rotation[2] == 2.0
    assert align_base._shear[2] == 1.0


def test_align_frames_base_save_transform_result_homography():
    align_base = AlignFramesBase(alignment_config={'transform': constants.ALIGN_HOMOGRAPHY})
    align_base._area_ratio = np.ones(5)
    align_base._aspect_ratio = np.ones(5)
    align_base._max_angle_dev = np.zeros(5)
    result = (1.2, 1.5, 3.0)
    align_base.save_transform_result(3, result)
    assert align_base._area_ratio[3] == 1.2
    assert align_base._aspect_ratio[3] == 1.5
    assert align_base._max_angle_dev[3] == 3.0


def test_align_frames_base_save_transform_result_none():
    align_base = AlignFramesBase()
    align_base._scale_x = np.ones(5)
    align_base._scale_y = np.ones(5)
    align_base.save_transform_result(1, None)
    assert align_base._scale_x[1] == 1.0
    assert align_base._scale_y[1] == 1.0


def test_align_frames_initialization():
    align_frames = AlignFrames()
    assert align_frames.sequential_processing()


def test_align_frames_run_frame_reference_frame():
    align_frames = AlignFrames()

    class MockProcess:
        ref_idx = 0

        def img_ref(self, idx):
            return np.ones((10, 10, 3))

    align_frames.process = MockProcess()
    test_image = np.ones((10, 10, 3))
    result = align_frames.run_frame(0, 0, test_image)
    assert np.array_equal(result, test_image)


def test_align_frames_run_frame_non_reference():
    align_frames = AlignFrames()

    class MockProcess:
        ref_idx = 0

        def saved_img_ref(self, idx):
            return np.ones((10, 10, 3))

    align_frames.process = MockProcess()
    align_frames.align_images = lambda idx, img_ref, img_0: np.zeros((10, 10, 3))
    test_image = np.ones((10, 10, 3))
    result = align_frames.run_frame(1, 0, test_image)
    assert np.array_equal(result, np.zeros((10, 10, 3)))


def test_align_frames_run_frame_align_images_exception():
    align_frames = AlignFrames()

    class MockProcess:
        ref_idx = 0

        def saved_img_ref(self, idx):
            return np.ones((10, 10, 3))

    align_frames.process = MockProcess()
    align_frames.align_images = lambda idx, img_ref, img_0: \
        (_ for _ in ()).throw(Exception("Test exception"))
    test_image = np.ones((10, 10, 3))
    try:
        align_frames.run_frame(1, 0, test_image)
        assert False
    except Exception as e:
        assert str(e) == "Test exception"


def test_align_frames_begin_initializes_arrays():
    align_frames = AlignFrames()

    class MockProcess:
        total_action_counts = 5

    align_frames.begin(MockProcess())
    assert len(align_frames._n_good_matches) == 5
    assert len(align_frames._area_ratio) == 5
    assert len(align_frames._aspect_ratio) == 5
    assert len(align_frames._max_angle_dev) == 5
    assert len(align_frames._scale_x) == 5
    assert len(align_frames._scale_y) == 5
    assert len(align_frames._translation_x) == 5
    assert len(align_frames._translation_y) == 5
    assert len(align_frames._rotation) == 5
    assert len(align_frames._shear) == 5


def test_align_frames_end_no_plot_summary():
    align_frames = AlignFrames(plot_summary=False)

    class MockProcess:
        ref_idx = 1
        working_path = "/tmp"
        plot_path = "plots"
        name = "test"
        id = 1

        def callback(self, callback_type, process_id, description, plot_path):
            pass

    align_frames.process = MockProcess()
    align_frames._n_good_matches = np.array([10, 0, 15, 20])
    align_frames._area_ratio = np.array([1.0, 1.0, 1.1, 0.9])
    align_frames._aspect_ratio = np.array([1.0, 1.0, 1.2, 0.8])
    align_frames._max_angle_dev = np.array([0.0, 0.0, 1.0, 2.0])
    align_frames._scale_x = np.array([1.0, 1.0, 1.05, 0.95])
    align_frames._scale_y = np.array([1.0, 1.0, 0.95, 1.05])
    align_frames._translation_x = np.array([0.0, 0.0, 5.0, -5.0])
    align_frames._translation_y = np.array([0.0, 0.0, -3.0, 3.0])
    align_frames._rotation = np.array([0.0, 0.0, 1.0, -1.0])
    align_frames._shear = np.array([0.0, 0.0, 0.5, -0.5])
    align_frames.end()


def test_align_frames_end_with_plot_summary_rigid():
    align_frames = AlignFrames(
        plot_summary=True, alignment_config={
            'transform': constants.ALIGN_RIGID,
            'rans_inlier_fraction_threshold': 0.5,
            'rans_avg_error_threshold': 1.0,
            'rans_max_error_threshold': 2.0
        })

    class MockProcess:
        ref_idx = 2
        working_path = "/tmp"
        output_path = "output"
        plot_path = "plots"
        name = "test"
        id = 1
        callback_calls = []
        plot_manager = MagicMock()

        def callback(self, callback_type, process_id, name, description, plot_path):
            self.callback_calls.append((callback_type, name, description, plot_path))

    process = MockProcess()
    align_frames.process = process
    align_frames._n_good_matches = np.array([10, 20, 0, 15, 25])
    align_frames._scale_x = np.array([1.0, 1.05, 1.0, 0.95, 1.02])
    align_frames._scale_y = np.array([1.0, 0.95, 1.0, 1.05, 0.98])
    align_frames._translation_x = np.array([0.0, 5.0, 0.0, -3.0, 2.0])
    align_frames._translation_y = np.array([0.0, -2.0, 0.0, 4.0, -1.0])
    align_frames._rotation = np.array([0.0, 1.5, 0.0, -2.0, 0.5])
    align_frames._shear = np.array([0.0, 0.3, 0.0, -0.4, 0.1])
    align_frames._subsamples = np.array([1, 1, 1, 1, 1])
    align_frames._inlier_fractions = np.zeros(5)
    align_frames._avg_errors = np.zeros(5)
    align_frames._max_errors = np.zeros(5)
    align_frames._area_ratio = np.ones(5)
    align_frames._aspect_ratio = np.ones(5)
    align_frames._max_angle_dev = np.zeros(5)
    align_frames.end()
    assert len(process.callback_calls) == 5
    process.plot_manager.save_plot.assert_called()


def test_align_frames_end_with_plot_summary_homography():
    align_frames = AlignFrames(
        plot_summary=True, alignment_config={
            'transform': constants.ALIGN_HOMOGRAPHY,
            'rans_inlier_fraction_threshold': 0.5,
            'rans_avg_error_threshold': 1.0,
            'rans_max_error_threshold': 2.0
        })

    class MockProcess:
        ref_idx = 1
        working_path = "/tmp"
        output_path = "output"
        plot_path = "plots"
        name = "test"
        id = 1
        callback_calls = []
        plot_manager = MagicMock()

        def callback(self, callback_type, process_id, name, description, plot_path):
            self.callback_calls.append((callback_type, name, description, plot_path))

    process = MockProcess()
    align_frames.process = process
    align_frames._n_good_matches = np.array([15, 0, 20, 25])
    align_frames._area_ratio = np.array([1.0, 1.0, 1.1, 0.9])
    align_frames._aspect_ratio = np.array([1.0, 1.0, 1.2, 0.8])
    align_frames._max_angle_dev = np.array([0.0, 0.0, 1.0, 2.0])
    align_frames._inlier_fractions = np.zeros(4)
    align_frames._avg_errors = np.zeros(4)
    align_frames._max_errors = np.zeros(4)
    align_frames._scale_x = np.ones(4)
    align_frames._scale_y = np.ones(4)
    align_frames._translation_x = np.zeros(4)
    align_frames._translation_y = np.zeros(4)
    align_frames._rotation = np.zeros(4)
    align_frames._shear = np.zeros(4)
    align_frames._subsamples = np.ones(4)
    align_frames.end()
    assert len(process.callback_calls) == 5
    process.plot_manager.save_plot.assert_called()


def test_align_frames_image_str():
    align_frames = AlignFrames()

    class MockProcess:
        def frame_str(self, idx):
            return f"Frame {idx}"

        def input_filepath(self, idx):
            return f"/path/to/file_{idx:04d}.jpg"

    align_frames.process = MockProcess()
    result = align_frames.image_str(5)
    assert result == "Frame 5, file_0005.jpg"


def test_align_frames_print_message():
    align_frames = AlignFrames()

    class MockProcess:
        messages = []

        def print_message(self, msg, level=None):
            self.messages.append((msg, level))

    align_frames.process = MockProcess()
    align_frames.print_message("Test message", constants.LOG_COLOR_LEVEL_3, logging.WARNING)
    assert len(align_frames.process.messages) == 1
    assert "Test message" in align_frames.process.messages[0][0]


if __name__ == "__main__":
    test_identity_matrix()
    test_translation_only()
    test_rotation_only()
    test_scale_only()
    test_check_affine_matrix_valid()
    test_check_affine_matrix_invalid_rotation()
    test_check_affine_matrix_invalid_scale()
    test_check_affine_matrix_invalid_translation()
    test_check_homography_distortion_valid()
    test_check_homography_distortion_invalid_area()
    test_check_homography_distortion_invalid_aspect()
    test_check_homography_distortion_skew()
    test_check_affine_matrix_valid_rotation()
    test_check_affine_matrix_valid_scale()
    test_check_affine_matrix_valid_translation()
    test_check_affine_matrix_valid_shear()
    test_check_affine_matrix_combined_valid()
    test_check_homography_distortion_valid_scale()
    test_check_homography_distortion_valid_aspect()
    test_check_homography_distortion_valid_skew()
    test_check_affine_matrix_combined_invalid()
    test_check_transform_rigid_valid()
    test_check_transform_homography_valid()
    test_check_transform_homography_invalid_area()
    test_check_transform_homography_invalid_aspect()
    test_check_transform_invalid_type()
    test_check_transform_rigid_invalid_rotation()
    test_check_transform_rigid_invalid_translation()
    test_check_transform_rigid_invalid_scale()
    test_check_transform_homography_invalid_skew()
    test_check_transform_rigid_combined_invalid()
    test_check_transform_none_thresholds()
    test_check_transform_homography_none_thresholds()
    test_decompose_affine_matrix_shear()
    test_decompose_affine_matrix_combined()
    test_check_affine_matrix_zero_matrix()
    test_check_homography_distortion_identity()
    test_check_homography_distortion_translation()
    test_check_homography_distortion_rotation_scale()
    test_align_frames_base_initialization()
    test_align_frames_base_custom_initialization()
    test_align_frames_base_homography_initialization()
    test_align_frames_base_get_transform_thresholds()
    test_align_frames_base_save_transform_result_rigid()
    test_align_frames_base_save_transform_result_homography()
    test_align_frames_base_save_transform_result_none()
    test_align_frames_initialization()
    test_align_frames_run_frame_reference_frame()
    test_align_frames_run_frame_non_reference()
    test_align_frames_run_frame_align_images_exception()
    test_align_frames_begin_initializes_arrays()
    test_align_frames_end_no_plot_summary()
    test_align_frames_end_with_plot_summary_rigid()
    test_align_frames_end_with_plot_summary_homography()
    test_align_frames_image_str()
    test_align_frames_print_message()
