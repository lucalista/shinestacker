import matplotlib.pyplot as plt
import cv2
import numpy as np
import logging
from focusstack.config.constants import constants
from focusstack.core.exceptions import AlignmentError, InvalidOptionError
from focusstack.algorithms.utils import img_8bit, img_bw_8bit, save_plot
from focusstack.algorithms.utils import get_img_metadata, validate_image
from focusstack.algorithms.stack_framework import SubAction

_DEFAULT_FEATURE_CONFIG = {
    'detector': constants.DEFAULT_DETECTOR,
    'descriptor': constants.DEFAULT_DESCRIPTOR
}

_DEFAULT_MATCHING_CONFIG = {
    'method': constants.DEFAULT_MATCHING_METHOD,
    'flann_idx_kdtree': constants.DEFAULT_FLANN_IDX_KDTREE,
    'flann_trees': constants.DEFAULT_FLANN_TREES,
    'flann_checks': constants.DEFAULT_FLANN_CHECKS,
    'threshold': constants.DEFAULT_ALIGN_THRESHOLD
}

_DEFAULT_ALIGNMENT_CONFIG = {
    'transform': constants.DEFAULT_TRANSFORM,
    'rans_threshold': constants.DEFAULT_RANS_THRESHOLD,
    'border_mode': constants.DEFAULT_BORDER_MODE,
    'border_value': constants.DEFAULT_BORDER_VALUE,
    'border_blur': constants.DEFAULT_BORDER_BLUR,
    'subsample': constants.DEFAULT_ALIGN_SUBSAMPLE,
    'fast_subsampling': constants.DEFAULT_ALIGN_FAST_SUBSAMPLING,
    'ecc_refinement': constants.DEFAULT_ECC_REFINEMENT,
    'ecc_gauss_filt_size': constants.DEFAULT_ECC_GAUSS_FILT_SIZE,
    'ecc_criteria': (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-7),
}

_cv2_border_mode_map = {
    constants.BORDER_CONSTANT: cv2.BORDER_CONSTANT,
    constants.BORDER_REPLICATE: cv2.BORDER_REPLICATE,
    constants.BORDER_REPLICATE_BLUR: cv2.BORDER_REPLICATE
}

RAISE_ORB_ORB_HAMMING = "align: detector ORB and descriptor ORB require match method NORM_HAMMING"


def get_good_matches(des_0, des_1, matching_config=None):
    matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
    matching_config_method = matching_config['method']
    if matching_config_method == constants.MATCHING_KNN:
        flann = cv2.FlannBasedMatcher(
            dict(algorithm=matching_config['flann_idx_kdtree'], trees=matching_config['flann_trees']),
            dict(checks=matching_config['flann_checks']))
        matches = flann.knnMatch(des_0, des_1, k=2)
        good_matches = [m for m, n in matches if m.distance < matching_config['threshold'] * n.distance]
    elif matching_config_method == constants.MATCHING_NORM_HAMMING:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        good_matches = sorted(bf.match(des_0, des_1), key=lambda x: x.distance)
    return good_matches


def detect_and_compute(img_0, img_1, feature_config=None, matching_config=None):
    feature_config = {**_DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
    matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
    img_bw_0, img_bw_1 = img_bw_8bit(img_0), img_bw_8bit(img_1)
    detector_map = {
        constants.DETECTOR_SIFT: cv2.SIFT_create,
        constants.DETECTOR_ORB: cv2.ORB_create,
        constants.DETECTOR_SURF: cv2.FastFeatureDetector_create,
        constants.DETECTOR_AKAZE: cv2.AKAZE_create
    }
    descriptor_map = {
        constants.DESCRIPTOR_SIFT: cv2.SIFT_create,
        constants.DESCRIPTOR_ORB: cv2.ORB_create,
        constants.DESCRIPTOR_AKAZE: cv2.AKAZE_create
    }
    detector = detector_map[feature_config['detector']]()
    descriptor = descriptor_map[feature_config['descriptor']]()
    feature_config_detector = feature_config['detector']
    feature_config_descriptor = feature_config['descriptor']
    if feature_config_detector == constants.DETECTOR_ORB and \
       feature_config_descriptor == constants.DESCRIPTOR_ORB and matching_config['method'] != constants.MATCHING_NORM_HAMMING:
        raise RuntimeError(RAISE_ORB_ORB_HAMMING)
    if feature_config_detector == feature_config_descriptor and \
       feature_config_detector in (constants.DETECTOR_SIFT, constants.DETECTOR_AKAZE):
        kp_0, des_0 = detector.detectAndCompute(img_bw_0, None)
        kp_1, des_1 = detector.detectAndCompute(img_bw_1, None)
    else:
        kp_0, des_0 = descriptor.compute(img_bw_0, detector.detect(img_bw_0, None))
        kp_1, des_1 = descriptor.compute(img_bw_1, detector.detect(img_bw_1, None))
    return kp_0, kp_1, get_good_matches(des_0, des_1, matching_config)


def find_transform(src_pts, dst_pts, transform=constants.DEFAULT_TRANSFORM,
                   rans_threshold=constants.DEFAULT_RANS_THRESHOLD):
    if transform == constants.ALIGN_HOMOGRAPHY:
        transf = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, rans_threshold)
    elif transform == constants.ALIGN_RIGID:
        transf = cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2.RANSAC,
                                             ransacReprojThreshold=rans_threshold)
    else:
        raise InvalidOptionError("transform", transform)
    return transf


def align_images(img_1, img_0, feature_config=None, matching_config=None, alignment_config=None,
                 plot_path=None, callbacks=None):
    feature_config = {**_DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
    matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
    alignment_config = {**_DEFAULT_ALIGNMENT_CONFIG, **(alignment_config or {})}
    try:
        cv2_border_mode = _cv2_border_mode_map[alignment_config['border_mode']]
    except KeyError:
        raise InvalidOptionError("border_mode", alignment_config['border_mode'])
    min_matches = 4 if alignment_config['transform'] == constants.ALIGN_HOMOGRAPHY else 3
    validate_image(img_0, *get_img_metadata(img_1))
    if callbacks and 'message' in callbacks.keys():
        callbacks['message']()

    subsample = alignment_config['subsample']
    if subsample:
        if alignment_config['fast_subsampling']:
            img_0_sub, img_1_sub = img_0[::subsample, ::subsample], img_1[::subsample, ::subsample]
        else:
            img_0_sub = cv2.resize(img_0, (0, 0), fx=1 / subsample, fy=1 / subsample, interpolation=cv2.INTER_AREA)
            img_1_sub = cv2.resize(img_0, (0, 0), fx=1 / subsample, fy=1 / subsample, interpolation=cv2.INTER_AREA)
        kp_0, kp_1, good_matches = detect_and_compute(img_0_sub, img_1_sub, feature_config, matching_config)
    else:
        img_0_sub, img_1_sub = img_0, img_1
    n_good_matches = len(good_matches)
    if callbacks and 'matches_message' in callbacks.keys():
        callbacks['matches_message'](n_good_matches)
    img_warp = None
    if n_good_matches >= min_matches:
        transform = alignment_config['transform']
        src_pts = np.float32([kp_0[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp_1[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        M, msk = find_transform(src_pts, dst_pts, transform, alignment_config['rans_threshold'])
        if plot_path is not None:
            matches_mask = msk.ravel().tolist()
            img_match = cv2.cvtColor(cv2.drawMatches(img_8bit(img_0_sub), kp_0, img_8bit(img_1_sub),
                                                     kp_1, good_matches, None, matchColor=(0, 255, 0),
                                                     singlePointColor=None, matchesMask=matches_mask,
                                                     flags=2), cv2.COLOR_BGR2RGB)
            plt.figure(figsize=(10, 5))
            plt.imshow(img_match, 'gray')
            plt.savefig(plot_path)
            if callbacks and 'save_plot' in callbacks.keys():
                callbacks['save_plot'](plot_path)

        h, w = img_0.shape[:2]
        h_sub, w_sub = img_0_sub.shape[:2]
        if subsample > 1:
            if transform == constants.ALIGN_HOMOGRAPHY:
                low_size = np.float32([[0, 0], [0, h_sub], [w_sub, h_sub], [w_sub, 0]])
                high_size = np.float32([[0, 0], [0, h], [w, h], [w, 0]])
                scale_up = cv2.getPerspectiveTransform(low_size, high_size)
                scale_down = cv2.getPerspectiveTransform(high_size, low_size)
                M = scale_up @ M @ scale_down
            elif transform == constants.ALIGN_RIGID:
                M_rigid_3x3 = np.vstack([M, [0.0, 0.0, 1.0]])
                scale_up = np.array([
                    [1.0 / subsample, 0.0, 0.0],
                    [0.0, 1.0 / subsample, 0.0],
                    [0.0, 0.0, 1.0]
                ])
                scale_down = np.array([
                    [float(subsample), 0.0, 0.0],
                    [0.0, float(subsample), 0.0],
                    [0.0, 0.0, 1.0]
                ])
                M = (scale_up @ M_rigid_3x3 @ scale_down)[:2, :]
            else:
                raise InvalidOptionError("transform", transform)

            if alignment_config['ecc_refinement']:
                if callbacks and 'ecc_message' in callbacks.keys():
                    callbacks['ecc_message']()
                img0_gray = img_bw_8bit(img_0)
                img1_gray = img_bw_8bit(img_1)
                try:
                    if transform == constants.ALIGN_HOMOGRAPHY:
                        M_init = M.astype(np.float32)
                        cc, M_refined = cv2.findTransformECC(
                            templateImage=img1_gray,
                            inputImage=img0_gray,
                            warpMatrix=M_init,
                            motionType=cv2.MOTION_HOMOGRAPHY,
                            criteria=alignment_config['ecc_criteria'],
                            inputMask=None,
                            gaussFiltSize=alignment_config['ecc_gauss_filt_size']
                        )
                        M = M_refined
                    elif transform == constants.ALIGN_RIGID:
                        M_init = np.eye(2, 3, dtype=np.float32)
                        a, b, tx = M[0]
                        c, d, ty = M[1]
                        # scale = np.sqrt(a * a + b * b)
                        angle = np.arctan2(b, a) * 180 / np.pi
                        M_init[0, 0] = np.cos(np.radians(angle))
                        M_init[0, 1] = -np.sin(np.radians(angle))
                        M_init[1, 0] = np.sin(np.radians(angle))
                        M_init[1, 1] = np.cos(np.radians(angle))
                        M_init[0, 2] = tx
                        M_init[1, 2] = ty
                        cc, M_refined = cv2.findTransformECC(
                            templateImage=img1_gray,
                            inputImage=img0_gray,
                            warpMatrix=M_init,
                            motionType=cv2.MOTION_EUCLIDEAN,
                            criteria=alignment_config['ecc_criteria'],
                            inputMask=None,
                            gaussFiltSize=alignment_config['ecc_gauss_filt_size']
                        )
                        cos_theta = M_refined[0, 0]
                        sin_theta = M_refined[1, 0]
                        tx = M_refined[0, 2]
                        ty = M_refined[1, 2]
                        M = np.array([
                            [cos_theta, -sin_theta, tx],
                            [sin_theta, cos_theta, ty]
                        ], dtype=np.float32)
                except cv2.error:
                    raise RuntimeError("ECC refinement failed.")

        if callbacks and 'align_message' in callbacks.keys():
            callbacks['align_message']()
        img_mask = np.ones_like(img_0, dtype=np.uint8)
        if alignment_config['transform'] == constants.ALIGN_HOMOGRAPHY:
            img_warp = cv2.warpPerspective(img_0, M, (w, h),
                                           borderMode=cv2_border_mode, borderValue=alignment_config['border_value'])
            if alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
                mask = cv2.warpPerspective(img_mask, M, (w, h),
                                           borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        elif alignment_config['transform'] == constants.ALIGN_RIGID:
            img_warp = cv2.warpAffine(img_0, M, (w, h),
                                      borderMode=cv2_border_mode, borderValue=alignment_config['border_value'])
            if alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
                mask = cv2.warpAffine(img_mask, M, (w, h),
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        if alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
            if callbacks and 'blur_message' in callbacks.keys():
                callbacks['blur_message']()
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            blurred_warp = cv2.GaussianBlur(img_warp, (21, 21), sigmaX=alignment_config['border_blur'])
            img_warp[mask == 0] = blurred_warp[mask == 0]
    return n_good_matches, img_warp


class AlignFrames(SubAction):
    def __init__(self, enabled=True, feature_config=None, matching_config=None, alignment_config=None, **kwargs):
        super().__init__(enabled)
        self.feature_config = {**_DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
        self.matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
        self.alignment_config = {**_DEFAULT_ALIGNMENT_CONFIG, **(alignment_config or {})}
        self.min_matches = 4 if self.alignment_config['transform'] == constants.ALIGN_HOMOGRAPHY else 3
        self.plot_summary = kwargs.get('plot_summary', False)
        self.plot_matches = kwargs.get('plot_matches', False)
        for k in self.feature_config.keys():
            if k in kwargs.keys():
                self.feature_config[k] = kwargs[k]
        for k in self.matching_config.keys():
            if k in kwargs.keys():
                self.matching_config[k] = kwargs[k]
        for k in self.alignment_config.keys():
            if k in kwargs.keys():
                self.alignment_config[k] = kwargs[k]

    def run_frame(self, idx, ref_idx, img_0):
        if idx == self.process.ref_idx:
            return img_0
        img_ref = self.process.img_ref(ref_idx)
        return self.align_images(idx, img_ref, img_0)

    def align_images(self, idx, img_1, img_0):
        idx_str = "{:04d}".format(idx)
        callbacks = {
            'message': lambda: self.process.sub_message_r(': find matches'),
            'matches_message': lambda n: self.process.sub_message_r(f": matches: {n}"),
            'align_message': lambda: self.process.sub_message_r(': align images'),
            'ecc_message': lambda: self.process.sub_message_r(": ecc refinement"),
            'blur_message': lambda: self.process.sub_message_r(': blur borders'),
            'save_plot': lambda plot_path: self.process.callback('save_plot', self.process.id,
                                                                 f"{self.process.name}: matches\nframe {idx_str}", plot_path)
        }
        if self.plot_matches:
            plot_path = f"{self.process.working_path}/{self.process.plot_path}/{self.process.name}-matches-{idx_str}.pdf"
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
        if self.plot_summary:
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
            plot_path = f"{self.process.working_path}/{self.process.plot_path}/{self.process.name}-matches.pdf"
            save_plot(plot_path)
            plt.close('all')
            self.process.callback('save_plot', self.process.id, f"{self.process.name}: matches", plot_path)
