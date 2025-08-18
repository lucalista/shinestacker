# pylint: disable=C0114, C0115, C0116, E1101, R0914, R0913, R0917, R0912, R0915, R0902
import logging
import numpy as np
import matplotlib.pyplot as plt
import cv2
from .. config.constants import constants
from .. core.exceptions import AlignmentError, InvalidOptionError
from .. core.colors import color_str
from .utils import img_8bit, img_bw_8bit, save_plot
from .utils import get_img_metadata, validate_image
from .stack_framework import SubAction

_DEFAULT_FEATURE_CONFIG = {
    'detector': constants.DEFAULT_DETECTOR,
    'descriptor': constants.DEFAULT_DESCRIPTOR
}

_DEFAULT_MATCHING_CONFIG = {
    'match_method': constants.DEFAULT_MATCHING_METHOD,
    'flann_idx_kdtree': constants.DEFAULT_FLANN_IDX_KDTREE,
    'flann_trees': constants.DEFAULT_FLANN_TREES,
    'flann_checks': constants.DEFAULT_FLANN_CHECKS,
    'threshold': constants.DEFAULT_ALIGN_THRESHOLD
}

_DEFAULT_ALIGNMENT_CONFIG = {
    'transform': constants.DEFAULT_TRANSFORM,
    'align_method': constants.DEFAULT_ALIGN_METHOD,
    'rans_threshold': constants.DEFAULT_RANS_THRESHOLD,
    'refine_iters': constants.DEFAULT_REFINE_ITERS,
    'align_confidence': constants.DEFAULT_ALIGN_CONFIDENCE,
    'max_iters': constants.DEFAULT_ALIGN_MAX_ITERS,
    'border_mode': constants.DEFAULT_BORDER_MODE,
    'border_value': constants.DEFAULT_BORDER_VALUE,
    'border_blur': constants.DEFAULT_BORDER_BLUR,
    'subsample': constants.DEFAULT_ALIGN_SUBSAMPLE,
    'fast_subsampling': constants.DEFAULT_ALIGN_FAST_SUBSAMPLING,
    'min_good_matches': constants.DEFAULT_ALIGN_MIN_GOOD_MATCHES
}


_cv2_border_mode_map = {
    constants.BORDER_CONSTANT: cv2.BORDER_CONSTANT,
    constants.BORDER_REPLICATE: cv2.BORDER_REPLICATE,
    constants.BORDER_REPLICATE_BLUR: cv2.BORDER_REPLICATE
}


def get_good_matches(des_0, des_1, matching_config=None):
    matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
    match_method = matching_config['match_method']
    good_matches = []
    if match_method == constants.MATCHING_KNN:
        flann = cv2.FlannBasedMatcher(
            {'algorithm': matching_config['flann_idx_kdtree'],
             'trees': matching_config['flann_trees']},
            {'checks': matching_config['flann_checks']})
        matches = flann.knnMatch(des_0, des_1, k=2)
        good_matches = [m for m, n in matches
                        if m.distance < matching_config['threshold'] * n.distance]
    elif match_method == constants.MATCHING_NORM_HAMMING:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        good_matches = sorted(bf.match(des_0, des_1), key=lambda x: x.distance)
    else:
        raise InvalidOptionError(
            'match_method', match_method,
            f". Valid options are: {constants.MATCHING_KNN}, {constants.MATCHING_NORM_HAMMING}"
        )
    return good_matches


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


def detect_and_compute(img_0, img_1, feature_config=None, matching_config=None):
    feature_config = {**_DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
    matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
    feature_config_detector = feature_config['detector']
    feature_config_descriptor = feature_config['descriptor']
    match_method = matching_config['match_method']
    validate_align_config(feature_config_detector, feature_config_descriptor, match_method)
    img_bw_0, img_bw_1 = img_bw_8bit(img_0), img_bw_8bit(img_1)
    detector_map = {
        constants.DETECTOR_SIFT: cv2.SIFT_create,
        constants.DETECTOR_ORB: cv2.ORB_create,
        constants.DETECTOR_SURF: cv2.FastFeatureDetector_create,
        constants.DETECTOR_AKAZE: cv2.AKAZE_create,
        constants.DETECTOR_BRISK: cv2.BRISK_create
    }
    descriptor_map = {
        constants.DESCRIPTOR_SIFT: cv2.SIFT_create,
        constants.DESCRIPTOR_ORB: cv2.ORB_create,
        constants.DESCRIPTOR_AKAZE: cv2.AKAZE_create,
        constants.DETECTOR_BRISK: cv2.BRISK_create
    }
    detector = detector_map[feature_config_detector]()
    if feature_config_detector == feature_config_descriptor and \
       feature_config_detector in (constants.DETECTOR_SIFT,
                                   constants.DETECTOR_AKAZE,
                                   constants.DETECTOR_BRISK):
        kp_0, des_0 = detector.detectAndCompute(img_bw_0, None)
        kp_1, des_1 = detector.detectAndCompute(img_bw_1, None)
    else:
        descriptor = descriptor_map[feature_config_descriptor]()
        kp_0, des_0 = descriptor.compute(img_bw_0, detector.detect(img_bw_0, None))
        kp_1, des_1 = descriptor.compute(img_bw_1, detector.detect(img_bw_1, None))
    return kp_0, kp_1, get_good_matches(des_0, des_1, matching_config)


def find_transform(src_pts, dst_pts, transform=constants.DEFAULT_TRANSFORM,
                   method=constants.DEFAULT_ALIGN_METHOD,
                   rans_threshold=constants.DEFAULT_RANS_THRESHOLD,
                   max_iters=constants.DEFAULT_ALIGN_MAX_ITERS,
                   align_confidence=constants.DEFAULT_ALIGN_CONFIDENCE,
                   refine_iters=constants.DEFAULT_REFINE_ITERS):
    if method == 'RANSAC':
        cv2_method = cv2.RANSAC
    elif method == 'LMEDS':
        cv2_method = cv2.LMEDS
    else:
        raise InvalidOptionError(
            'align_method', method,
            f". Valid options are: {constants.ALIGN_RANSAC}, {constants.ALIGN_LMEDS}"
        )
    if transform == constants.ALIGN_HOMOGRAPHY:
        result = cv2.findHomography(src_pts, dst_pts, method=cv2_method,
                                    ransacReprojThreshold=rans_threshold,
                                    maxIters=max_iters)
    elif transform == constants.ALIGN_RIGID:
        result = cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2_method,
                                             ransacReprojThreshold=rans_threshold,
                                             confidence=align_confidence / 100.0,
                                             refineIters=refine_iters)
    else:
        raise InvalidOptionError("transform", transform)
    return result


def align_images(img_1, img_0, feature_config=None, matching_config=None, alignment_config=None,
                 plot_path=None, callbacks=None):
    feature_config = {**_DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
    matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
    alignment_config = {**_DEFAULT_ALIGNMENT_CONFIG, **(alignment_config or {})}
    try:
        cv2_border_mode = _cv2_border_mode_map[alignment_config['border_mode']]
    except KeyError as e:
        raise InvalidOptionError("border_mode", alignment_config['border_mode']) from e
    min_matches = 4 if alignment_config['transform'] == constants.ALIGN_HOMOGRAPHY else 3
    validate_image(img_0, *get_img_metadata(img_1))
    if callbacks and 'message' in callbacks:
        callbacks['message']()
    subsample = alignment_config['subsample']
    min_good_matches = alignment_config['min_good_matches']
    while True:
        if subsample > 1:
            if alignment_config['fast_subsampling']:
                img_0_sub, img_1_sub = \
                    img_0[::subsample, ::subsample], img_1[::subsample, ::subsample]
            else:
                img_0_sub = cv2.resize(img_0, (0, 0),
                                       fx=1 / subsample, fy=1 / subsample,
                                       interpolation=cv2.INTER_AREA)
                img_1_sub = cv2.resize(img_1, (0, 0),
                                       fx=1 / subsample, fy=1 / subsample,
                                       interpolation=cv2.INTER_AREA)
        else:
            img_0_sub, img_1_sub = img_0, img_1
        kp_0, kp_1, good_matches = detect_and_compute(img_0_sub, img_1_sub,
                                                      feature_config, matching_config)
        n_good_matches = len(good_matches)
        if n_good_matches > min_good_matches or subsample == 1:
            break
        subsample = 1
        if callbacks and 'warning' in callbacks:
            callbacks['warning'](
                f"only {n_good_matches} < {min_good_matches} matches found, "
                "retrying without subsampling")
    if callbacks and 'matches_message' in callbacks:
        callbacks['matches_message'](n_good_matches)
    img_warp = None
    m = None
    if n_good_matches >= min_matches:
        transform = alignment_config['transform']
        src_pts = np.float32([kp_0[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp_1[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        m, msk = find_transform(src_pts, dst_pts, transform, alignment_config['align_method'],
                                *(alignment_config[k]
                                  for k in ['rans_threshold', 'max_iters',
                                            'align_confidence', 'refine_iters']))
        if plot_path is not None:
            matches_mask = msk.ravel().tolist()
            img_match = cv2.cvtColor(cv2.drawMatches(
                img_8bit(img_0_sub), kp_0, img_8bit(img_1_sub),
                kp_1, good_matches, None, matchColor=(0, 255, 0),
                singlePointColor=None, matchesMask=matches_mask,
                flags=2), cv2.COLOR_BGR2RGB)
            plt.figure(figsize=(10, 5))
            plt.imshow(img_match, 'gray')
            plt.savefig(plot_path)
            if callbacks and 'save_plot' in callbacks:
                callbacks['save_plot'](plot_path)
        h, w = img_0.shape[:2]
        h_sub, w_sub = img_0_sub.shape[:2]
        if subsample > 1:
            if transform == constants.ALIGN_HOMOGRAPHY:
                low_size = np.float32([[0, 0], [0, h_sub], [w_sub, h_sub], [w_sub, 0]])
                high_size = np.float32([[0, 0], [0, h], [w, h], [w, 0]])
                scale_up = cv2.getPerspectiveTransform(low_size, high_size)
                scale_down = cv2.getPerspectiveTransform(high_size, low_size)
                m = scale_up @ m @ scale_down
            elif transform == constants.ALIGN_RIGID:
                rotation = m[:2, :2]
                translation = m[:, 2]
                translation_fullres = translation * subsample
                m = np.empty((2, 3), dtype=np.float32)
                m[:2, :2] = rotation
                m[:, 2] = translation_fullres
            else:
                raise InvalidOptionError("transform", transform)
        if callbacks and 'align_message' in callbacks:
            callbacks['align_message']()
        img_mask = np.ones_like(img_0, dtype=np.uint8)
        if alignment_config['transform'] == constants.ALIGN_HOMOGRAPHY:
            img_warp = cv2.warpPerspective(
                img_0, m, (w, h),
                borderMode=cv2_border_mode, borderValue=alignment_config['border_value'])
            if alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
                mask = cv2.warpPerspective(img_mask, m, (w, h),
                                           borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        elif alignment_config['transform'] == constants.ALIGN_RIGID:
            img_warp = cv2.warpAffine(
                img_0, m, (w, h),
                borderMode=cv2_border_mode, borderValue=alignment_config['border_value'])
            if alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
                mask = cv2.warpAffine(img_mask, m, (w, h),
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        if alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
            if callbacks and 'blur_message' in callbacks:
                callbacks['blur_message']()
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            blurred_warp = cv2.GaussianBlur(
                img_warp, (21, 21), sigmaX=alignment_config['border_blur'])
            img_warp[mask == 0] = blurred_warp[mask == 0]
    return n_good_matches, m, img_warp


class AlignFrames(SubAction):
    def __init__(self, enabled=True, feature_config=None, matching_config=None,
                 alignment_config=None, **kwargs):
        super().__init__(enabled)
        self.process = None
        self.n_matches = None
        self.feature_config = {**_DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
        self.matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
        self.alignment_config = {**_DEFAULT_ALIGNMENT_CONFIG, **(alignment_config or {})}
        self.min_matches = 4 \
            if self.alignment_config['transform'] == constants.ALIGN_HOMOGRAPHY else 3
        self.plot_summary = kwargs.get('plot_summary', False)
        self.plot_matches = kwargs.get('plot_matches', False)
        for k in self.feature_config:
            if k in kwargs:
                self.feature_config[k] = kwargs[k]
        for k in self.matching_config:
            if k in kwargs:
                self.matching_config[k] = kwargs[k]
        for k in self.alignment_config:
            if k in kwargs:
                self.alignment_config[k] = kwargs[k]

    def run_frame(self, idx, ref_idx, img_0):
        if idx == self.process.ref_idx:
            return img_0
        img_ref = self.process.img_ref(ref_idx)
        return self.align_images(idx, img_ref, img_0)

    def sub_msg(self, msg, color=constants.LOG_COLOR_LEVEL_3):
        self.process.sub_message_r(color_str(msg, color))

    def align_images(self, idx, img_1, img_0):
        idx_str = f"{idx:04d}"
        callbacks = {
            'message': lambda: self.sub_msg(': find matches'),
            'matches_message': lambda n: self.sub_msg(f": good matches: {n}"),
            'align_message': lambda: self.sub_msg(': align images'),
            'ecc_message': lambda: self.sub_msg(": ecc refinement"),
            'blur_message': lambda: self.sub_msg(': blur borders'),
            'warning': lambda msg: self.sub_msg(
                f': {msg}', constants.LOG_COLOR_ALERT),
            'save_plot': lambda plot_path: self.process.callback(
                'save_plot', self.process.id,
                f"{self.process.name}: matches\nframe {idx_str}", plot_path)
        }
        if self.plot_matches:
            plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                f"{self.process.name}-matches-{idx_str}.pdf"
        else:
            plot_path = None
        n_good_matches, _m, img = align_images(
            img_1, img_0,
            feature_config=self.feature_config,
            matching_config=self.matching_config,
            alignment_config=self.alignment_config,
            plot_path=plot_path,
            callbacks=callbacks
        )
        self.n_matches[idx] = n_good_matches
        if n_good_matches < self.min_matches:
            self.process.sub_message(f": image not aligned, too few matches found: "
                                     f"{n_good_matches}", level=logging.CRITICAL)
            raise AlignmentError(idx, f"too few matches found: "
                                 f"{n_good_matches} < {self.min_matches}")
        return img

    def begin(self, process):
        self.process = process
        self.n_matches = np.zeros(process.counts)

    def end(self):
        if self.plot_summary:
            plt.figure(figsize=(10, 5))
            x = np.arange(1, len(self.n_matches) + 1, dtype=int)
            no_ref = x != self.process.ref_idx + 1
            x = x[no_ref]
            y = self.n_matches[no_ref]
            y_max = y[1] \
                if self.process.ref_idx == 0 \
                else y[-1] if self.process.ref_idx == len(y) - 1 \
                else (y[self.process.ref_idx - 1] + y[self.process.ref_idx]) / 2

            plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                     [0, y_max], color='cornflowerblue', linestyle='--', label='reference frame')
            plt.plot([x[0], x[-1]], [self.min_matches, self.min_matches], color='lightgray',
                     linestyle='--', label='min. matches')
            plt.plot(x, y, color='navy', label='matches')
            plt.xlabel('frame')
            plt.ylabel('# of matches')
            plt.legend()
            plt.ylim(0)
            plt.xlim(x[0], x[-1])
            plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                        f"{self.process.name}-matches.pdf"
            save_plot(plot_path)
            plt.close('all')
            self.process.callback('save_plot', self.process.id,
                                  f"{self.process.name}: matches", plot_path)
