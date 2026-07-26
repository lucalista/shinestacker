# pylint: disable=C0114
import os

DEFAULTS = {
    'check_for_updates': True,
    'expert_options': False,
    'plots_format': 'png',
    'project_view_strategy': 'modern_horizontal',
    'retouch_view_strategy': 'overlaid',
    'retouch_after_run': False,
    'input_folder_path': '',
    'paint_refresh_time': 50,  # ms
    'display_refresh_time': 50,  # ms
    'cursor_update_time': 16,  # ms
    'min_mouse_step_brush_fraction': 0.25,
    'cursor_style': 'preview',
    'brush_size': 100,
    'brush_hardness': 50,
    'brush_opacity': 100,
    'brush_flow': 100,
    'temp_folder_path': '',
    'raw_formats': {
        'auto_bright': True,
        'auto_bright_thr': 1.0,  # %
    },
    'sequential_task': {
        'max_threads': 8,
        'chunk_submit': True
    },
    'image_sequence_manager': {
        'reverse_order': False,
        'plots_path': 'plots'
    },
    'reference_frame_task': {
        'step_process': True
    },
    'combined_actions_params': {
        'max_threads': int(min(os.cpu_count() or 4, 256)),
    },
    'align_frames_params': {
        'memory_limit': 8,  # GB
        'max_threads': int(min(os.cpu_count() or 4, 256)),
        'detector': 'ORB',
        'descriptor': 'ORB',
        'match_method': 'NORM_HAMMING',
        'flann_idx_kdtree': 2,
        'flann_trees': 5,
        'flann_checks': 50,
        'threshold': 0.75,
        'transform': 'ALIGN_RIGID',
        'align_method': 'RANSAC',
        'rans_threshold': 3.0,  # px
        'refine_iters': 100,
        'align_confidence': 99.9,
        'max_iters': 2000,
        'border_mode': 'BORDER_REPLICATE_BLUR',
        'border_value': [0] * 4,
        'border_blur': 50,  # px
        'subsample': 0,
        'fast_subsampling': False,
        'min_good_matches': 20,
        'phase_corr_fallback': False,
        'abort_abnormal': False,
        'resolution_target': 2,  # Mpx
        'align_mode': 'auto',
        'chunk_submit': True,
        'bw_matching': False,
        'delta_max': 2,
        'compute_rans_quality': False,
        'rans_inlier_fraction_threshold': 0.75,
        'rans_avg_error_threshold': 1.0,
        'rans_max_error_threshold': 30,
    },
    'balance_frames_params': {
        'subsample': 0,
        'fast_subsampling': False,
        'resolution_target': 2,  # Mpx
        'corr_map': 'LINEAR',
        'channel': 'LUMI',
        'mask_size': 0,
        'intensity_interval': {'min': 0, 'max': -1}
    },
    'stacker': 'Pyramid',
    'focus_stack_params': {
        'memory_limit': 8,  # GB
        'max_threads': int(min(os.cpu_count() or 4, 256)),
        'prefix': "stack_",
        'plot_stack': True,
        'denoise_amount': 0.0,
        'sharpen_amount_percent': 0.0,
        'sharpen_radius': 1.0,
        'sharpen_threshold': 0.0

    },
    'focus_stack_bunch_params': {
        'memory_limit': 8,  # GB
        'max_threads': int(min(os.cpu_count() or 4, 256)),
        'frames': 10,
        'overlap': 2,
        'prefix': "bunch_",
        'plot_stack': True
    },
    'depth_map_params': {
        'mode': 'auto',
        'float_type': 'float-32',
        'map_type': 'max',
        'energy': 'laplacian',
        'kernel_size': 5,
        'blur_size': 5,
        'weight_power': 1.0,
        'pyramid_levels': 5,
        'energy_smooth_size': 1,
        'energy_sigma_color': 0.8,
        'energy_sigma_space': 2,
        'pyramid_smooth_size': 1,
        'temperature': 0.0,
        'plot_depth_map': False
    },
    'pyramid_params': {
        'method': 'rgb',
        'float_type': 'float-32',
        'min_size': 32,
        'kernel_size': 5,
        'gen_kernel': 0.4,
        'tile_size': 512,
        'n_tiled_layers': 2,
        'mode': 'auto',
        'max_tile_size': 4096,
        'min_tile_size': 128,
        'min_n_tiled_layers': 1
    },
    'noise_detection_params': {
        'method': 'norm_lab',
        'noise_map_filename': 'hot_pixels.png',
        'max_frames': 10,
        'noisy_masked_px': [100, 100, 100],
        'channel_thresholds': [13, 13, 13],
        'blur_size': 5,
        'plot_histograms': False,
        'use_lab_space': True,
    },
    'mask_noise_params': {
        'kernel_size': 3,
        'method': 'MEAN',
        'max_noisy_pxls': 2000
    },
    'vignetting_params': {
        'r_steps': 100,
        'black_threshold': 1.0,
        'max_correction': 1.0,
        'subsample': 0,
        'fast_subsampling': False
    },
    'multilayer_params': {
        'file_reverse_order': True
    }
}
