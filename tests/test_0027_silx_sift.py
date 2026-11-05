import gc
import threading
import weakref
import logging
import numpy as np
import cv2
import pytest
from shinestacker.config.constants import constants
from shinestacker.core.exceptions import InvalidOptionError
from shinestacker.algorithms import silx_sift
from shinestacker.algorithms.feature_match import (
    FeatureCache, FeatureMatcher, SubsamplingFeatureMatcher, DEFAULT_ALIGNMENT_CONFIG)

SIFT = {'detector': constants.DETECTOR_SIFT, 'descriptor': constants.DESCRIPTOR_SIFT}
KNN = {'match_method': constants.MATCHING_KNN}
needs_opencl = pytest.mark.skipif(
    not silx_sift.silx_sift_usable(), reason="silx, pyopencl or an OpenCL device not available")


def _test_image(size=(480, 640)):
    rng = np.random.default_rng(42)
    img = cv2.GaussianBlur(rng.integers(0, 256, size, dtype=np.uint8), (0, 0), 3)
    return cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)


def test_default_backend_is_opencv():
    matcher = FeatureMatcher(SIFT, KNN)
    assert matcher.feature_config['sift_backend'] == constants.SIFT_BACKEND_OPENCV
    assert not matcher._silx_sift


def test_invalid_backend():
    with pytest.raises(InvalidOptionError):
        FeatureMatcher({**SIFT, 'sift_backend': 'cuda'}, KNN)


def test_backend_ignored_for_other_detectors():
    matcher = FeatureMatcher({'detector': constants.DETECTOR_ORB,
                              'descriptor': constants.DESCRIPTOR_ORB,
                              'sift_backend': constants.SIFT_BACKEND_SILX},
                             {'match_method': constants.MATCHING_NORM_HAMMING})
    assert not matcher._silx_sift


def test_silx_unavailable_falls_back(monkeypatch):
    monkeypatch.setattr(silx_sift, 'silx_sift_usable', lambda: False)
    warnings = []
    matcher = FeatureMatcher({**SIFT, 'sift_backend': constants.SIFT_BACKEND_SILX}, KNN,
                             callbacks={'warning': warnings.append})
    assert not matcher._silx_sift
    assert not warnings
    kp, des = matcher.detect_and_compute(_test_image())
    assert len(kp) > 0 and des.shape == (len(kp), 128)
    matcher.detect_and_compute(_test_image())
    assert len(warnings) == 1


def test_silx_unavailable_warns_through_alignment_callback(monkeypatch):
    # the align actions build their matcher without callbacks and pass a warning callback
    monkeypatch.setattr(silx_sift, 'silx_sift_usable', lambda: False)
    warnings = []
    matcher = SubsamplingFeatureMatcher({**SIFT, 'sift_backend': constants.SIFT_BACKEND_SILX},
                                        KNN, DEFAULT_ALIGNMENT_CONFIG)
    img = _test_image()
    matcher.match_images_with_fallback(img, img, warning_callback=warnings.append)
    assert len(warnings) == 1 and 'silx' in warnings[0]


def test_silx_unavailable_warns_to_log_without_callback(monkeypatch, caplog):
    monkeypatch.setattr(silx_sift, 'silx_sift_usable', lambda: False)
    matcher = FeatureMatcher({**SIFT, 'sift_backend': constants.SIFT_BACKEND_SILX}, KNN)
    with caplog.at_level(logging.WARNING):
        matcher.detect_and_compute(_test_image())
    assert any('silx' in r.getMessage() for r in caplog.records)


def _silx_matcher(monkeypatch, fake_silx, **kwargs):
    monkeypatch.setattr(silx_sift, 'silx_sift_usable', lambda: True)
    monkeypatch.setattr(silx_sift.SiftPlans, 'detect_and_compute', fake_silx)
    return FeatureMatcher({**SIFT, 'sift_backend': constants.SIFT_BACKEND_SILX}, KNN, **kwargs)


def test_silx_failure_falls_back(monkeypatch):
    def fail(_self, _img):
        raise RuntimeError("out of device memory")
    warnings = []
    matcher = _silx_matcher(monkeypatch, fail, callbacks={'warning': warnings.append})
    assert matcher._silx_sift
    kp, _des = matcher.detect_and_compute(_test_image())
    assert len(kp) > 0
    assert not matcher._silx_sift
    assert len(warnings) == 1


def test_silx_failure_within_pair_recomputes_first_image(monkeypatch):
    calls = []

    def fail_second(_self, _img):
        calls.append(1)
        if len(calls) > 1:
            raise RuntimeError("out of device memory")
        return [], None
    matcher = _silx_matcher(monkeypatch, fail_second)
    img = _test_image()
    result = matcher.match_images(img, img)
    # the first image is not left with the (empty) silx result
    assert len(result.kp_0) > 0 and result.n_good_matches() > 0


def test_silx_failure_in_other_thread_does_not_mix_backends(monkeypatch):
    # thread A extracts its first image with silx; before A goes on, silx fails in thread B
    a_extracted, b_failed = threading.Event(), threading.Event()

    def fake_silx(_self, _img):
        if threading.current_thread().name == 'B':
            raise RuntimeError("out of device memory")
        if not a_extracted.is_set():
            a_extracted.set()
            b_failed.wait(10)
        return [], None
    matcher = _silx_matcher(monkeypatch, fake_silx)
    img = _test_image()
    results = []
    thread_a = threading.Thread(
        target=lambda: results.append(matcher.match_images(img, img)), name='A')
    thread_a.start()
    assert a_extracted.wait(10)
    thread_b = threading.Thread(target=matcher.detect_and_compute, args=(img,), name='B')
    thread_b.start()
    thread_b.join()
    b_failed.set()
    thread_a.join(10)
    assert not matcher._silx_sift
    # A's silx result of the first image was recomputed with OpenCV, not matched as it is
    assert len(results[0].kp_0) > 0 and results[0].n_good_matches() > 0


def test_silx_failure_replaces_cached_silx_features(monkeypatch):
    # frame 1 is cached from the pair (0, 1) with silx; silx fails before the pair (1, 2)
    calls = []

    def fail_third(_self, _img):
        calls.append(1)
        if len(calls) > 2:
            raise RuntimeError("out of device memory")
        return [], None
    matcher = _silx_matcher(monkeypatch, fail_third)
    matcher.cache = FeatureCache()
    img = _test_image()
    matcher.match_images(img, img, keys=((0, 1), (1, 1)))
    result = matcher.match_images(img, img, keys=((1, 1), (2, 1)))
    assert not matcher._silx_sift
    # the cached silx features of frame 1 were recomputed with OpenCV and replace the entry
    assert len(result.kp_ref) > 0 and result.n_good_matches() > 0
    kp, des, silx = matcher.cache._items[(1, 1)]
    assert len(kp) > 0 and not silx and not des.flags.writeable


class _FakePlan:
    pass


def test_release_drops_the_last_plan_reference(monkeypatch):
    monkeypatch.setattr(silx_sift, 'silx_sift_usable', lambda: True)
    matcher = SubsamplingFeatureMatcher(
        {**SIFT, 'sift_backend': constants.SIFT_BACKEND_SILX}, KNN, DEFAULT_ALIGNMENT_CONFIG)
    plan = _FakePlan()
    ref = weakref.ref(plan)
    matcher.feature_matcher._silx_plans._plans[(4, 4)] = plan
    del plan
    matcher.release_resources()
    assert ref() is None


def test_plans_freed_with_their_matcher(monkeypatch):
    # a stopped run skips end(): the plans go with the action that owns the matcher
    monkeypatch.setattr(silx_sift, 'silx_sift_usable', lambda: True)
    matcher = FeatureMatcher({**SIFT, 'sift_backend': constants.SIFT_BACKEND_SILX}, KNN)
    plan = _FakePlan()
    ref = weakref.ref(plan)
    matcher._silx_plans._plans[(4, 4)] = plan
    del plan, matcher
    gc.collect()
    assert ref() is None


@needs_opencl
def test_release_plans():
    plans = silx_sift.SiftPlans()
    plans.detect_and_compute(_test_image())
    ref = weakref.ref(plans._get_plan(_test_image().shape))
    plans.release()
    gc.collect()
    assert ref() is None
    assert len(plans.detect_and_compute(_test_image())[0]) > 0


@needs_opencl
def test_silx_output_format():
    kp, des = silx_sift.SiftPlans().detect_and_compute(_test_image())
    assert len(kp) > 0
    assert all(isinstance(k, cv2.KeyPoint) for k in kp)
    assert des.dtype == np.float32 and des.shape == (len(kp), 128)


@needs_opencl
def test_silx_matches_translation():
    img = _test_image((600, 800))
    shifted = np.roll(img, (7, -12), axis=(0, 1))
    matcher = FeatureMatcher({**SIFT, 'sift_backend': constants.SIFT_BACKEND_SILX}, KNN)
    assert matcher._silx_sift
    result = matcher.match_images(img, shifted)
    # fails if silx broke and OpenCV did the work
    assert matcher._silx_sift
    assert result.n_good_matches() > 20
    # points of the shifted image minus points of the reference give the shift
    shift = np.median(result.get_src_points() - result.get_dst_points(), axis=0).ravel()
    assert np.allclose(shift, [-12, 7], atol=0.5)


def test_sift_implementation_for_the_log(monkeypatch):
    assert FeatureMatcher(SIFT, KNN).sift_implementation() == "SIFT (OpenCV)"
    assert FeatureMatcher({'detector': constants.DETECTOR_ORB,
                           'descriptor': constants.DESCRIPTOR_ORB},
                          {'match_method': constants.MATCHING_NORM_HAMMING}
                          ).sift_implementation() is None
    silx_config = {**SIFT, 'sift_backend': constants.SIFT_BACKEND_SILX}
    monkeypatch.setattr(silx_sift, 'silx_sift_usable', lambda: False)
    assert FeatureMatcher(silx_config, KNN).sift_implementation() == "SIFT (OpenCV)"
    monkeypatch.setattr(silx_sift, 'silx_sift_usable', lambda: True)
    monkeypatch.setattr(silx_sift, 'device_name', lambda: "Test GPU")
    assert FeatureMatcher(silx_config, KNN).sift_implementation() == \
        "SIFT (silx, OpenCL: Test GPU)"

    def no_device():
        raise RuntimeError("no context")
    monkeypatch.setattr(silx_sift, 'device_name', no_device)
    assert FeatureMatcher(silx_config, KNN).sift_implementation() == "SIFT (silx, OpenCL)"


@needs_opencl
def test_device_name_is_the_plan_device():
    plans = silx_sift.SiftPlans()
    plan = plans._get_plan(_test_image().shape)
    assert silx_sift.device_name() == plan.ctx.devices[0].name.strip()
