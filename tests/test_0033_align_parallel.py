# pylint: disable=W0212
import threading
import logging
import pytest
from unittest.mock import Mock, patch
import cv2
import numpy as np
from shinestacker.config.constants import constants
from shinestacker.core.exceptions import RunStopException
from shinestacker.algorithms.align_parallel import AlignFramesParallel, compose_transforms
from shinestacker.algorithms.align import AlignFramesBase
from shinestacker.algorithms.transform_estimate import (
    TransformationExtractor,
    AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS, AFFINE_THRESHOLDS_LARGE,
    HOMOGRAPHY_THRESHOLDS_LARGE)


def test_compose_transforms():
    t1_rigid = np.array([[1, 0, 10], [0, 1, 20]], dtype=np.float64)
    t2_rigid = np.array([[0, -1, 5], [1, 0, 15]], dtype=np.float64)
    result_rigid = compose_transforms(t1_rigid, t2_rigid, constants.ALIGN_RIGID)
    assert result_rigid.shape == (2, 3)
    t1_homo = np.eye(3, dtype=np.float64)
    t1_homo[0, 2] = 10
    t2_homo = np.eye(3, dtype=np.float64)
    t2_homo[1, 2] = 20
    result_homo = compose_transforms(t1_homo, t2_homo, constants.ALIGN_HOMOGRAPHY)
    assert result_homo.shape == (3, 3)


def test_align_frames_parallel_initialization():
    aligner = AlignFramesParallel(
        max_threads=4,
        chunk_submit=False,
        bw_matching=True
    )
    assert aligner.max_threads == 4
    assert not aligner.chunk_submit
    assert aligner.bw_matching


def test_cache_img():
    aligner = AlignFramesParallel()
    aligner.process = Mock()
    aligner.process.input_filepath.return_value = "test_path.jpg"
    with patch('shinestacker.algorithms.align_parallel.read_img') as mock_read, \
         patch('shinestacker.algorithms.align_parallel.img_bw') as mock_bw:
        mock_read.return_value = np.ones((100, 100, 3), dtype=np.uint8)
        mock_bw.return_value = np.ones((100, 100), dtype=np.uint8)
        aligner._img_cache = [None]
        aligner._img_shapes = [None]
        aligner._img_locks = [0]
        aligner._cache_locks = [threading.Lock()]
        result = aligner.cache_img(0)
        assert result is not None
        assert aligner._img_cache[0] is not None
        result2 = aligner.cache_img(0)
        assert np.array_equal(result, result2)


def create_test_images():
    img1 = np.zeros((200, 200, 3), dtype=np.uint8)
    img2 = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.rectangle(img1, (50, 50), (70, 70), (255, 255, 255), -1)
    cv2.rectangle(img2, (55, 55), (75, 75), (255, 255, 255), -1)
    return img1, img2


def test_align_images_method():
    aligner = AlignFramesParallel(alignment_config={
        'transform': constants.ALIGN_RIGID,
        'border_mode': constants.BORDER_CONSTANT,
        'border_value': 0,
        'border_blur': 5
    })
    process = Mock()
    process.idx_tot_str = Mock(return_value="1/2")
    process.input_filepath = Mock(return_value="test.jpg")
    aligner.process = process
    aligner.get_transform_thresholds = Mock(
        return_value=(AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS))
    aligner.get_transform_thresholds_large = Mock(
        return_value=(AFFINE_THRESHOLDS_LARGE, HOMOGRAPHY_THRESHOLDS_LARGE))
    aligner.print_message = Mock()
    img_ref = np.ones((100, 100, 3), dtype=np.uint8)
    img_0 = np.ones((100, 100, 3), dtype=np.uint8)
    affine_thresholds, homography_thresholds = aligner.get_transform_thresholds()
    aligner.transformation_extractor = TransformationExtractor(
        aligner.alignment_config, affine_thresholds, homography_thresholds)
    aligner._cumulative_transforms = [None]
    result = aligner.align_images(0, img_ref, img_0)
    assert result is None
    aligner._cumulative_transforms = [np.eye(2, 3, dtype=np.float32)]
    result = aligner.align_images(0, img_ref, img_0)
    assert result.shape == img_ref.shape
    aligner.alignment_config['transform'] = constants.ALIGN_HOMOGRAPHY
    aligner._cumulative_transforms = [np.eye(3, dtype=np.float32)]
    result = aligner.align_images(0, img_ref, img_0)
    assert result.shape == img_ref.shape


def test_align_images_border_modes():
    aligner = AlignFramesParallel()
    process = Mock()
    process.idx_tot_str = Mock(return_value="1/2")
    process.input_filepath = Mock(return_value="test.jpg")
    aligner.process = process
    aligner.print_message = Mock()
    aligner.get_transform_thresholds = Mock(
        return_value=(AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS))
    aligner.get_transform_thresholds_large = Mock(
        return_value=(AFFINE_THRESHOLDS_LARGE, HOMOGRAPHY_THRESHOLDS_LARGE))
    affine_thresholds, homography_thresholds = aligner.get_transform_thresholds()
    aligner.transformation_extractor = TransformationExtractor(
        aligner.alignment_config, affine_thresholds, homography_thresholds)
    img_ref = np.ones((100, 100, 3), dtype=np.uint8)
    img_0 = np.ones((100, 100, 3), dtype=np.uint8)
    for border_mode in [constants.BORDER_CONSTANT,
                        constants.BORDER_REPLICATE,
                        constants.BORDER_REPLICATE_BLUR]:
        aligner.alignment_config['border_mode'] = border_mode
        aligner.alignment_config['border_value'] = 0
        aligner.alignment_config['border_blur'] = 5
        aligner.alignment_config['transform'] = constants.ALIGN_RIGID
        aligner.transformation_extractor.alignment_config = aligner.alignment_config
        aligner._cumulative_transforms = [np.eye(2, 3, dtype=np.float32)]
        result = aligner.align_images(0, img_ref, img_0)
        assert result.shape == img_ref.shape


def test_extract_features_fallback():
    aligner = AlignFramesParallel(alignment_config={
        'transform': constants.ALIGN_RIGID,
        'subsample': 1,
        'fast_subsampling': False,
        'min_good_matches': 100,
        'align_method': 'RANSAC',
        'rans_threshold': 3.0,
        'max_iters': 2000,
        'align_confidence': 0.99,
        'refine_iters': 10,
        'phase_corr_fallback': False,
        'abort_abnormal': False,
    })
    process = Mock()
    process.ref_idx = 0
    process.idx_tot_str = Mock(return_value="1/2")
    process.input_filepath = Mock(return_value="test.jpg")
    aligner.process = process
    aligner.print_message = Mock()
    aligner._n_good_matches = [0] * 2
    aligner._target_indices = [None] * 2
    aligner._transforms = [None] * 2
    with patch.object(aligner, 'cache_img') as mock_cache:
        mock_cache.side_effect = [
            np.ones((100, 100, 3), dtype=np.uint8),
            np.zeros((100, 100, 3), dtype=np.uint8)
        ]
        _info, warnings = aligner.find_transform(1)
        assert len(warnings) > 0


def test_submit_threads():
    aligner = AlignFramesParallel()
    aligner.process = Mock()
    aligner.process.idx_tot_str = Mock(return_value="1/2")
    aligner.process.input_filepath = Mock(side_effect=lambda idx: f"img{idx}.jpg")
    aligner.process.num_input_filepaths = Mock(return_value=3)
    aligner.print_message = Mock()
    aligner.find_transform = Mock(return_value=([], []))
    aligner.step_counter = 0
    aligner.process.after_step = Mock()
    aligner.process.check_running = Mock()
    aligner._n_good_matches = [0] * 3
    aligner._img_locks = [0] * 3
    aligner._img_cache = [None] * 3
    idxs = [1, 2]
    imgs = ["img1.jpg", "img2.jpg"]

    def create_mock_future(result):
        future = Mock()
        future.result.return_value = result
        return future

    with patch('shinestacker.algorithms.align_parallel.ThreadPoolExecutor') as mock_executor_class:
        mock_executor = Mock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        futures = []
        for idx in idxs:
            future = create_mock_future(([], []))
            futures.append(future)
        mock_executor.submit.side_effect = lambda fn, idx: futures.pop(0) \
            if futures else create_mock_future(([], []))
        with patch('shinestacker.algorithms.align_parallel.as_completed') as mock_as_completed:
            mock_as_completed.return_value = futures.copy()
            aligner.submit_threads(idxs, imgs)
            assert mock_executor.submit.call_count == len(idxs)
            assert aligner.process.after_step.call_count == len(idxs)


def test_submit_threads_with_exceptions():
    aligner = AlignFramesParallel()
    aligner.process = Mock()
    aligner.process.idx_tot_str = Mock(return_value="1/2")
    aligner.process.input_filepath = Mock(side_effect=lambda idx: f"img{idx}.jpg")
    aligner.process.num_input_filepaths = Mock(return_value=3)
    aligner.print_message = Mock()
    aligner.step_counter = 0
    aligner.process.after_step = Mock()
    aligner.process.check_running = Mock()
    aligner._n_good_matches = [0] * 3
    aligner._img_locks = [0] * 3
    aligner._img_cache = [None] * 3
    idxs = [1]
    imgs = ["img1.jpg"]
    with patch('shinestacker.algorithms.align_parallel.ThreadPoolExecutor') as mock_executor_class:
        mock_executor = Mock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        future = Mock()
        future.result.side_effect = Exception("Test exception")
        mock_executor.submit.return_value = future
        with patch('shinestacker.algorithms.align_parallel.as_completed') as mock_as_completed:
            mock_as_completed.return_value = [future]
            aligner.submit_threads(idxs, imgs)
            aligner.print_message.assert_called()
            assert "failed processing" in aligner.print_message.call_args[0][0]


def test_submit_threads_runstop_exception():
    aligner = AlignFramesParallel()
    aligner.process = Mock()
    aligner.process.idx_tot_str = Mock(return_value="1/2")
    aligner.process.input_filepath = Mock(side_effect=lambda idx: f"img{idx}.jpg")
    aligner.process.num_input_filepaths = Mock(return_value=3)
    aligner.print_message = Mock()
    aligner.step_counter = 0
    aligner.process.after_step = Mock()
    aligner.process.check_running = Mock()
    aligner._n_good_matches = [0] * 3
    aligner._img_locks = [0] * 3
    aligner._img_cache = [None] * 3
    idxs = [1]
    imgs = ["img1.jpg"]
    with patch('shinestacker.algorithms.align_parallel.ThreadPoolExecutor') as mock_executor_class:
        mock_executor = Mock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        future = Mock()
        future.result.side_effect = RunStopException("Stop requested")
        mock_executor.submit.return_value = future
        with patch('shinestacker.algorithms.align_parallel.as_completed') as mock_as_completed:
            mock_as_completed.return_value = [future]
            with pytest.raises(RunStopException):
                aligner.submit_threads(idxs, imgs)


def test_begin_initialization():
    aligner = AlignFramesParallel()
    process = Mock()
    process.num_input_filepaths = Mock(return_value=3)
    process.ref_idx = 1
    process.input_filepaths = Mock(return_value=["img0.jpg", "img1.jpg", "img2.jpg"])
    process.input_filepath = Mock(side_effect=lambda idx: f"img{idx}.jpg")
    process.callback = Mock()
    process.id = "test_id"
    process.name = "test_name"
    aligner.process = process
    aligner.print_message = Mock()
    with patch.object(AlignFramesBase, 'begin'):
        # Call just the initialization part of begin
        n_frames = aligner.process.num_input_filepaths()
        aligner.print_message(
            f"preprocess {n_frames} images in parallel, cores: {aligner.max_threads}")
        aligner.process.callback(constants.CALLBACK_STEP_COUNTS,
                                 aligner.process.id, aligner.process.name, 2 * n_frames)
        assert n_frames == 3
        aligner.print_message.assert_called()
        aligner.process.callback.assert_called()


def test_begin_transform_combination():
    aligner = AlignFramesParallel()
    aligner.process = Mock()
    aligner.print_message = Mock()
    n_frames = 3
    ref_idx = 1
    aligner._img_shapes = [(100, 100)] * n_frames
    aligner._cumulative_transforms = [None] * n_frames
    aligner._target_indices = [1, None, 1]
    aligner._transforms = [
        np.array([[1.0, 0.0, 10.0], [0.0, 1.0, 5.0]], dtype=np.float64),
        None,
        np.array([[1.0, 0.0, -5.0], [0.0, 1.0, -2.0]], dtype=np.float64)
    ]
    transform_type = constants.ALIGN_RIGID
    identity = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
    aligner._cumulative_transforms[ref_idx] = identity
    frames_to_process = []
    for i in range(n_frames):
        if i != ref_idx:
            frames_to_process.append((i, abs(i - ref_idx)))
    frames_to_process.sort(key=lambda x: x[1])
    for i, _ in frames_to_process:
        target_idx = aligner._target_indices[i]
        if target_idx is not None and aligner._cumulative_transforms[target_idx] is not None:
            aligner._cumulative_transforms[i] = compose_transforms(
                aligner._transforms[i], aligner._cumulative_transforms[target_idx], transform_type)
        else:
            aligner._cumulative_transforms[i] = None
            aligner.print_message(
                f"warning: no cumulative transform for {i}",
                color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
    assert aligner._cumulative_transforms[0] is not None
    assert aligner._cumulative_transforms[1] is not None
    assert aligner._cumulative_transforms[2] is not None


def test_find_transform_successful():
    aligner = AlignFramesParallel(alignment_config={
        'transform': constants.ALIGN_RIGID,
        'subsample': 1,
        'fast_subsampling': False,
        'min_good_matches': 4,
        'align_method': 'RANSAC',
        'rans_threshold': 3.0,
        'max_iters': 2000,
        'align_confidence': 0.99,
        'refine_iters': 10,
        'phase_corr_fallback': False,
        'abort_abnormal': False
    })
    process = Mock()
    process.ref_idx = 0
    process.idx_tot_str = Mock(return_value="1/2")
    process.input_filepath = Mock(side_effect=lambda idx: f"img{idx}.jpg")
    aligner.process = process
    aligner.print_message = Mock()
    aligner.get_transform_thresholds = Mock(return_value=(100, 0.5))
    img1, img2 = create_test_images()
    aligner._img_cache = [img1, img2]
    aligner._img_shapes = [img1.shape, img2.shape]
    aligner._img_locks = [1, 1]
    aligner._cache_locks = [threading.Lock(), threading.Lock()]
    aligner._n_good_matches = [0, 0]
    aligner._target_indices = [None, None]
    aligner._transforms = [None, None]
    with patch.object(aligner, 'cache_img') as mock_cache:
        mock_cache.side_effect = [img1, img2]
        with patch.object(aligner.feature_matcher, 'match_images_with_fallback') as mock_match:
            mock_kp_0 = []
            mock_kp_ref = []
            mock_good_matches = []
            for i in range(10):
                kp_0 = Mock()
                kp_0.pt = (float(i * 10), float(i * 10))
                mock_kp_0.append(kp_0)
                kp_ref = Mock()
                kp_ref.pt = (float(i * 10 + 5), float(i * 10 + 5))
                mock_kp_ref.append(kp_ref)
                match = Mock()
                match.queryIdx = i
                match.trainIdx = i
                mock_good_matches.append(match)
            mock_match_result = Mock()
            mock_match_result.kp_0 = mock_kp_0
            mock_match_result.kp_ref = mock_kp_ref
            mock_match_result.good_matches = mock_good_matches
            mock_match_result.has_sufficient_matches.return_value = len(mock_good_matches) >= 4
            mock_match_result.get_src_points.return_value = np.float32(
                [kp.pt for kp in mock_kp_0]).reshape(-1, 1, 2)
            mock_match_result.get_dst_points.return_value = np.float32(
                [kp.pt for kp in mock_kp_ref]).reshape(-1, 1, 2)
            mock_match_result.img_0_sub = None
            mock_match_result.img_ref_sub = None
            mock_match_result.subsample = None
            mock_match.return_value = (mock_match_result, 1)
            aligner.feature_matcher._last_subsampled_images = (img1, img2)
            with patch.object(
                    aligner.transformation_extractor, 'extract_transformation') as mock_extract:
                mock_extract.return_value = (
                    np.eye(2, 3, dtype=np.float32),  # m
                    False,  # phase_corr_called
                    None,   # msk
                    None,   # quality
                )
                info, warnings = aligner.find_transform(1, delta=1)
                assert aligner._transforms[1] is not None
                assert aligner._target_indices[1] == 0


def test_find_transform_max_delta_reached():
    aligner = AlignFramesParallel(alignment_config={
        'transform': constants.ALIGN_RIGID,
        'subsample': 1,
        'fast_subsampling': False,
        'min_good_matches': 4,
        'phase_corr_fallback': False,
        'abort_abnormal': False
    })
    aligner.delta_max = 1
    process = Mock()
    process.ref_idx = 2
    process.idx_tot_str = Mock(return_value="1/3")
    process.input_filepath = Mock(side_effect=lambda idx: f"img{idx}.jpg")
    aligner.process = process
    aligner.print_message = Mock()
    aligner._n_good_matches = [0, 0, 0]
    aligner._target_indices = [None, None, None]
    aligner._transforms = [None, None, None]
    with patch.object(aligner, 'cache_img') as mock_cache:
        with patch.object(aligner.feature_matcher, 'match_images_with_fallback') as mock_match:
            mock_kp_0 = [Mock(pt=(10.0, 10.0))]
            mock_kp_ref = [Mock(pt=(15.0, 15.0))]
            mock_matches = [Mock(queryIdx=0, trainIdx=0)]
            mock_match_result = Mock()
            mock_match_result.kp_0 = mock_kp_0
            mock_match_result.kp_ref = mock_kp_ref
            mock_match_result.good_matches = mock_matches
            mock_match_result.n_good_matches.return_value = len(mock_matches)
            mock_match_result.has_sufficient_matches.return_value = len(mock_matches) >= 4
            mock_match_result.get_src_points.return_value = np.float32(
                [kp.pt for kp in mock_kp_0]).reshape(-1, 1, 2)
            mock_match_result.get_dst_points.return_value = np.float32(
                [kp.pt for kp in mock_kp_ref]).reshape(-1, 1, 2)
            mock_match.return_value = (mock_match_result, 1)
            mock_cache.return_value = np.ones((100, 100, 3), dtype=np.uint8)
            info, warnings = aligner.find_transform(1, delta=1)
            assert len(warnings) > 0
            assert "frame skipped" in warnings[0].lower()


def test_find_transform_phase_correlation_fallback():
    aligner = AlignFramesParallel(alignment_config={
        'transform': constants.ALIGN_RIGID,
        'subsample': 1,
        'fast_subsampling': False,
        'min_good_matches': 4,
        'phase_corr_fallback': True,
        'abort_abnormal': False
    })
    process = Mock()
    process.ref_idx = 0
    process.idx_tot_str = Mock(return_value="1/2")
    process.input_filepath = Mock(side_effect=lambda idx: f"img{idx}.jpg")
    aligner.process = process
    aligner.print_message = Mock()
    aligner._n_good_matches = [0, 0]
    aligner._target_indices = [None, None]
    aligner._transforms = [None, None]
    aligner._img_shapes = [(100, 100, 3)] * 2
    with patch.object(aligner, 'cache_img') as mock_cache:
        with patch.object(aligner.feature_matcher, 'match_images_with_fallback') as mock_match:
            with patch.object(
                    aligner.transformation_extractor, 'extract_transformation') as mock_extract:
                mock_match_result = Mock()
                mock_match_result.n_good_matches.return_value = 1
                mock_match.return_value = (mock_match_result, 1)
                aligner.feature_matcher._last_subsampled_images = (
                    np.ones((100, 100, 3), dtype=np.uint8),
                    np.ones((100, 100, 3), dtype=np.uint8)
                )
                mock_cache.return_value = np.ones((100, 100, 3), dtype=np.uint8)
                mock_extract.return_value = (
                    np.eye(2, 3, dtype=np.float32),
                    True,
                    None,
                    None
                )
                info, warnings = aligner.find_transform(1, delta=1)
                assert aligner._transforms[1] is not None
                assert aligner._target_indices[1] == 0
                assert aligner._n_good_matches[1] == 1


def test_find_transform_invalid_transform_abort():
    aligner = AlignFramesParallel(alignment_config={
        'transform': constants.ALIGN_RIGID,
        'subsample': 1,
        'fast_subsampling': False,
        'min_good_matches': 4,
        'align_method': 'RANSAC',
        'rans_threshold': 3.0,
        'max_iters': 2000,
        'align_confidence': 0.99,
        'refine_iters': 10,
        'phase_corr_fallback': False,
        'abort_abnormal': True
    })
    process = Mock()
    process.ref_idx = 0
    process.idx_tot_str = Mock(return_value="1/2")
    process.input_filepath = Mock(side_effect=lambda idx: f"img{idx}.jpg")
    aligner.process = process
    aligner.print_message = Mock()
    aligner.get_transform_thresholds = Mock(return_value=(100, 0.5))
    aligner._n_good_matches = [0, 0]
    aligner._target_indices = [None, None]
    aligner._transforms = [None, None]
    aligner._img_shapes = [(100, 100, 3)] * 2
    with patch.object(aligner, 'cache_img') as mock_cache:
        with patch.object(aligner.feature_matcher, 'match_images_with_fallback') as mock_match:
            with patch.object(
                    aligner.transformation_extractor, 'extract_transformation') as mock_extract:
                mock_kp_0 = [Mock(pt=(i * 10.0, i * 10.0)) for i in range(10)]
                mock_kp_ref = [Mock(pt=(i * 10.0 + 5, i * 10.0 + 5)) for i in range(10)]
                mock_matches = [Mock(queryIdx=i, trainIdx=i) for i in range(10)]
                mock_match_result = Mock()
                mock_match_result.kp_0 = mock_kp_0
                mock_match_result.kp_ref = mock_kp_ref
                mock_match_result.good_matches = mock_matches
                mock_match_result.n_good_matches.return_value = len(mock_matches)
                mock_match_result.img_0_sub = None
                mock_match_result.img_ref_sub = None
                mock_match_result.subsample = None
                mock_match.return_value = (mock_match_result, 1)
                test_img = np.ones((100, 100, 3), dtype=np.uint8)
                aligner.feature_matcher._last_subsampled_images = (test_img, test_img)
                mock_cache.return_value = test_img
                mock_extract.side_effect = RuntimeError(
                    "invalid transformation: test invalid reason")
                with pytest.raises(RuntimeError, match="invalid transformation"):
                    aligner.find_transform(1, delta=1)


def test_find_transform_rescale_failure():
    aligner = AlignFramesParallel(alignment_config={
        'transform': constants.ALIGN_RIGID,
        'subsample': 2,
        'fast_subsampling': False,
        'min_good_matches': 4,
        'align_method': 'RANSAC',
        'rans_threshold': 3.0,
        'max_iters': 2000,
        'align_confidence': 0.99,
        'refine_iters': 10,
        'phase_corr_fallback': False,
        'abort_abnormal': False
    })
    process = Mock()
    process.ref_idx = 0
    process.idx_tot_str = Mock(return_value="1/2")
    process.input_filepath = Mock(side_effect=lambda idx: f"img{idx}.jpg")
    aligner.process = process
    aligner.print_message = Mock()
    aligner._n_good_matches = [0, 0]
    aligner._target_indices = [None, None]
    aligner._transforms = [None, None]
    aligner._img_shapes = [(100, 100, 3)] * 2
    with patch.object(aligner, 'find_transform') as mock_recursive:
        with patch.object(aligner, 'cache_img') as mock_cache:
            with patch.object(aligner.feature_matcher, 'match_images_with_fallback') as mock_match:
                with patch.object(
                        aligner.transformation_extractor, 'extract_transformation') as mock_extract:
                    mock_match_result = Mock()
                    mock_match_result.n_good_matches.return_value = 10
                    mock_match.return_value = (mock_match_result, 2)
                    aligner.feature_matcher._last_subsampled_images = (
                        np.ones((50, 50, 3), dtype=np.uint8),
                        np.ones((50, 50, 3), dtype=np.uint8)
                    )
                    mock_cache.return_value = np.ones((100, 100, 3), dtype=np.uint8)
                    mock_extract.return_value = (10, None, False, None)
                    mock_recursive.return_value = ([], ["recursive call"])
                    info, warnings = aligner.find_transform(1, delta=1)
                    assert len(warnings) > 0
                    assert aligner._transforms[1] is None


if __name__ == '__main__':
    test_compose_transforms()
    test_align_frames_parallel_initialization()
    test_cache_img()
    test_align_images_method()
    test_align_images_border_modes()
    test_extract_features_fallback()
    test_submit_threads()
    test_submit_threads_with_exceptions()
    test_begin_initialization()
    test_begin_transform_combination()
    test_find_transform_successful()
    test_find_transform_max_delta_reached()
    test_find_transform_phase_correlation_fallback()
    test_find_transform_invalid_transform_abort()


def test_frame_status_name_matches_output_file():
    # status boxes are keyed by output file name; RAW inputs are written as .tif
    assert AlignFramesParallel.frame_status_name("/in/DSC00196.ARW") == "DSC00196.tif"
    assert AlignFramesParallel.frame_status_name("/in/img.JPG") == "img.jpg"
    assert AlignFramesParallel.frame_status_name("/in/img.tif") == "img.tif"
