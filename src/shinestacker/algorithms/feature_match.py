# pylint: disable=C0114, C0115, C0116, R0913, R0903, E1101, W0718, R0914, R0917
import numpy as np
import cv2
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. core.exceptions import InvalidOptionError
from .utils import img_bw_8bit, img_subsample

DEFAULT_FEATURE_CONFIG = {
    'detector': DEFAULTS['align_frames_params']['detector'],
    'descriptor': DEFAULTS['align_frames_params']['descriptor']
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
    'align_confidence': DEFAULTS['align_frames_params']['align_confidence'],
    'max_iters': DEFAULTS['align_frames_params']['max_iters'],
    'border_mode': DEFAULTS['align_frames_params']['border_mode'],
    'border_value': DEFAULTS['align_frames_params']['border_value'],
    'border_blur': DEFAULTS['align_frames_params']['border_blur'],
    'interpolation': DEFAULTS['align_frames_params']['interpolation'],
    'subsample': DEFAULTS['align_frames_params']['subsample'],
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


class FeatureMatcher:
    def __init__(self, feature_config, matching_config, callbacks=None):
        self.feature_config = {**DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
        self.matching_config = {**DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
        self.callbacks = callbacks or {}
        detector = self.feature_config['detector']
        descriptor = self.feature_config['descriptor']
        match_method = self.matching_config['match_method']
        validate_align_config(detector, descriptor, match_method)
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

    def detect_and_compute(self, image):
        img_bw = img_bw_8bit(image)
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
        return kp, des

    def match_images(self, img_ref, img_0):
        kp_0, des_0 = self.detect_and_compute(img_0)
        kp_ref, des_ref = self.detect_and_compute(img_ref)
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

    def match_images_with_fallback(self, img_ref, img_0, subsample=1, warning_callback=None):
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
            match_result = self.feature_matcher.match_images(img_ref_sub, img_0_sub)
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
