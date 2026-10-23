import pytest
import numpy as np
import cv2
from unittest.mock import MagicMock, patch
from shinestacker.config.constants import constants
from shinestacker.core.exceptions import InvalidOptionError
from shinestacker.algorithms.transform_estimate import (
    find_transform, rescale_transform, TransformationExtractor,
    find_transform_phase_correlation, plot_matches,
    check_homography_distortion, decompose_affine_matrix,
    AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS)


def test_find_transform_invalid_method():
    src_pts = np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float32)
    dst_pts = np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float32)
    subsample = 1
    with pytest.raises(InvalidOptionError):
        find_transform(src_pts, dst_pts, subsample, method='INVALID_METHOD')


def test_find_transform_invalid_transform():
    src_pts = np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float32)
    dst_pts = np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float32)
    subsample = 1
    with pytest.raises(InvalidOptionError):
        find_transform(src_pts, dst_pts, subsample, transform='INVALID_TRANSFORM')


def test_rescale_transform_invalid_type():
    m = np.eye(3)
    result = rescale_transform(m, 100, 100, 50, 50, 2, 'INVALID_TYPE')
    assert result == 0


def test_apply_alignment_transform_invalid_border_mode():
    align_config = {'border_mode': 'INVALID_MODE', 'transform': 'rigid', 'border_value': 0}
    extractor = TransformationExtractor(align_config, None, None)
    img_0 = np.ones((100, 100, 3), dtype=np.uint8)
    img_ref = np.ones((100, 100, 3), dtype=np.uint8)
    m = np.float32([[1, 0, 0], [0, 1, 0]])
    with pytest.raises(InvalidOptionError):
        extractor.apply_alignment_transform(img_0, img_ref, m)


def test_extract_transformation_insufficient_matches_no_fallback():
    alignment_config = {
        'transform': 'rigid',
        'min_good_matches': 10,
        'phase_corr_fallback': False,
        'abort_abnormal': False
    }
    extractor = TransformationExtractor(alignment_config, None, None)
    match_result = MagicMock()
    match_result.has_sufficient_matches.return_value = False
    match_result.n_good_matches.return_value = 5
    callbacks = {'warning': MagicMock()}
    result = extractor.extract_transformation(
        match_result, None, None, 1, (100, 100), callbacks)
    assert result[0] is None
    callbacks['warning'].assert_called_once()


def test_extract_transformation_phase_correlation_fallback():
    alignment_config = {
        'transform': 'rigid', 'min_good_matches': 10,
        'phase_corr_fallback': True, 'abort_abnormal': False}
    extractor = TransformationExtractor(alignment_config, None, None)
    match_result = MagicMock()
    match_result.has_sufficient_matches.return_value = False
    match_result.n_good_matches.return_value = 5
    callbacks = {'warning': MagicMock()}
    img_ref_sub = np.ones((50, 50, 3), dtype=np.uint8)
    img_0_sub = np.ones((50, 50, 3), dtype=np.uint8)
    with patch('shinestacker.algorithms.transform_estimate.'
               'find_transform_phase_correlation') as mock_phase:
        with patch('shinestacker.algorithms.transform_estimate.check_transform') as mock_check:
            mock_phase.return_value = np.float32([[1, 0, 0], [0, 1, 0]])
            mock_check.return_value = (True, "Valid", None)
            result = extractor.extract_transformation(
                match_result, img_ref_sub, img_0_sub, 1, (100, 100), callbacks)
    assert result[1]
    callbacks['warning'].assert_called_once_with(
        "only 5 < 10 matches found, using phase correlation as fallback")


def test_extract_transformation_valid_phase_correlation():
    from shinestacker.algorithms.transform_estimate import TransformationExtractor
    from unittest.mock import MagicMock, patch
    alignment_config = {
        'transform': 'rigid', 'min_good_matches': 10,
        'phase_corr_fallback': True, 'abort_abnormal': False}
    extractor = TransformationExtractor(alignment_config, AFFINE_THRESHOLDS, None)
    match_result = MagicMock()
    match_result.has_sufficient_matches.return_value = False
    match_result.n_good_matches.return_value = 5
    callbacks = {'warning': MagicMock(), 'matches_message': MagicMock()}
    img_ref_sub = np.ones((50, 50, 3), dtype=np.uint8)
    img_0_sub = np.ones((50, 50, 3), dtype=np.uint8)
    with patch('shinestacker.algorithms.transform_estimate.'
               'find_transform_phase_correlation') as mock_phase:
        with patch('shinestacker.algorithms.'
                   'transform_estimate.check_transform') as mock_check:
            mock_phase.return_value = np.float32([[1, 0, 0], [0, 1, 0]])
            mock_check.return_value = (True, "Valid", None)
            result = extractor.extract_transformation(
                match_result, img_ref_sub, img_0_sub, 1, (100, 100), callbacks)
    assert result[0] is not None
    assert result[1]
    callbacks['warning'].assert_called_once_with(
        "only 5 < 10 matches found, using phase correlation as fallback")


def test_extract_transformation_phase_correlation_fails():
    alignment_config = {
        'transform': 'rigid', 'min_good_matches': 10,
        'phase_corr_fallback': True, 'abort_abnormal': False}
    extractor = TransformationExtractor(alignment_config, None, None)
    match_result = MagicMock()
    match_result.has_sufficient_matches.return_value = False
    match_result.n_good_matches.return_value = 5
    callbacks = {'warning': MagicMock()}
    img_ref_sub = np.ones((50, 50, 3), dtype=np.uint8)
    img_0_sub = np.ones((50, 50, 3), dtype=np.uint8)
    with patch('shinestacker.algorithms.transform_estimate.'
               'find_transform_phase_correlation') as mock_phase:
        mock_phase.return_value = None
        result = extractor.extract_transformation(
            match_result, img_ref_sub, img_0_sub, 1, (100, 100), callbacks)
    assert result[0] is None
    assert result[1]
    assert callbacks['warning'].call_count == 2


def test_extract_transformation_valid_matches():
    from shinestacker.algorithms.transform_estimate import TransformationExtractor
    from unittest.mock import MagicMock, patch
    alignment_config = {
        'transform': 'rigid', 'min_good_matches': 10, 'phase_corr_fallback': True,
        'abort_abnormal': False, 'align_method': 'RANSAC', 'rans_threshold': 3.0,
        'max_iters': 1000, 'align_confidence': 95, 'refine_iters': 10,
        'compute_rans_quality': False,
        'rans_inlier_fraction_threshold': 0.9,
        'rans_avg_error_threshold': 0.2,
        'rans_max_error_threshold': 3,
    }
    extractor = TransformationExtractor(alignment_config, AFFINE_THRESHOLDS, None)
    match_result = MagicMock()
    match_result.has_sufficient_matches.return_value = True
    match_result.n_good_matches.return_value = 15
    match_result.get_src_points.return_value = np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float32)
    match_result.get_dst_points.return_value = np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float32)
    callbacks = {'warning': MagicMock(), 'matches_message': MagicMock()}
    img_ref_sub = np.ones((50, 50, 3), dtype=np.uint8)
    img_0_sub = np.ones((50, 50, 3), dtype=np.uint8)
    with patch('shinestacker.algorithms.transform_estimate.find_transform') as mock_find:
        with patch('shinestacker.algorithms.transform_estimate.check_transform') as mock_check:
            mock_find.return_value = (np.float32([[1, 0, 0], [0, 1, 0]]), np.array([1, 1, 1]), {})
            mock_check.return_value = (True, "Valid", None)
            result = extractor.extract_transformation(match_result, img_ref_sub, img_0_sub, 1,
                                                      (100, 100), callbacks)
    assert result[0] is not None
    callbacks['matches_message'].assert_called_once_with(15)


def test_extract_transformation_invalid_transform():
    alignment_config = {
        'transform': 'rigid', 'min_good_matches': 10,
        'phase_corr_fallback': True, 'abort_abnormal': False,
        'align_method': 'RANSAC', 'rans_threshold': 3.0,
        'max_iters': 1000, 'align_confidence': 95, 'refine_iters': 10,
        'compute_rans_quality': False,
        'rans_inlier_fraction_threshold': 0.9,
        'rans_avg_error_threshold': 0.2,
        'rans_max_error_threshold': 3,
    }
    extractor = TransformationExtractor(alignment_config, AFFINE_THRESHOLDS, None)
    match_result = MagicMock()
    match_result.has_sufficient_matches.return_value = True
    match_result.n_good_matches.return_value = 15
    match_result.get_src_points.return_value = np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float32)
    match_result.get_dst_points.return_value = np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float32)
    callbacks = {'warning': MagicMock()}
    img_ref_sub = np.ones((50, 50, 3), dtype=np.uint8)
    img_0_sub = np.ones((50, 50, 3), dtype=np.uint8)
    with patch('shinestacker.algorithms.transform_estimate.find_transform') as mock_find:
        with patch('shinestacker.algorithms.transform_estimate.check_transform') as mock_check:
            mock_find.return_value = (np.float32([[2, 0, 0], [0, 2, 0]]), np.array([1, 1, 1]), {})
            mock_check.return_value = (False, "Invalid transform", None)
            result = extractor.extract_transformation(
                match_result, img_ref_sub, img_0_sub, 1, (100, 100), callbacks)
    assert result[0] is None
    callbacks['warning'].assert_called_once_with(
        "invalid transformation: Invalid transform, alignment failed")


def test_apply_alignment_transform_invalid_matrix_shapes():
    from shinestacker.config import constants
    align_config = {
        'border_mode': constants.BORDER_CONSTANT, 'transform': constants.ALIGN_RIGID,
        'border_value': 0, 'border_blur': 5
    }
    extractor = TransformationExtractor(align_config, None, None)
    img_0 = np.ones((100, 100, 3), dtype=np.uint8)
    img_ref = np.ones((100, 100, 3), dtype=np.uint8)
    m_wrong_rigid = np.eye(3)
    callbacks = {'warning': MagicMock()}
    result = extractor.apply_alignment_transform(img_0, img_ref, m_wrong_rigid, callbacks)
    assert result is None
    callbacks['warning'].assert_called_once()


def test_extract_transformation_abort_abnormal():
    alignment_config = {
        'transform': 'rigid', 'min_good_matches': 10,
        'phase_corr_fallback': True, 'abort_abnormal': True,
        'align_method': 'RANSAC', 'rans_threshold': 3.0,
        'max_iters': 1000, 'align_confidence': 95, 'refine_iters': 10,
        'compute_rans_quality': False,
        'rans_inlier_fraction_threshold': 0.9,
        'rans_avg_error_threshold': 0.2,
        'rans_max_error_threshold': 3,
    }
    extractor = TransformationExtractor(alignment_config, AFFINE_THRESHOLDS, None)
    match_result = MagicMock()
    match_result.has_sufficient_matches.return_value = True
    match_result.n_good_matches.return_value = 15
    match_result.get_src_points.return_value = np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float32)
    match_result.get_dst_points.return_value = np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float32)
    callbacks = {'warning': MagicMock()}
    img_ref_sub = np.ones((50, 50, 3), dtype=np.uint8)
    img_0_sub = np.ones((50, 50, 3), dtype=np.uint8)
    with patch('shinestacker.algorithms.transform_estimate.find_transform') as mock_find:
        with patch('shinestacker.algorithms.transform_estimate.check_transform') as mock_check:
            mock_find.return_value = (np.float32([[2, 0, 0], [0, 2, 0]]), np.array([1, 1, 1]), {})
            mock_check.return_value = (False, "Invalid transform", None)
            with pytest.raises(RuntimeError):
                extractor.extract_transformation(
                    match_result, img_ref_sub, img_0_sub, 1, (100, 100), callbacks)


def test_extract_transformation_with_plot_path():
    alignment_config = {
        'transform': 'rigid', 'min_good_matches': 10,
        'phase_corr_fallback': False, 'abort_abnormal': False,
        'align_method': 'RANSAC', 'rans_threshold': 3.0,
        'max_iters': 1000, 'align_confidence': 95, 'refine_iters': 10,
        'compute_rans_quality': False,
        'rans_inlier_fraction_threshold': 0.9,
        'rans_avg_error_threshold': 0.2,
        'rans_max_error_threshold': 3,
    }
    extractor = TransformationExtractor(alignment_config, AFFINE_THRESHOLDS, None)
    match_result = MagicMock()
    match_result.has_sufficient_matches.return_value = True
    match_result.n_good_matches.return_value = 15
    match_result.get_src_points.return_value = np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float32)
    match_result.get_dst_points.return_value = np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float32)
    match_result.kp_ref = []
    match_result.kp_0 = []
    match_result.good_matches = []
    callbacks = {'warning': MagicMock(), 'save_plot': MagicMock()}
    img_ref_sub = np.ones((50, 50, 3), dtype=np.uint8)
    img_0_sub = np.ones((50, 50, 3), dtype=np.uint8)
    plot_manager = MagicMock()
    with patch('shinestacker.algorithms.transform_estimate.find_transform') as mock_find:
        with patch('shinestacker.algorithms.transform_estimate.check_transform') as mock_check:
            with patch('shinestacker.algorithms.transform_estimate.plot_matches') as mock_plot:
                mock_find.return_value = (np.float32([[1, 0, 0], [0, 1, 0]]),
                                          np.array([1, 1, 1]), {})
                mock_check.return_value = (True, "Valid", None)
                extractor.extract_transformation(
                    match_result, img_ref_sub, img_0_sub, 1, (100, 100),
                    callbacks, "test_plot.png", plot_manager)
                mock_plot.assert_called_once()
                callbacks['save_plot'].assert_called_once_with("test_plot.png", tag="matches")


def test_find_transform_phase_correlation_identical_images():
    img_ref = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
    img_0 = img_ref.copy()
    m = find_transform_phase_correlation(img_ref, img_0)
    assert m is not None
    assert m.shape == (2, 3)
    assert abs(m[0, 0] - 1.0) < 0.01
    assert abs(m[1, 1] - 1.0) < 0.01
    assert abs(m[0, 2]) < 1.0
    assert abs(m[1, 2]) < 1.0


def test_find_transform_phase_correlation_color_images():
    img_ref = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    img_0 = img_ref.copy()
    m = find_transform_phase_correlation(img_ref, img_0)
    assert m is not None
    assert m.shape == (2, 3)
    assert abs(m[0, 0] - 1.0) < 0.01
    assert abs(m[1, 1] - 1.0) < 0.01
    assert abs(m[0, 2]) < 1.0
    assert abs(m[1, 2]) < 1.0


def test_rescale_transform_rigid():
    m = np.array([[1.0, 0.0, 10.0], [0.0, 1.0, 5.0]], dtype=np.float32)
    result = rescale_transform(m, 200, 200, 100, 100, 2, constants.ALIGN_RIGID)
    assert result is not None
    assert result.shape == (2, 3)
    assert abs(result[0, 2] - 20.0) < 0.001
    assert abs(result[1, 2] - 10.0) < 0.001


def test_plot_matches():
    msk = np.array([1, 1, 0], dtype=np.uint8)
    img_ref_sub = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
    img_0_sub = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
    kp_ref = [cv2.KeyPoint(10, 10, 5), cv2.KeyPoint(20, 20, 5), cv2.KeyPoint(30, 30, 5)]
    kp_0 = [cv2.KeyPoint(15, 15, 5), cv2.KeyPoint(25, 25, 5), cv2.KeyPoint(35, 35, 5)]
    good_matches = [cv2.DMatch(0, 0, 0, 0), cv2.DMatch(1, 1, 0, 0), cv2.DMatch(2, 2, 0, 0)]
    plot_path = "test_plot.png"
    plot_manager = MagicMock()
    plot_matches(msk, img_ref_sub, img_0_sub, kp_ref, kp_0, good_matches, plot_path, plot_manager)
    plot_manager.save_plot.assert_called_once()
    plot_matches(msk, img_ref_sub, img_0_sub, kp_ref, kp_0, good_matches, plot_path, None)
    plot_matches(msk, img_ref_sub, img_0_sub, kp_ref, kp_0, [], plot_path, plot_manager)
    with patch('cv2.drawMatches') as mock_draw:
        mock_draw.return_value = None
        plot_matches(msk, img_ref_sub, img_0_sub, kp_ref, kp_0, good_matches,
                     plot_path, plot_manager)


def test_apply_alignment_transform_rigid_valid():
    align_config = {
        'border_mode': constants.BORDER_CONSTANT,
        'transform': constants.ALIGN_RIGID,
        'border_value': 0,
        'border_blur': 5
    }
    extractor = TransformationExtractor(align_config, None, None)
    img_0 = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    img_ref = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    m = np.float32([[1, 0, 10], [0, 1, 5]])
    result = extractor.apply_alignment_transform(img_0, img_ref, m)
    assert result is not None
    assert result.shape == img_ref.shape


def test_apply_alignment_transform_homography_valid():
    align_config = {
        'border_mode': constants.BORDER_CONSTANT,
        'transform': constants.ALIGN_HOMOGRAPHY,
        'border_value': 0,
        'border_blur': 5
    }
    extractor = TransformationExtractor(align_config, None, None)
    img_0 = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    img_ref = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    m = np.eye(3, dtype=np.float32)
    result = extractor.apply_alignment_transform(img_0, img_ref, m)
    assert result is not None
    assert result.shape == img_ref.shape


def test_apply_alignment_transform_border_replicate_blur():
    align_config = {
        'border_mode': constants.BORDER_REPLICATE_BLUR,
        'transform': constants.ALIGN_RIGID,
        'border_value': 0,
        'border_blur': 5
    }
    extractor = TransformationExtractor(align_config, None, None)
    img_0 = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    img_ref = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    m = np.float32([[1, 0, 10], [0, 1, 5]])
    callbacks = {'blur_message': MagicMock()}
    result = extractor.apply_alignment_transform(img_0, img_ref, m, callbacks)
    assert result is not None
    assert result.shape == img_ref.shape
    callbacks['blur_message'].assert_called_once()


def test_apply_alignment_transform_estimation_message():
    align_config = {
        'border_mode': constants.BORDER_CONSTANT,
        'transform': constants.ALIGN_RIGID,
        'border_value': 0,
        'border_blur': 5
    }
    extractor = TransformationExtractor(align_config, None, None)
    img_0 = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    img_ref = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    m = np.float32([[1, 0, 10], [0, 1, 5]])
    callbacks = {'estimation_message': MagicMock()}
    result = extractor.apply_alignment_transform(img_0, img_ref, m, callbacks)
    assert result is not None
    callbacks['estimation_message'].assert_called_once()


def test_decompose_affine_matrix_complex():
    angle = 30
    scale_x, scale_y = 1.5, 0.8
    tx, ty = 25.0, -15.0
    angle_rad = np.radians(angle)
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)
    m = np.array([
        [scale_x * cos_a, scale_x * sin_a, tx],
        [-scale_y * sin_a, scale_y * cos_a, ty]
    ], dtype=np.float64)
    scales, rotation, shear, translation = decompose_affine_matrix(m)
    assert abs(scales[0] - scale_x) < 1e-10
    assert abs(scales[1] - scale_y) < 1e-10
    assert abs(rotation - angle) < 1e-10
    assert abs(shear) < 1e-10
    assert abs(translation[0] - tx) < 1e-10
    assert abs(translation[1] - ty) < 1e-10


def test_check_homography_distortion_complex():
    m = np.array([[1.0, 0.2, 10.0], [0.1, 0.9, 5.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(m, img_shape, HOMOGRAPHY_THRESHOLDS)
    assert is_valid is not None
    assert reason is not None
    if result is not None:
        assert len(result) == 3


def test_apply_alignment_transform_interpolation():
    rng = np.random.default_rng(0)
    img = rng.integers(0, 65536, (64, 64, 3), dtype=np.uint16)
    m = np.float32([[1, 0, 0.5], [0, 1, 0.5]])
    detail = {}
    for interpolation in constants.VALID_INTERPOLATIONS:
        align_config = {
            'border_mode': constants.BORDER_REPLICATE,
            'transform': constants.ALIGN_RIGID,
            'border_value': 0,
            'interpolation': interpolation
        }
        extractor = TransformationExtractor(align_config, None, None)
        result = extractor.apply_alignment_transform(img, img, m)
        assert result.shape == img.shape and result.dtype == img.dtype
        gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY).astype(np.float64)
        detail[interpolation] = np.abs(cv2.Laplacian(gray, cv2.CV_64F))[8:-8, 8:-8].mean()
    assert detail[constants.INTER_CUBIC] > 1.2 * detail[constants.INTER_LINEAR]
    assert detail[constants.INTER_LANCZOS4] > detail[constants.INTER_CUBIC]


def test_apply_alignment_transform_invalid_interpolation():
    align_config = {'border_mode': constants.BORDER_CONSTANT, 'transform': constants.ALIGN_RIGID,
                    'border_value': 0, 'interpolation': 'INVALID'}
    extractor = TransformationExtractor(align_config, None, None)
    img = np.ones((10, 10, 3), dtype=np.uint8)
    with pytest.raises(InvalidOptionError):
        extractor.apply_alignment_transform(img, img, np.float32([[1, 0, 0], [0, 1, 0]]))
