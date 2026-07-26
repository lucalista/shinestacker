# pylint: disable=C0114, C0115, C0116, E1101, R0914, R0913, E1128, C3001
# pylint: disable=R0917, R0912, R0915, R0902, E1121, W0102, W0718
import os
import math
import logging
import numpy as np
import matplotlib.pyplot as plt
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. config.app_config import AppConfig
from .. core.exceptions import InvalidOptionError
from .. core.colors import color_str
from .stack_framework import SubAction
from .feature_match import (
    SubsamplingFeatureMatcher,
    DEFAULT_FEATURE_CONFIG, DEFAULT_MATCHING_CONFIG, DEFAULT_ALIGNMENT_CONFIG)
from .transform_estimate import (
    TransformationExtractor,
    AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS, AFFINE_THRESHOLDS_LARGE,
    HOMOGRAPHY_THRESHOLDS_LARGE)


def get_subsample_factor(h0, w0, target_res):
    img_res = (float(h0) / constants.ONE_KILO) * (float(w0) / constants.ONE_KILO)
    return int(math.sqrt(1 + math.floor(img_res / target_res)))


def align_images(img_ref, img_0, feature_config=None, matching_config=None, alignment_config=None,
                 plot_path=None, plot_manager=None, callbacks=None,
                 affine_thresholds=AFFINE_THRESHOLDS,
                 homography_thresholds=HOMOGRAPHY_THRESHOLDS):
    feature_config = {**DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
    matching_config = {**DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
    alignment_config = {**DEFAULT_ALIGNMENT_CONFIG, **(alignment_config or {})}
    if callbacks and 'message' in callbacks:
        callbacks['message']()
    h0, w0 = img_0.shape[:2]
    subsample = alignment_config['subsample']
    if subsample == 0:
        subsample = get_subsample_factor(
            h0, w0, DEFAULTS['align_frames_params']['resolution_target'])
    feature_matcher = SubsamplingFeatureMatcher(
        feature_config, matching_config, alignment_config, callbacks)
    match_result, _final_subsample = feature_matcher.match_images_with_fallback(
        img_ref, img_0, subsample=subsample,
        warning_callback=lambda msg:
            callbacks['warning'](msg) if callbacks and 'warning' in callbacks else None
    )
    n_good_matches = match_result.n_good_matches()
    img_ref_sub, img_0_sub = feature_matcher.get_last_subsampled_images()
    extractor = TransformationExtractor(
        alignment_config, affine_thresholds, homography_thresholds)
    m, _phase_corr_called, _msk, _quality = extractor.extract_transformation(
        match_result, img_ref_sub, img_0_sub, subsample, img_0.shape, callbacks,
        plot_path, plot_manager)
    if m is None:
        if callbacks and 'warning' in callbacks:
            callbacks['warning']('could not extract transformation, alignment failed')
        return n_good_matches, None, None
    img_warp = extractor.apply_alignment_transform(img_0, img_ref, m, callbacks)
    return match_result.n_good_matches(), m, img_warp


class AlignFramesBase(SubAction):
    def __init__(self, name='', enabled=True, feature_config=None, matching_config=None,
                 alignment_config=None, use_large_thresholds=False, **kwargs):
        super().__init__(name, enabled)
        self.process = None
        self._n_good_matches = None
        self.feature_config = {**DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
        self.matching_config = {**DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
        self.alignment_config = {**DEFAULT_ALIGNMENT_CONFIG, **(alignment_config or {})}
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
        self._subsamples = None
        self._area_ratio = None
        self._aspect_ratio = None
        self._max_angle_dev = None
        self._scale_x = None
        self._scale_y = None
        self._translation_x = None
        self._translation_y = None
        self._rotation = None
        self._shear = None
        self._inlier_fractions = None
        self._avg_errors = None
        self._max_errors = None
        if use_large_thresholds:
            affine_thresholds, homography_thresholds = self.get_transform_thresholds_large()
        else:
            affine_thresholds, homography_thresholds = self.get_transform_thresholds()
        self.feature_matcher = SubsamplingFeatureMatcher(
            self.feature_config, self.matching_config, self.alignment_config)
        self.transformation_extractor = TransformationExtractor(
            self.alignment_config, affine_thresholds, homography_thresholds)

    def align_images(self, _idx, _img_ref, _img_0):
        pass

    def print_message(self, msg, color=constants.LOG_COLOR_LEVEL_3, level=logging.INFO):
        self.process.print_message(color_str(msg, color), level=level)

    def begin(self, process):
        self.process = process
        self._subsamples = np.zeros(process.total_action_counts)
        self._n_good_matches = np.zeros(process.total_action_counts)
        self._area_ratio = np.ones(process.total_action_counts)
        self._aspect_ratio = np.ones(process.total_action_counts)
        self._max_angle_dev = np.zeros(process.total_action_counts)
        self._scale_x = np.ones(process.total_action_counts)
        self._scale_y = np.ones(process.total_action_counts)
        self._translation_x = np.zeros(process.total_action_counts)
        self._translation_y = np.zeros(process.total_action_counts)
        self._rotation = np.zeros(process.total_action_counts)
        self._shear = np.zeros(process.total_action_counts)
        self._inlier_fractions = np.zeros(process.total_action_counts)
        self._avg_errors = np.zeros(process.total_action_counts)
        self._max_errors = np.zeros(process.total_action_counts)

    def get_img_ref(self, _ref_idx):
        return None

    def run_frame(self, idx, ref_idx, img_0):
        if idx == self.process.ref_idx:
            return img_0
        img_ref = self.get_img_ref(ref_idx)
        return self.align_images(idx, img_ref, img_0)

    def get_transform_thresholds(self):
        return AFFINE_THRESHOLDS, HOMOGRAPHY_THRESHOLDS

    def get_transform_thresholds_large(self):
        return AFFINE_THRESHOLDS_LARGE, HOMOGRAPHY_THRESHOLDS_LARGE

    def image_str(self, idx):
        return f"{self.process.frame_str(idx)}, " \
               f"{os.path.basename(self.process.input_filepath(idx))}"

    def end(self):

        def get_coordinates(items):
            x = np.arange(1, len(items) + 1, dtype=int)
            no_ref = x != self.process.ref_idx + 1
            x = x[no_ref]
            y = np.array(items)[no_ref]
            if self.process.ref_idx == 0:
                y_ref = y[1]
            elif self.process.ref_idx >= len(y):
                y_ref = y[-1]
            else:
                y_ref = (y[self.process.ref_idx - 1] + y[self.process.ref_idx]) / 2
            return x, y, y_ref

        if self.plot_summary:
            save_plot_name = self.process.output_path if self.name == '' else self.name
            plots_ext = AppConfig.get('plots_format')
            fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
            x, y, y_ref = get_coordinates(self._n_good_matches)
            plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                     [0, y_ref], color='cornflowerblue', linestyle='--', label='reference frame')
            plt.plot([x[0], x[-1]], [self.min_matches, self.min_matches], color='lightgray',
                     linestyle='--', label='min. matches')
            plt.plot(x, y, color='navy', label='matches')
            plt.title("Number of matches")
            plt.xlabel('frame')
            plt.ylabel('# of matches')
            plt.legend()
            plt.ylim(0)
            plt.xlim(x[0], x[-1])
            plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                        f"{self.process.name}-matches.{plots_ext}"
            self.process.plot_manager.save_plot(plot_path, fig)
            self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                  save_plot_name, f"{self.process.name}: matches", plot_path)
            transform = self.alignment_config['transform']
            title = "Transformation parameters rel. to reference frame"
            if transform == constants.ALIGN_RIGID:
                fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
                x, y, y_ref = get_coordinates(self._rotation)
                plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                         [0, y_ref], color='cornflowerblue',
                         linestyle='--', label='reference frame')
                plt.plot([x[0], x[-1]], [0, 0], color='cornflowerblue', linestyle='--')
                plt.plot(x, y, color='navy', label='rotation (°)')
                y_lim = max(1, max(abs(y.min()), abs(y.max())) * 1.1)
                plt.ylim(-y_lim, y_lim)
                plt.title(title)
                plt.xlabel('frame')
                plt.ylabel('rotation angle (degrees)')
                plt.legend()
                plt.xlim(x[0], x[-1])
                plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                            f"{self.process.name}-rotation.{plots_ext}"
                self.process.plot_manager.save_plot(plot_path, fig)
                self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                      save_plot_name, f"{self.process.name}: rotation", plot_path)
                fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
                x, y_x, y_x_ref = get_coordinates(self._translation_x)
                x, y_y, y_y_ref = get_coordinates(self._translation_y)
                plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                         [y_x_ref, y_y_ref], color='cornflowerblue',
                         linestyle='--', label='reference frame')
                plt.plot([x[0], x[-1]], [0, 0], color='cornflowerblue', linestyle='--')
                plt.plot(x, y_x, color='blue', label='translation, x (px)')
                plt.plot(x, y_y, color='red', label='translation, y (px)')
                y_lim = max(
                    1, max(abs(y_x.min()), abs(y_x.max()), abs(y_y.min()), abs(y_y.max())) * 1.1)
                plt.ylim(-y_lim, y_lim)
                plt.title(title)
                plt.xlabel('frame')
                plt.ylabel('translation (pixels)')
                plt.legend()
                plt.xlim(x[0], x[-1])
                plots_ext = AppConfig.get('plots_format')
                plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                            f"{self.process.name}-translation.{plots_ext}"
                self.process.plot_manager.save_plot(plot_path, fig)
                self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                      save_plot_name, f"{self.process.name}: translation",
                                      plot_path)
                fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
                x, y, y_ref = get_coordinates(self._scale_x)
                plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                         [1, y_ref], color='cornflowerblue',
                         linestyle='--', label='reference frame')
                plt.plot([x[0], x[-1]], [1, 1], color='cornflowerblue', linestyle='--')
                plt.plot(x, y, color='blue', label='scale factor')
                d_max = max(0.01, max(abs(y.min() - 1), abs(y.max() - 1)) * 1.1)
                plt.ylim(1.0 - d_max, 1.0 + d_max)
                plt.title(title)
                plt.xlabel('frame')
                plt.ylabel('scale factor')
                plt.legend()
                plt.xlim(x[0], x[-1])
                plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                            f"{self.process.name}-scale.{plots_ext}"
                self.process.plot_manager.save_plot(plot_path, fig)
                self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                      save_plot_name, f"{self.process.name}: scale", plot_path)
            elif transform == constants.ALIGN_HOMOGRAPHY:
                fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
                x, y, y_ref = get_coordinates(self._area_ratio)
                plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                         [0, y_ref], color='cornflowerblue',
                         linestyle='--', label='reference frame')
                plt.plot([x[0], x[-1]], [0, 0], color='cornflowerblue', linestyle='--')
                plt.plot(x, y, color='navy', label='area ratio')
                d_max = max(abs(y.min() - 1), abs(y.max() - 1)) * 1.1
                plt.ylim(1.0 - d_max, 1.0 + d_max)
                plt.title(title)
                plt.xlabel('frame')
                plt.ylabel('warped area ratio')
                plt.legend()
                plt.xlim(x[0], x[-1])
                plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                            f"{self.process.name}-area-ratio.{plots_ext}"
                self.process.plot_manager.save_plot(plot_path, fig)
                self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                      save_plot_name, f"{self.process.name}: area ratio", plot_path)
                fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
                x, y, y_ref = get_coordinates(self._aspect_ratio)
                plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                         [0, y_ref], color='cornflowerblue',
                         linestyle='--', label='reference frame')
                plt.plot([x[0], x[-1]], [0, 0], color='cornflowerblue', linestyle='--')
                plt.plot(x, y, color='navy', label='aspect ratio')
                y_min, y_max = y.min(), y.max()
                delta = y_max - y_min
                plt.ylim(y_min - 0.05 * delta, y_max + 0.05 * delta)
                plt.title(title)
                plt.xlabel('frame')
                plt.ylabel('aspect ratio')
                plt.legend()
                plt.xlim(x[0], x[-1])
                plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                            f"{self.process.name}-aspect-ratio.{plots_ext}"
                self.process.plot_manager.save_plot(plot_path, fig)
                self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                      save_plot_name, f"{self.process.name}: aspect ratio",
                                      plot_path)
                fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
                x, y, y_ref = get_coordinates(self._max_angle_dev)
                plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                         [0, y_ref], color='cornflowerblue',
                         linestyle='--', label='reference frame')
                plt.plot([x[0], x[-1]], [0, 0], color='cornflowerblue', linestyle='--')
                plt.plot(x, y, color='navy', label='max. dev. ang. (°)')
                y_lim = max(abs(y.min()), abs(y.max())) * 1.1
                plt.ylim(-y_lim, y_lim)
                plt.title(title)
                plt.xlabel('frame')
                plt.ylabel('max deviation angle (degrees)')
                plt.legend()
                plt.xlim(x[0], x[-1])
                plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                            f"{self.process.name}-rotation.{plots_ext}"
                self.process.plot_manager.save_plot(plot_path, fig)
                self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                      save_plot_name, f"{self.process.name}: rotation", plot_path)
            fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
            x, y, y_ref = get_coordinates(self._subsamples)
            plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                     [0, y_ref], color='cornflowerblue', linestyle='--', label='reference frame')
            plt.axhline(y=1, color='red',
                        linestyle='--', label='full resolution')
            plt.plot(x, y, color='darkgreen', linewidth=2, label='subsample factor')
            plt.title("Subsample factor")
            plt.xlabel('frame')
            plt.ylabel('subsample factor')
            plt.ylim(0)
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.xlim(x[0], x[-1])
            plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                        f"{self.process.name}-subsample.{plots_ext}"
            self.process.plot_manager.save_plot(plot_path, fig)
            self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                  save_plot_name, f"{self.process.name}: inlier ratio", plot_path)
            if self.alignment_config['compute_rans_quality']:
                rans_inlier_fraction_threshold = self.alignment_config.get(
                    'rans_inlier_fraction_threshold')
                rans_avg_error_threshold = self.alignment_config.get('rans_avg_error_threshold')
                rans_max_error_threshold = self.alignment_config.get('rans_max_error_threshold')
                fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
                x, y, y_ref = get_coordinates(self._inlier_fractions)
                plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                         [0, y_ref], color='cornflowerblue', linestyle='--',
                         label='reference frame')
                plt.axhline(y=rans_inlier_fraction_threshold, color='red',
                            linestyle='--', label=f'threshold ({rans_inlier_fraction_threshold})')
                plt.plot(x, y, color='darkgreen', linewidth=2, label='inlier ratio')
                plt.title("RANSAC Inlier Ratio per Frame")
                plt.xlabel('frame')
                plt.ylabel('inlier ratio')
                plt.ylim(0, 1.05)
                plt.legend()
                plt.grid(True, alpha=0.3)
                plt.xlim(x[0], x[-1])
                plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                            f"{self.process.name}-inlier-ratio.{plots_ext}"
                self.process.plot_manager.save_plot(plot_path, fig)
                self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                      save_plot_name, f"{self.process.name}: inlier ratio",
                                      plot_path)
                fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
                x, y, y_ref = get_coordinates(self._avg_errors)
                plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                         [0, y_ref], color='cornflowerblue', linestyle='--',
                         label='reference frame')
                plt.axhline(y=rans_avg_error_threshold, color='red',
                            linestyle='--', label=f'threshold ({rans_avg_error_threshold}px)')
                plt.plot(x, y, color='darkred', linewidth=2, label='avg error (px)')
                plt.title("Average Reprojection Error per Frame")
                plt.xlabel('frame')
                plt.ylabel('error (pixels)')
                plt.legend()
                plt.grid(True, alpha=0.3)
                plt.xlim(x[0], x[-1])
                plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                            f"{self.process.name}-avg-error.{plots_ext}"
                self.process.plot_manager.save_plot(plot_path, fig)
                self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                      save_plot_name, f"{self.process.name}: avg error", plot_path)
                fig = plt.figure(figsize=constants.PLT_FIG_SIZE)
                x, y, y_ref = get_coordinates(self._max_errors)
                rans_max_error_threshold = self.alignment_config.get(
                    'rans_max_error_threshold', 1.0)
                plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                         [0, y_ref], color='cornflowerblue', linestyle='--',
                         label='reference frame')
                plt.axhline(y=rans_max_error_threshold, color='red',
                            linestyle='--', label=f'threshold ({rans_max_error_threshold}px)')
                plt.plot(x, y, color='purple', linewidth=2, label='max error (px)')
                plt.title("Maximum Reprojection Error per Frame")
                plt.xlabel('frame')
                plt.ylabel('max error (pixels)')
                plt.legend()
                plt.grid(True, alpha=0.3)
                plt.xlim(x[0], x[-1])
                plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                            f"{self.process.name}-max-error.{plots_ext}"
                self.process.plot_manager.save_plot(plot_path, fig)
                self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                      save_plot_name, f"{self.process.name}: max error", plot_path)

    def save_transform_result(self, idx, result):
        if result is None:
            return
        transform = self.alignment_config['transform']
        if transform == constants.ALIGN_HOMOGRAPHY:
            area_ratio, aspect_ratio, max_angle_dev = result
            self._area_ratio[idx] = area_ratio
            self._aspect_ratio[idx] = aspect_ratio
            self._max_angle_dev[idx] = max_angle_dev
        elif transform == constants.ALIGN_RIGID:
            scale_x, scale_y, translation_x, translation_y, rotation, shear = result
            self._scale_x[idx] = scale_x
            self._scale_y[idx] = scale_y
            self._translation_x[idx] = translation_x * self._subsamples[idx]
            self._translation_y[idx] = translation_y * self._subsamples[idx]
            self._rotation[idx] = rotation
            self._shear[idx] = shear
        else:
            raise InvalidOptionError(
                'transform', transform,
                f". Valid options are: {constants.ALIGN_HOMOGRAPHY}, {constants.ALIGN_RIGID}"
            )

    def save_quality_metrics(self, idx, quality):
        if quality is None:
            return
        self._inlier_fractions[idx] = quality.get('inlier_fraction', 0)
        self._avg_errors[idx] = quality.get('avg_error_px', 0)
        self._max_errors[idx] = quality.get('max_error_px', 0)

    def compute_transformation(self, idx, img_ref, img_0, callbacks, plot_path):
        def run_with_subsample(subsample_val):
            match_result, final_subsample = self.feature_matcher.match_images_with_fallback(
                img_ref, img_0, subsample=subsample_val,
                warning_callback=warning_callback
            )
            n_good_matches = match_result.n_good_matches()
            img_ref_sub, img_0_sub = self.feature_matcher.get_last_subsampled_images()
            m, phase_corr_called, _msk, quality = \
                self.transformation_extractor.extract_transformation(
                    match_result, img_ref_sub, img_0_sub, final_subsample, img_0.shape, callbacks,
                    plot_path, self.process.plot_manager)
            return m, phase_corr_called, quality, n_good_matches
        h0, w0 = img_0.shape[:2]
        subsample = self.alignment_config['subsample']
        if subsample == 0:
            subsample = get_subsample_factor(
                h0, w0, DEFAULTS['align_frames_params']['resolution_target'])
            self._subsamples[idx] = subsample
        warning_callback = None
        if callbacks and 'warning' in callbacks:
            warning_callback = callbacks['warning']
        else:
            warning_callback = lambda msg: self.print_message(  # noqa
                f'{self.image_str(idx)}: {msg}',
                color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
        m, phase_corr_called, quality, n_good_matches = run_with_subsample(subsample)
        if self.alignment_config['compute_rans_quality'] and quality and \
                quality.get('status') != 'GOOD' and subsample != 1:
            self.print_message(
                f'{self.image_str(idx)}: poor match quality: {quality}, '
                'retrying with no subsampling',
                color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
            self._subsamples[idx] = 1
            m, phase_corr_called, quality, n_good_matches = run_with_subsample(1)
        if quality:
            self.save_quality_metrics(idx, quality)
        return m, phase_corr_called, quality, n_good_matches


class AlignFrames(AlignFramesBase):
    def __init__(self, name='', enabled=True, feature_config=None, matching_config=None,
                 alignment_config=None, **kwargs):
        super().__init__(name, enabled, feature_config, matching_config,
                         alignment_config, use_large_thresholds=True, **kwargs)

    def align_images(self, idx, img_ref, img_0):
        idx_str = f"{idx:04d}"
        idx_tot_str = self.process.frame_str(idx)
        save_plot_name = self.process.output_path if self.name == '' else self.name
        callbacks = {
            'message': lambda: self.print_message(
                f'{idx_tot_str}: estimate transform using feature matching'),
            'matches_message': lambda n: self.print_message(
                f'{idx_tot_str}: good matches found: {n}'),
            'estimation_message': lambda: self.print_message(
                f'{idx_tot_str}: align images'),
            'blur_message': lambda: self.print_message(f'{idx_tot_str}: blur borders'),
            'warning': lambda msg: self.print_message(color_str(
                f'{msg}', constants.LOG_COLOR_WARNING), level=logging.WARNING),
            'save_plot': lambda plot_path, tag="_default": self.process.callback(
                constants.CALLBACK_SAVE_PLOT, self.process.id,
                save_plot_name, f"{self.process.name}: matches\nframe {idx_str}", plot_path,
                tag),
            'save_transform_result': lambda result: self.save_transform_result(idx, result)
        }
        if self.plot_matches:
            plots_ext = AppConfig.get('plots_format')
            plot_path = os.path.join(
                self.process.working_path,
                self.process.plot_path,
                f"{self.process.name}-matches-{idx_str}.{plots_ext}")
        else:
            plot_path = None
        if callbacks and 'message' in callbacks:
            callbacks['message']()

        m, _phase_corr_called, _quality, n_good_matches = self.compute_transformation(
            idx, img_ref, img_0, callbacks, plot_path)

        self._n_good_matches[idx] = n_good_matches
        if m is None:
            return None
        img_warp = self.transformation_extractor.apply_alignment_transform(
            img_0, img_ref, m, callbacks)
        return img_warp

    def get_img_ref(self, ref_idx):
        return self.process.saved_img_ref(ref_idx)

    def sequential_processing(self):
        return True
