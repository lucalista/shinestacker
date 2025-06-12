import matplotlib.pyplot as plt
import cv2
import numpy as np
from focus_stack.utils import img_8bit, img_bw_8bit, save_plot
from focus_stack.exceptions import AlignmentError, InvalidOptionError
from focus_stack.utils import get_img_metadata, validate_image
import logging

ALIGN_HOMOGRAPHY = "ALIGN_HOMOGRAPHY"
ALIGN_RIGID = "ALIGN_RIGID"
BORDER_CONSTANT = "BORDER_CONSTANT"
BORDER_REPLICATE = "BORDER_REPLICATE"
BORDER_REPLICATE_BLUR = "BORDER_REPLICATE_BLUR"
DETECTOR_SIFT = "SIFT"
DETECTOR_ORB = "ORB"
DETECTOR_SURF = "SURF"
DETECTOR_AKAZE = "AKAZE"
DESCRIPTOR_SIFT = "SIFT"
DESCRIPTOR_ORB = "ORB"
DESCRIPTOR_AKAZE = "AKAZE"
MATCHING_KNN = "KNN"
MATCHING_NORM_HAMMING = "NORM_HAMMING"

_DEFAULT_FEATURE_CONFIG = {
    'detector': DETECTOR_SIFT,
    'descriptor': DESCRIPTOR_SIFT
}

_DEFAULT_MATCHING_CONFIG = {
    'method': MATCHING_KNN,
    'flann_idx_kdtree': 2,
    'flann_trees': 5,
    'flann_checks': 50,
    'threshold': 0.75
}

_DEFAULT_ALIGNMENT_CONFIG = {
    'transform': ALIGN_RIGID,
    'rans_threshold': 5.0,
    'border_mode': BORDER_REPLICATE_BLUR,
    'border_value': (0, 0, 0, 0),
    'border_blur': 50
}

_cv2_border_mode_map = {
    BORDER_CONSTANT: cv2.BORDER_CONSTANT,
    BORDER_REPLICATE: cv2.BORDER_REPLICATE,
    BORDER_REPLICATE_BLUR: cv2.BORDER_REPLICATE
}

_VALID_DETECTORS = {DETECTOR_SIFT, DETECTOR_ORB, DETECTOR_SURF, DETECTOR_AKAZE}
_VALID_DESCRIPTORS = {DESCRIPTOR_SIFT, DESCRIPTOR_ORB, DESCRIPTOR_AKAZE}
_VALID_MATCHING_METHODS = {MATCHING_KNN, MATCHING_NORM_HAMMING}
_VALID_TRANSFORMS = {ALIGN_HOMOGRAPHY, ALIGN_RIGID}
_VALID_BORDER_MODES = {BORDER_CONSTANT, BORDER_REPLICATE, BORDER_REPLICATE_BLUR}


def get_good_matches(des_0, des_1, matching_config=None):
    matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
    if matching_config['method'] == MATCHING_KNN:
        flann = cv2.FlannBasedMatcher(
            dict(algorithm=matching_config['flann_idx_kdtree'], trees=matching_config['flann_trees']),
            dict(checks=matching_config['flann_checks']))
        matches = flann.knnMatch(des_0, des_1, k=2)
        good_matches = [m for m, n in matches if m.distance < matching_config['threshold'] * n.distance]
    elif matching_config['method'] == MATCHING_NORM_HAMMING:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        good_matches = sorted(bf.match(des_0, des_1), key=lambda x: x.distance)
    return good_matches


def detect_and_compute(img_0, img_1, feature_config=None, matching_config=None):
    feature_config = {**_DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
    matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
    img_bw_0, img_bw_1 = img_bw_8bit(img_0), img_bw_8bit(img_1)
    detector_map = {
        DETECTOR_SIFT: cv2.SIFT_create,
        DETECTOR_ORB: cv2.ORB_create,
        DETECTOR_SURF: cv2.FastFeatureDetector_create,
        DETECTOR_AKAZE: cv2.AKAZE_create
    }
    descriptor_map = {
        DESCRIPTOR_SIFT: cv2.SIFT_create,
        DESCRIPTOR_ORB: cv2.ORB_create,
        DESCRIPTOR_AKAZE: cv2.AKAZE_create
    }
    detector = detector_map[feature_config['detector']]()
    descriptor = descriptor_map[feature_config['descriptor']]()
    if feature_config['detector'] == feature_config['descriptor'] and feature_config['detector'] in {DETECTOR_SIFT, DETECTOR_AKAZE}:
        kp_0, des_0 = detector.detectAndCompute(img_bw_0, None)
        kp_1, des_1 = detector.detectAndCompute(img_bw_1, None)
    else:
        kp_0, des_0 = descriptor.compute(img_bw_0, detector.detect(img_bw_0, None))
        kp_1, des_1 = descriptor.compute(img_bw_1, detector.detect(img_bw_1, None))
    return kp_0, kp_1, get_good_matches(des_0, des_1, matching_config)


def find_transform(src_pts, dst_pts, transform=ALIGN_RIGID, rans_threshold=5.0):
    if transform == ALIGN_HOMOGRAPHY:
        return cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, rans_threshold)
    elif transform == ALIGN_RIGID:
        return cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=rans_threshold)
    raise InvalidOptionError("transform", transform)


def align_images(img_1, img_0, feature_config=None, matching_config=None, alignment_config=None, plot_path=None, callbacks=None):
    feature_config = {**_DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
    matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
    alignment_config = {**_DEFAULT_ALIGNMENT_CONFIG, **(alignment_config or {})}
    try:
        cv2_border_mode = _cv2_border_mode_map[alignment_config['border_mode']]
    except KeyError:
        raise InvalidOptionError("border_mode", alignment_config['border_mode'])
    min_matches = 4 if alignment_config['transform'] == ALIGN_HOMOGRAPHY else 3
    validate_image(img_0, *get_img_metadata(img_1))
    if callbacks and 'message' in callbacks:
        callbacks['message']()
    kp_0, kp_1, good_matches = detect_and_compute(img_0, img_1, feature_config, matching_config)
    n_good_matches = len(good_matches)
    if callbacks and 'matches_message' in callbacks:
        callbacks['matches_message'](n_good_matches)
    img_warp = None
    if n_good_matches >= min_matches:
        src_pts = np.float32([kp_0[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp_1[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        M, msk = find_transform(src_pts, dst_pts, alignment_config['transform'], alignment_config['rans_threshold'])
        h, w = img_0.shape[:2]
        if callbacks and 'align_message' in callbacks:
            callbacks['align_message']()
        if alignment_config['transform'] == ALIGN_HOMOGRAPHY:
            img_warp = cv2.warpPerspective(img_0, M, (w, h),
                                           borderMode=cv2_border_mode, borderValue=alignment_config['border_value'])
            if alignment_config['border_mode'] == BORDER_REPLICATE_BLUR:
                mask = cv2.warpPerspective(np.ones_like(img_0, dtype=np.uint8), M, (w, h),
                                           borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        elif alignment_config['transform'] == ALIGN_RIGID:
            img_warp = cv2.warpAffine(img_0, M, (img_0.shape[1], img_0.shape[0]),
                                      borderMode=cv2_border_mode, borderValue=alignment_config['border_value'])
            if alignment_config['border_mode'] == BORDER_REPLICATE_BLUR:
                mask = cv2.warpAffine(np.ones_like(img_0, dtype=np.uint8), M, (w, h),
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        if alignment_config['border_mode'] == BORDER_REPLICATE_BLUR:
            if callbacks and 'blur_message' in callbacks:
                callbacks['blur_message']()
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            blurred_warp = cv2.GaussianBlur(img_warp, (21, 21), sigmaX=alignment_config['border_blur'])
            img_warp[mask == 0] = blurred_warp[mask == 0]
        if plot_path is not None:
            matches_mask = msk.ravel().tolist()
            img_match = cv2.cvtColor(cv2.drawMatches(img_8bit(img_0), kp_0, img_8bit(img_1),
                                                     kp_1, good_matches, None, matchColor=(0, 255, 0),
                                                     singlePointColor=None, matchesMask=matches_mask,
                                                     flags=2), cv2.COLOR_BGR2RGB)
            plt.figure(figsize=(10, 5))
            plt.imshow(img_match, 'gray')
            plt.savefig(plot_path)
    return n_good_matches, img_warp


class AlignFrames:
    def __init__(self, feature_config=None, matching_config=None, alignment_config=None, plot_histograms=False):
        self.feature_config = {**_DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
        self.matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
        self.alignment_config = {**_DEFAULT_ALIGNMENT_CONFIG, **(alignment_config or {})}
        self.min_matches = 4 if self.alignment_config['transform'] == ALIGN_HOMOGRAPHY else 3
        self.plot_histograms = plot_histograms

    def run_frame(self, idx, ref_idx, img_0):
        if idx == self.process.ref_idx:
            return img_0
        img_ref = self.process.img_ref(ref_idx)
        return self.align_images(idx, img_ref, img_0)

    def align_images(self, idx, img_1, img_0):
        callbacks = {
            'message': lambda: self.process.sub_message_r(': find matches'),
            'matches_message': lambda n: self.process.sub_message_r(f": matches: {n}"),
            'align_message': lambda: self.process.sub_message_r(': align images'),
            'blur_message': lambda: self.process.sub_message_r(': blur borders')
        }
        if self.plot_histograms:
            plot_path = self.process.working_path + "/" + self.process.plot_path + "/" + f"{self.process.name}-matches-{idx:04d}.pdf"
        else:
            plot_path = None
        n_good_matches, img = align_images(
            img_1, img_0,
            feature_config=self.feature_config,
            matching_config=self.matching_config,
            alignment_config=self.alignment_config,
            plot_path=plot_path,
            callbacks=callbacks
        )
        self.n_matches[idx] = n_good_matches
        if n_good_matches < self.min_matches:
            self.process.sub_message(f": image not aligned, too few matches found: {n_good_matches}", level=logging.CRITICAL)
            raise AlignmentError(idx, f"too few matches found: {n_good_matches} < {self.min_matches}")
        return img

    def begin(self, process):
        self.process = process
        self.n_matches = np.zeros(process.counts)

    def end(self):
        if self.plot_histograms:
            plt.figure(figsize=(10, 5))
            x = np.arange(1, len(self.n_matches) + 1, dtype=int)
            no_ref = (x != self.process.ref_idx + 1)
            x = x[no_ref]
            y = self.n_matches[no_ref]
            y_max = y[1] if self.process.ref_idx == 0 else y[-1] if self.process.ref_idx == len(y) - 1 else (y[self.process.ref_idx - 1] + y[self.process.ref_idx]) / 2 # noqa

            plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1], [0, y_max], color='cornflowerblue', linestyle='--', label='reference frame')
            plt.plot([x[0], x[-1]], [self.min_matches, self.min_matches], color='lightgray', linestyle='--', label='min. matches')
            plt.plot(x, y, color='navy', label='matches')
            plt.xlabel('frame')
            plt.ylabel('# of matches')
            plt.legend()
            plt.ylim(0)
            plt.xlim(x[0], x[-1])
            save_plot(self.process.working_path + "/" + self.process.plot_path + "/" + self.process.name + "-matches.pdf")
            plt.close('all')
