# pylint: disable=C0114, C0115, C0116, E1101, R0914, R0912, R0913, R0903, E1121, R0917, R0915
import math
import numpy as np
import cv2
import matplotlib.pyplot as plt
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. core.exceptions import InvalidOptionError
from .utils import img_8bit


AFFINE_THRESHOLDS = {
    'max_rotation': 10.0,  # degrees
    'min_scale': 0.9,
    'max_scale': 1.1,
    'max_shear': 5.0,  # degrees
    'max_translation_ratio': 0.1,  # 10% of image dimension
}

HOMOGRAPHY_THRESHOLDS = {
    'max_skew': 10.0,  # degrees
    'max_scale_change': 1.5,  # max area change ratio
    'max_aspect_ratio': 2.0,  # max aspect ratio change
}

AFFINE_THRESHOLDS_LARGE = {
    'max_rotation': 20.0,  # degrees
    'min_scale': 0.5,
    'max_scale': 1.5,
    'max_shear': 10.0,  # degrees
    'max_translation_ratio': 0.2,  # 20% of image dimension
}

HOMOGRAPHY_THRESHOLDS_LARGE = {
    'max_skew': 12.0,  # degrees
    'max_scale_change': 2.0,  # max area change ratio
    'max_aspect_ratio': 4.0,  # max aspect ratio change
}


def decompose_affine_matrix(m):
    a, b, tx = m[0, 0], m[0, 1], m[0, 2]
    c, d, ty = m[1, 0], m[1, 1], m[1, 2]
    scale_x = math.sqrt(a**2 + b**2)
    scale_y = math.sqrt(c**2 + d**2)
    rotation = math.degrees(math.atan2(b, a))
    shear = math.degrees(math.atan2(-c, d)) - rotation
    shear = (shear + 180) % 360 - 180
    return (scale_x, scale_y), rotation, shear, (tx, ty)


def check_affine_matrix(m, img_shape, affine_thresholds):
    if affine_thresholds is None:
        return True, "No thresholds provided", None
    (scale_x, scale_y), rotation, shear, (tx, ty) = decompose_affine_matrix(m)
    h, w = img_shape[:2]
    reasons = []
    if abs(rotation) > affine_thresholds['max_rotation']:
        reasons.append(f"rotation too large ({rotation:.1f}°)")
    if scale_x < affine_thresholds['min_scale'] or scale_x > affine_thresholds['max_scale']:
        reasons.append(f"x-scale out of range ({scale_x:.2f})")
    if scale_y < affine_thresholds['min_scale'] or scale_y > affine_thresholds['max_scale']:
        reasons.append(f"y-scale out of range ({scale_y:.2f})")
    if abs(shear) > affine_thresholds['max_shear']:
        reasons.append(f"shear too large ({shear:.1f}°)")
    max_tx = w * affine_thresholds['max_translation_ratio']
    max_ty = h * affine_thresholds['max_translation_ratio']
    if abs(tx) > max_tx:
        reasons.append(f"x-translation too large (|{tx:.1f}| > {max_tx:.1f})")
    if abs(ty) > max_ty:
        reasons.append(f"y-translation too large (|{ty:.1f}| > {max_ty:.1f})")
    if reasons:
        return False, "; ".join(reasons), None
    return True, "Transformation within acceptable limits", \
        (scale_x, scale_y, tx, ty, rotation, shear)


def check_homography_distortion(m, img_shape, homography_thresholds):
    if homography_thresholds is None:
        return True, "No thresholds provided", None
    h, w = img_shape[:2]
    corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
    transformed = cv2.perspectiveTransform(corners.reshape(1, -1, 2), m).reshape(-1, 2)
    reasons = []
    area_orig = w * h
    area_new = cv2.contourArea(transformed)
    area_ratio = area_new / area_orig
    if area_ratio > homography_thresholds['max_scale_change'] or \
       area_ratio < 1.0 / homography_thresholds['max_scale_change']:
        reasons.append(f"area change too large ({area_ratio:.2f})")
    rect = cv2.minAreaRect(transformed.astype(np.float32))
    (w_rect, h_rect) = rect[1]
    aspect_ratio = max(w_rect, h_rect) / min(w_rect, h_rect)
    if aspect_ratio > homography_thresholds['max_aspect_ratio']:
        reasons.append(f"aspect ratio change too large ({aspect_ratio:.2f})")
    angles = []
    for i in range(4):
        vec1 = transformed[(i + 1) % 4] - transformed[i]
        vec2 = transformed[(i - 1) % 4] - transformed[i]
        angle = np.degrees(np.arccos(np.dot(vec1, vec2) /
                           (np.linalg.norm(vec1) * np.linalg.norm(vec2))))
        angles.append(angle)
    max_angle_dev = max(abs(angle - 90) for angle in angles)
    if max_angle_dev > homography_thresholds['max_skew']:
        reasons.append(f"angle distortion too large ({max_angle_dev:.1f}°)")
    if reasons:
        return False, "; ".join(reasons), None
    return True, "Transformation within acceptable limits", \
        (area_ratio, aspect_ratio, max_angle_dev)


def check_transform(m, img_shape, transform_type, affine_thresholds, homography_thresholds):
    if img_shape is None:
        return False, 'null image shape', None
    if transform_type == constants.ALIGN_RIGID:
        return check_affine_matrix(
            m, img_shape, affine_thresholds)
    if transform_type == constants.ALIGN_HOMOGRAPHY:
        return check_homography_distortion(
            m, img_shape, homography_thresholds)
    return False, f'invalid transfrom option {transform_type}', None


def find_transform(src_pts, dst_pts, subsample,
                   transform=DEFAULTS['align_frames_params']['transform'],
                   method=DEFAULTS['align_frames_params']['align_method'],
                   rans_threshold=DEFAULTS['align_frames_params']['rans_threshold'],
                   max_iters=DEFAULTS['align_frames_params']['max_iters'],
                   align_confidence=DEFAULTS['align_frames_params']['align_confidence'],
                   refine_iters=DEFAULTS['align_frames_params']['refine_iters'],
                   compute_rans_quality=DEFAULTS[
                       'align_frames_params']['compute_rans_quality'],
                   rans_inlier_fraction_threshold=DEFAULTS[
                       'align_frames_params']['rans_inlier_fraction_threshold'],
                   rans_avg_error_threshold=DEFAULTS[
                       'align_frames_params']['rans_avg_error_threshold'],
                   rans_max_error_threshold=DEFAULTS[
                       'align_frames_params']['rans_max_error_threshold']):
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
        m, mask = cv2.findHomography(src_pts, dst_pts, method=cv2_method,
                                     ransacReprojThreshold=rans_threshold,
                                     maxIters=max_iters)
    elif transform == constants.ALIGN_RIGID:
        m, mask = cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2_method,
                                              ransacReprojThreshold=rans_threshold,
                                              confidence=align_confidence / 100.0,
                                              refineIters=refine_iters)
    else:
        raise InvalidOptionError(
            'transform', method,
            f". Valid options are: {constants.ALIGN_HOMOGRAPHY}, {constants.ALIGN_RIGID}"
        )
    if compute_rans_quality:
        quality = compute_ransac_quality(
            src_pts, dst_pts, m, mask, transform, subsample,
            rans_inlier_fraction_threshold, rans_avg_error_threshold, rans_max_error_threshold)
    else:
        quality = None
    return m, mask, quality


def compute_ransac_quality(src_pts, dst_pts, m, mask, transform_type, subsample,
                           rans_inlier_fraction_threshold,
                           rans_avg_error_threshold,
                           rans_max_error_threshold):
    if m is None or mask is None:
        return None
    src_pts = np.array(src_pts, dtype=np.float32).reshape(-1, 2)
    dst_pts = np.array(dst_pts, dtype=np.float32).reshape(-1, 2)
    m = np.array(m, dtype=np.float32)
    mask = np.array(mask, dtype=np.uint8).ravel()
    inlier_indices = np.where(mask == 1)[0]
    n_inliers = len(inlier_indices)
    n_total = len(src_pts)
    if n_inliers == 0:
        return {'status': 'FAILED', 'n_inliers': 0}
    src_inliers = src_pts[inlier_indices]
    dst_inliers = dst_pts[inlier_indices]
    if transform_type == constants.ALIGN_HOMOGRAPHY:
        src_homo = np.hstack([src_inliers, np.ones((n_inliers, 1))])
        dst_pred_homo = np.dot(src_homo, m.T)
        dst_pred = dst_pred_homo[:, :2] / dst_pred_homo[:, 2:3]
    else:
        if m.shape != (2, 3):
            if m.size == 6:
                m = m.reshape(2, 3)
            else:
                return None
        src_homo = np.hstack([src_inliers, np.ones((n_inliers, 1))])
        dst_pred = np.dot(src_homo, m.T)
    errors = np.linalg.norm(dst_inliers - dst_pred, axis=1)
    avg_error = float(np.mean(errors) / math.sqrt(n_inliers) * subsample)
    max_error = float(np.max(errors) * subsample)
    inlier_fraction = n_inliers / n_total
    if inlier_fraction > rans_inlier_fraction_threshold and avg_error < rans_avg_error_threshold \
            and max_error < rans_max_error_threshold:
        status = 'GOOD'
    elif n_inliers > 0:
        status = 'POOR'
    else:
        status = 'FAILED'
    return {
        'inlier_fraction': inlier_fraction,
        'avg_error_px': avg_error,
        'max_error_px': max_error,
        'status': status,
        'n_inliers': n_inliers,
        'subsample': subsample
    }


def rescale_transform(m, w0, h0, w_sub, h_sub, subsample, transform):
    if transform == constants.ALIGN_HOMOGRAPHY:
        low_size = np.float32([[0, 0], [0, h_sub], [w_sub, h_sub], [w_sub, 0]])
        high_size = np.float32([[0, 0], [0, h0], [w0, h0], [w0, 0]])
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
        return 0
    return m


def find_transform_phase_correlation(img_ref, img_0):
    if len(img_ref.shape) == 3:
        ref_gray = cv2.cvtColor(img_ref[..., :3], cv2.COLOR_BGR2GRAY)
        mov_gray = cv2.cvtColor(img_0[..., :3], cv2.COLOR_BGR2GRAY)
    else:
        ref_gray = img_ref
        mov_gray = img_0
    h, w = ref_gray.shape
    window_y = np.hanning(h)
    window_x = np.hanning(w)
    window = np.outer(window_y, window_x)
    ref_win = ref_gray.astype(np.float32) * window
    mov_win = mov_gray.astype(np.float32) * window
    ref_fft = np.fft.fft2(ref_win)
    mov_fft = np.fft.fft2(mov_win)
    ref_mag = np.fft.fftshift(np.abs(ref_fft))
    mov_mag = np.fft.fftshift(np.abs(mov_fft))
    center = (w // 2, h // 2)
    radius = min(center[0], center[1])
    y, x = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((x - center[0])**2 + (y - center[1])**2)
    log_r_bins = np.logspace(0, np.log10(radius), 50, endpoint=False)
    ref_profile = []
    mov_profile = []
    for i in range(len(log_r_bins) - 1):
        mask = (dist_from_center >= log_r_bins[i]) & (dist_from_center < log_r_bins[i + 1])
        if np.any(mask):
            ref_profile.append(np.mean(ref_mag[mask]))
            mov_profile.append(np.mean(mov_mag[mask]))
    if len(ref_profile) < 5:
        scale = 1.0
    else:
        ref_prof = np.array(ref_profile)
        mov_prof = np.array(mov_profile)
        ref_prof = (ref_prof - np.mean(ref_prof)) / (np.std(ref_prof) + 1e-8)
        mov_prof = (mov_prof - np.mean(mov_prof)) / (np.std(mov_prof) + 1e-8)
        correlation = np.correlate(ref_prof, mov_prof, mode='full')
        shift_idx = np.argmax(correlation) - len(ref_prof) + 1
        scale = np.exp(shift_idx * 0.1)  # Empirical scaling factor
        scale = np.clip(scale, 0.9, 1.1)  # Limit to small scale changes
    if abs(scale - 1.0) > 0.01:
        scaled_size = (int(w * scale), int(h * scale))
        mov_scaled = cv2.resize(img_0, scaled_size)
        new_h, new_w = mov_scaled.shape[:2]
        start_x = (w - new_w) // 2
        start_y = (h - new_h) // 2
        mov_centered = np.zeros_like(img_0)
        mov_centered[start_y:start_y + new_h, start_x:start_x + new_w] = mov_scaled
    else:
        mov_centered = img_0
        scale = 1.0
    if len(img_ref.shape) == 3:
        ref_gray_trans = cv2.cvtColor(img_ref[..., :3], cv2.COLOR_BGR2GRAY)
        mov_gray_trans = cv2.cvtColor(mov_centered[..., :3], cv2.COLOR_BGR2GRAY)
    else:
        ref_gray_trans = img_ref
        mov_gray_trans = mov_centered
    ref_win_trans = ref_gray_trans.astype(np.float32) * window
    mov_win_trans = mov_gray_trans.astype(np.float32) * window
    shift, _response = cv2.phaseCorrelate(ref_win_trans, mov_win_trans)
    m = np.float32([[scale, 0, shift[0]], [0, scale, shift[1]]])
    return m


def plot_matches(msk, img_ref_sub, img_0_sub, kp_ref, kp_0, good_matches,
                 plot_path, plot_manager=None):
    matches_mask = msk.ravel().tolist()
    if len(good_matches) == 0:
        return
    match_result = cv2.drawMatches(
        img_8bit(img_0_sub), kp_0, img_8bit(img_ref_sub),
        kp_ref, good_matches, None, matchColor=(0, 255, 0),
        singlePointColor=None, matchesMask=matches_mask,
        flags=2)
    if match_result is None:
        return
    img_match = cv2.cvtColor(match_result, cv2.COLOR_BGR2RGB)
    fig, ax = plt.subplots(figsize=constants.PLT_FIG_SIZE)
    ax.imshow(img_match)
    ax.set_axis_off()
    plt.tight_layout()
    if plot_manager is not None and plot_path is not None:
        plot_manager.save_plot(plot_path, fig)
    plt.close(fig)


class TransformationExtractor:
    def __init__(self, alignment_config, affine_thresholds, homography_thresholds):
        self.alignment_config = alignment_config
        self.affine_thresholds = affine_thresholds
        self.homography_thresholds = homography_thresholds

    def extract_transformation(self, match_result, img_ref_sub, img_0_sub, subsample,
                               original_shape, callbacks=None, plot_path=None, plot_manager=None):
        transform_type = self.alignment_config['transform']
        min_matches = 4 if transform_type == constants.ALIGN_HOMOGRAPHY else 3
        min_good_matches = self.alignment_config['min_good_matches']
        phase_corr_fallback = self.alignment_config['phase_corr_fallback']
        n_good_matches = match_result.n_good_matches()
        m = None
        msk = None
        quality = None
        phase_corr_called = False
        if match_result.has_sufficient_matches(min_good_matches):
            src_pts = match_result.get_src_points()
            dst_pts = match_result.get_dst_points()
            m, msk, quality = find_transform(
                src_pts, dst_pts, subsample, transform_type, self.alignment_config['align_method'],
                *(self.alignment_config[k]
                  for k in ['rans_threshold', 'max_iters',
                            'align_confidence', 'refine_iters',
                            'compute_rans_quality',
                            'rans_inlier_fraction_threshold',
                            'rans_avg_error_threshold',
                            'rans_max_error_threshold']))
            if m is not None and plot_path is not None and plot_manager is not None:
                plot_matches(msk, img_ref_sub, img_0_sub, match_result.kp_ref, match_result.kp_0,
                             match_result.good_matches, plot_path, plot_manager)
                if callbacks and 'save_plot' in callbacks:
                    callbacks['save_plot'](plot_path, tag="matches")
        if m is None or not match_result.has_sufficient_matches(min_matches):
            if phase_corr_fallback:
                if callbacks and 'warning' in callbacks:
                    callbacks['warning'](
                        f"only {n_good_matches} < {min_good_matches} matches found"
                        ", using phase correlation as fallback")
                n_good_matches = 0
                m = find_transform_phase_correlation(img_ref_sub, img_0_sub)
                phase_corr_called = True
                if m is None:
                    if callbacks and 'warning' in callbacks:
                        callbacks['warning']("alignment by phase correlation failed")
                    return None, phase_corr_called, msk, None
            elif not match_result.has_sufficient_matches(min_matches):
                if callbacks and 'warning' in callbacks:
                    s_str = 'es' if n_good_matches > 1 else ''
                    callbacks['warning'](
                        f"only {n_good_matches} < {min_good_matches} "
                        f"match{s_str} found, alignment falied")
                return None, phase_corr_called, msk, None
            else:
                if callbacks and 'warning' in callbacks:
                    callbacks['warning']("could not compute transformation, alignment failed")
                return None, phase_corr_called, msk, None
        h0, w0 = original_shape[:2]
        h_sub, w_sub = img_0_sub.shape[:2]
        if subsample > 1:
            m = rescale_transform(m, w0, h0, w_sub, h_sub, subsample, transform_type)
            if m is None:
                if callbacks and 'warning' in callbacks:
                    callbacks['warning']("can't rescale transformation matrix, alignment failed")
                return None, phase_corr_called, msk, None
        is_valid, reason, result = check_transform(
            m, original_shape, transform_type,
            self.affine_thresholds, self.homography_thresholds)
        if callbacks and 'save_transform_result' in callbacks:
            callbacks['save_transform_result'](result)
        if not is_valid:
            if callbacks and 'warning' in callbacks:
                callbacks['warning'](f"invalid transformation: {reason}, alignment failed")
            if self.alignment_config['abort_abnormal']:
                raise RuntimeError(f"invalid transformation: {reason}, alignment failed")
            return None, phase_corr_called, msk, None
        if not phase_corr_called and callbacks and 'matches_message' in callbacks:
            callbacks['matches_message'](n_good_matches)
        return m, phase_corr_called, msk, quality

    def apply_alignment_transform(self, img_0, img_ref, m, callbacks=None):
        try:
            cv2_border_mode = {
                constants.BORDER_CONSTANT: cv2.BORDER_CONSTANT,
                constants.BORDER_REPLICATE: cv2.BORDER_REPLICATE,
                constants.BORDER_REPLICATE_BLUR: cv2.BORDER_REPLICATE
            }[self.alignment_config['border_mode']]
        except KeyError as e:
            raise InvalidOptionError("border_mode", self.alignment_config['border_mode']) from e
        if callbacks and 'estimation_message' in callbacks:
            callbacks['estimation_message']()
        transform_type = self.alignment_config['transform']
        if transform_type == constants.ALIGN_RIGID and m.shape != (2, 3):
            if callbacks and 'warning' in callbacks:
                callbacks['warning'](f"invalid matrix shape for rigid transform: {m.shape}")
            return None
        if transform_type == constants.ALIGN_HOMOGRAPHY and m.shape != (3, 3):
            if callbacks and 'warning' in callbacks:
                callbacks['warning'](f"invalid matrix shape for homography: {m.shape}")
            return None
        img_mask = np.ones_like(img_0, dtype=np.uint8)
        h_ref, w_ref = img_ref.shape[:2]
        img_warp = None
        if transform_type == constants.ALIGN_HOMOGRAPHY:
            img_warp = cv2.warpPerspective(
                img_0, m, (w_ref, h_ref),
                borderMode=cv2_border_mode, borderValue=self.alignment_config['border_value'])
            if self.alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
                mask = cv2.warpPerspective(img_mask, m, (w_ref, h_ref),
                                           borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        elif transform_type == constants.ALIGN_RIGID:
            img_warp = cv2.warpAffine(
                img_0, m, (w_ref, h_ref),
                borderMode=cv2_border_mode, borderValue=self.alignment_config['border_value'])
            if self.alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
                mask = cv2.warpAffine(img_mask, m, (w_ref, h_ref),
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        if self.alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
            if callbacks and 'blur_message' in callbacks:
                callbacks['blur_message']()
            mask = cv2.cvtColor(mask[..., :3], cv2.COLOR_BGR2GRAY)
            blurred_warp = cv2.GaussianBlur(
                img_warp, (21, 21), sigmaX=self.alignment_config['border_blur'])
            img_warp[mask == 0] = blurred_warp[mask == 0]
        if img_warp.ndim == 3 and img_warp.shape[2] == 4:
            coverage = np.ones(img_0.shape[:2], dtype=np.uint8)
            if transform_type == constants.ALIGN_HOMOGRAPHY:
                coverage = cv2.warpPerspective(coverage, m, (w_ref, h_ref),
                                               borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            else:
                coverage = cv2.warpAffine(coverage, m, (w_ref, h_ref),
                                          borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            img_warp[..., 3][coverage == 0] = 0
        return img_warp
