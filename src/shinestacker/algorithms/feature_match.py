# pylint: disable=R0913, R0903, W0718, R0914, R0917, R0902
import logging
import threading
import numpy as np
import cv2
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. core.exceptions import InvalidOptionError
from .utils import img_bw_8bit, img_subsample
from . import silx_sift

DEFAULT_FEATURE_CONFIG = {
    'detector': DEFAULTS['align_frames_params']['detector'],
    'descriptor': DEFAULTS['align_frames_params']['descriptor'],
    'sift_backend': DEFAULTS['align_frames_params']['sift_backend']
}

DEFAULT_MATCHING_CONFIG = {
    'match_method': DEFAULTS['align_frames_params']['match_method'],
    'flann_idx_kdtree': DEFAULTS['align_frames_params']['flann_idx_kdtree'],
    'flann_trees': DEFAULTS['align_frames_params']['flann_trees'],
    'flann_checks': DEFAULTS['align_frames_params']['flann_checks'],
    'threshold': DEFAULTS['align_frames_params']['threshold'],
}

DEFAULT_ALIGNMENT_CONFIG = {
    'transform': DEFAULTS['align_frames_params']['transform'],
    'align_method': DEFAULTS['align_frames_params']['align_method'],
    'rans_threshold': DEFAULTS['align_frames_params']['rans_threshold'],
    'refine_iters': DEFAULTS['align_frames_params']['refine_iters'],
    'refit': DEFAULTS['align_frames_params']['refit'],
    'refit_threshold': DEFAULTS['align_frames_params']['refit_threshold'],
    'align_confidence': DEFAULTS['align_frames_params']['align_confidence'],
    'max_iters': DEFAULTS['align_frames_params']['max_iters'],
    'border_mode': DEFAULTS['align_frames_params']['border_mode'],
    'border_value': DEFAULTS['align_frames_params']['border_value'],
    'border_blur': DEFAULTS['align_frames_params']['border_blur'],
    'interpolation': DEFAULTS['align_frames_params']['interpolation'],
    'subsample': DEFAULTS['align_frames_params']['subsample'],
    'resolution_target': DEFAULTS['align_frames_params']['resolution_target'],
    'fast_subsampling': DEFAULTS['align_frames_params']['fast_subsampling'],
    'min_good_matches': DEFAULTS['align_frames_params']['min_good_matches'],
    'phase_corr_fallback': DEFAULTS['align_frames_params']['phase_corr_fallback'],
    'abort_abnormal': DEFAULTS['align_frames_params']['abort_abnormal'],
    'compute_rans_quality': DEFAULTS['align_frames_params']['compute_rans_quality'],
    'rans_inlier_fraction_threshold':
        DEFAULTS['align_frames_params']['rans_inlier_fraction_threshold'],
    'rans_avg_error_threshold': DEFAULTS['align_frames_params']['rans_avg_error_threshold'],
    'rans_max_error_threshold': DEFAULTS['align_frames_params']['rans_max_error_threshold'],
}


class MatchResult:
    def __init__(self, kp_0, kp_ref, good_matches):
        self.kp_0 = kp_0
        self.kp_ref = kp_ref
        self.good_matches = good_matches

    def n_good_matches(self):
        return len(self.good_matches)

    def has_sufficient_matches(self, min_matches):
        return self.n_good_matches() >= min_matches

    def get_src_points(self):
        return np.float32(
            [self.kp_0[match.queryIdx].pt for match in self.good_matches]
        ).reshape(-1, 1, 2)

    def get_dst_points(self):
        return np.float32(
            [self.kp_ref[match.trainIdx].pt for match in self.good_matches]
        ).reshape(-1, 1, 2)


def validate_align_config(detector, descriptor, match_method):
    if descriptor == constants.DESCRIPTOR_SIFT and match_method == constants.MATCHING_NORM_HAMMING:
        raise ValueError("Descriptor SIFT requires matching method KNN")
    if detector == constants.DETECTOR_ORB and descriptor == constants.DESCRIPTOR_AKAZE and \
            match_method == constants.MATCHING_NORM_HAMMING:
        raise ValueError("Detector ORB and descriptor AKAZE require matching method KNN")
    if detector == constants.DETECTOR_BRISK and descriptor == constants.DESCRIPTOR_AKAZE:
        raise ValueError("Detector BRISK is incompatible with descriptor AKAZE")
    if detector == constants.DETECTOR_SURF and descriptor == constants.DESCRIPTOR_AKAZE:
        raise ValueError("Detector SURF is incompatible with descriptor AKAZE")
    if detector == constants.DETECTOR_SIFT and descriptor != constants.DESCRIPTOR_SIFT:
        raise ValueError("Detector SIFT requires descriptor SIFT")
    if detector in constants.NOKNN_METHODS['detectors'] and \
       descriptor in constants.NOKNN_METHODS['descriptors'] and \
       match_method != constants.MATCHING_NORM_HAMMING:
        raise ValueError(f"Detector {detector} and descriptor {descriptor}"
                         " require matching method Hamming distance")


class FeatureCache:
    """Keypoints and descriptors by key. Each is computed once, also when several threads ask
    for the same key at the same time (the frames of a chain are matched in pairs, so each
    frame is needed twice).

    The key is (frame, subsample) only: a cache belongs to one FeatureMatcher, with one fixed
    detector and descriptor, for one run (a matcher with another configuration, such as the
    fallback detector, needs its own cache or a configuration in the key). The cached keypoints
    and descriptors are shared by the matches and must not be modified.

    drop() and clear() do not wait for computations in progress, and a computation that finishes
    after them stores its result: call them only when no thread uses the frame (drop) or the
    cache (clear) any more.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._items = {}
        self._key_locks = {}

    def get_or_compute(self, key, compute):
        with self._lock:
            if key in self._items:
                return self._items[key]
            key_lock = self._key_locks.setdefault(key, threading.Lock())
        with key_lock:
            with self._lock:
                if key in self._items:
                    return self._items[key]
            result = compute()
            with self._lock:
                self._items[key] = result
            return result

    def put(self, key, result):
        """Replace the entry of a key."""
        with self._lock:
            self._items[key] = result

    def drop(self, frame):
        """Forget all entries of a frame; keys are (frame, subsample)."""
        with self._lock:
            for key in [k for k in self._items if k[0] == frame]:
                del self._items[key]
                self._key_locks.pop(key, None)

    def clear(self):
        with self._lock:
            self._items.clear()
            self._key_locks.clear()


class FeatureMatcher:
    def __init__(self, feature_config, matching_config, callbacks=None):
        self.cache = None       # a FeatureCache that only this matcher uses, set by the caller
        self.feature_config = {**DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
        self.matching_config = {**DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
        self.callbacks = callbacks or {}
        detector = self.feature_config['detector']
        descriptor = self.feature_config['descriptor']
        match_method = self.matching_config['match_method']
        validate_align_config(detector, descriptor, match_method)
        self._lock = threading.Lock()
        self._pending_warning = None
        self._silx_sift = self._select_silx_sift(detector, descriptor)
        self._silx_plans = silx_sift.SiftPlans() if self._silx_sift else None
        self.detector = {
            constants.DETECTOR_SIFT: cv2.SIFT_create,
            constants.DETECTOR_ORB: cv2.ORB_create,
            constants.DETECTOR_SURF: cv2.FastFeatureDetector_create,
            constants.DETECTOR_AKAZE: cv2.AKAZE_create,
            constants.DETECTOR_BRISK: cv2.BRISK_create
        }[detector]()
        if detector == descriptor and detector in (
            constants.DETECTOR_SIFT, constants.DETECTOR_AKAZE, constants.DETECTOR_BRISK
        ):
            self.descriptor = self.detector
        else:
            self.descriptor = {
                constants.DESCRIPTOR_SIFT: cv2.SIFT_create,
                constants.DESCRIPTOR_ORB: cv2.ORB_create,
                constants.DESCRIPTOR_AKAZE: cv2.AKAZE_create,
                constants.DETECTOR_BRISK: cv2.BRISK_create
            }[descriptor]()

    def _select_silx_sift(self, detector, descriptor):
        backend = self.feature_config['sift_backend']
        if backend not in constants.VALID_SIFT_BACKENDS:
            raise InvalidOptionError(
                'sift_backend', backend,
                f". Valid options are: {', '.join(constants.VALID_SIFT_BACKENDS)}")
        if backend == constants.SIFT_BACKEND_OPENCV or \
                (detector, descriptor) != (constants.DETECTOR_SIFT, constants.DESCRIPTOR_SIFT):
            return False
        usable = silx_sift.silx_sift_usable()
        if not usable:
            # issued on first use: the align actions build their matcher before they can log
            self._pending_warning = "silx SIFT requested but silx/pyopencl or an OpenCL" \
                                    " device is not available, using OpenCV SIFT"
        return usable

    def _warning(self, msg, warning_callback=None):
        callback = warning_callback or self.callbacks.get('warning')
        if callback:
            callback(msg)
        else:
            logging.getLogger(__name__).warning(msg)

    def release_resources(self):
        if self._silx_plans is not None:
            self._silx_plans.release()

    def sift_implementation(self):
        """The SIFT implementation in use, for the log; None for other detectors."""
        if (self.feature_config['detector'], self.feature_config['descriptor']) != \
                (constants.DETECTOR_SIFT, constants.DESCRIPTOR_SIFT):
            return None
        if not self._silx_sift:
            return "SIFT (OpenCV)"
        try:
            return f"SIFT (silx, OpenCL: {silx_sift.device_name()})"
        except Exception:
            return "SIFT (silx, OpenCL)"

    def detect_and_compute(self, image, key=None, warning_callback=None):
        """key: (frame, subsample) of the image; with a cache set, the features of a key are
        computed once."""
        kp, des, _silx = self._features(image, key, warning_callback)
        return kp, des

    def _features(self, image, key, warning_callback=None):
        # (kp, des, computed with silx)
        if key is None or self.cache is None:
            return self._detect_and_compute(image, warning_callback)
        return self.cache.get_or_compute(
            key, lambda: self._shared(self._detect_and_compute(image, warning_callback)))

    def _opencv_features(self, image, key):
        """OpenCV features of an image whose features came from silx before silx failed."""
        result = self._detect_and_compute(image, allow_silx=False)
        if key is None or self.cache is None:
            return result
        result = self._shared(result)
        self.cache.put(key, result)
        return result

    @staticmethod
    def _shared(result):
        """Features that several matches use: the descriptors are read-only."""
        if result[1] is not None:
            result[1].setflags(write=False)
        return result

    def _detect_and_compute(self, image, warning_callback=None, allow_silx=True):
        # also returns whether silx computed the features
        img_bw = img_bw_8bit(image)
        with self._lock:
            msg, self._pending_warning = self._pending_warning, None
        if msg:
            self._warning(msg, warning_callback)
        if allow_silx and self._silx_sift:
            try:
                return (*self._silx_plans.detect_and_compute(img_bw), True)
            except Exception as e:
                with self._lock:
                    first_failure, self._silx_sift = self._silx_sift, False
                if first_failure:
                    self._warning(f"silx SIFT failed ({e}), using OpenCV SIFT",
                                  warning_callback)
        detector_name = self.feature_config['detector']
        descriptor_name = self.feature_config['descriptor']
        if (detector_name == descriptor_name and detector_name in
                (constants.DETECTOR_SIFT, constants.DETECTOR_AKAZE, constants.DETECTOR_BRISK)):
            kp, des = self.detector.detectAndCompute(img_bw, None)
        else:
            kp = self.detector.detect(img_bw, None)
            if kp:
                kp, des = self.descriptor.compute(img_bw, kp)
            else:
                des = None
        return kp, des, False

    def match_images(self, img_ref, img_0, keys=(None, None), warning_callback=None):
        kp_0, des_0, silx_0 = self._features(img_0, keys[1], warning_callback)
        kp_ref, des_ref, silx_ref = self._features(img_ref, keys[0], warning_callback)
        # silx failed in between (possibly in another thread, or after the features of a
        # cached frame): do not match silx features against OpenCV ones
        if silx_0 and not silx_ref:
            kp_0, des_0, _silx = self._opencv_features(img_0, keys[1])
        elif silx_ref and not silx_0:
            kp_ref, des_ref, _silx = self._opencv_features(img_ref, keys[0])
        if des_0 is None or des_ref is None or len(des_0) == 0 or len(des_ref) == 0:
            return MatchResult(kp_0, kp_ref, [])
        good_matches = self.match_features(des_0, des_ref)
        return MatchResult(kp_0, kp_ref, good_matches)

    def match_features(self, des_0, des_ref):
        matching_config = {**DEFAULT_MATCHING_CONFIG, **(self.matching_config or {})}
        match_method = matching_config['match_method']
        good_matches = []
        invalid_option = False
        try:
            if match_method == constants.MATCHING_KNN:
                flann = cv2.FlannBasedMatcher(
                    {'algorithm': matching_config['flann_idx_kdtree'],
                     'trees': matching_config['flann_trees']},
                    {'checks': matching_config['flann_checks']})
                matches = flann.knnMatch(des_0, des_ref, k=2)
                good_matches = [m for m, n in matches
                                if m.distance < matching_config['threshold'] * n.distance]
            elif match_method == constants.MATCHING_NORM_HAMMING:
                bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                good_matches = sorted(bf.match(des_0, des_ref), key=lambda x: x.distance)
            else:
                invalid_option = True
        except Exception:
            if self.callbacks and 'warning' in self.callbacks:
                self.callbacks['warning']("failed to compute matches")
        if invalid_option:
            raise InvalidOptionError(
                'match_method', match_method,
                f". Valid options are: {constants.MATCHING_KNN}, {constants.MATCHING_NORM_HAMMING}"
            )
        return good_matches


class SubsamplingFeatureMatcher:
    def __init__(self, feature_config, matching_config, alignment_config, callbacks=None):
        self.feature_matcher = FeatureMatcher(feature_config, matching_config, callbacks)
        self.alignment_config = alignment_config
        self.callbacks = callbacks or {}
        self._last_subsampled_images = (None, None)

    def match_images_with_fallback(self, img_ref, img_0, subsample=1, warning_callback=None,
                                   frame_keys=None):
        """frame_keys: the frame numbers (ref, img_0), if the matcher has a feature cache."""
        final_subsample = subsample
        min_good_matches = self.alignment_config['min_good_matches']
        fast_subsampling = self.alignment_config['fast_subsampling']
        while True:
            if final_subsample > 1:
                img_0_sub = img_subsample(img_0, final_subsample, fast_subsampling)
                img_ref_sub = img_subsample(img_ref, final_subsample, fast_subsampling)
            else:
                img_0_sub, img_ref_sub = img_0, img_ref
            self._last_subsampled_images = (img_ref_sub, img_0_sub)
            keys = (None, None) if frame_keys is None else \
                ((frame_keys[0], final_subsample), (frame_keys[1], final_subsample))
            match_result = self.feature_matcher.match_images(
                img_ref_sub, img_0_sub, keys, warning_callback)
            n_good_matches = match_result.n_good_matches()
            if n_good_matches >= min_good_matches or final_subsample == 1:
                break
            final_subsample = 1
            if warning_callback:
                s_str = 'es' if n_good_matches != 1 else ''
                warning_callback(
                    f"only {n_good_matches} < {min_good_matches} "
                    f"match{s_str} found, retrying without subsampling")
        return match_result, final_subsample

    def get_last_subsampled_images(self):
        return self._last_subsampled_images

    def release_resources(self):
        self.feature_matcher.release_resources()

    def sift_implementation(self):
        return self.feature_matcher.sift_implementation()
