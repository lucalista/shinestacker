# pylint: disable=C0114, C0115, C0116, E1101, R0902, R0913, R0917, R0914, R0912, R0915
import os
import numpy as np
import cv2
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. core.exceptions import InvalidOptionError
from .utils import read_img, write_img, read_and_validate_img, img_bw
from .base_stack_algo import BaseStackAlgo, TempDirBase


class DepthMapStack(BaseStackAlgo, TempDirBase):
    supports_alpha = True

    def __init__(self, **kwargs):
        default_params = DEFAULTS['depth_map_params']
        focus_stack_params = DEFAULTS['focus_stack_params']
        self.energy_smooth_size = kwargs.get(
            'energy_smooth_size', default_params['energy_smooth_size'])
        self.pyramid_smooth_size = kwargs.get(
            'pyramid_smooth_size', default_params['pyramid_smooth_size'])
        self.weight_power = kwargs.get('weight_power', default_params['weight_power'])
        self.compute_steps_per_frame()
        float_type = kwargs.get('float_type', default_params['float_type'])
        BaseStackAlgo.__init__(self, "depth map", self.steps_per_frame, float_type)
        TempDirBase.__init__(self)
        self.map_type = kwargs.get('map_type', default_params['map_type'])
        self.pyramid_levels = kwargs.get('pyramid_levels', default_params['pyramid_levels'])
        self.energy = kwargs.get('energy', default_params['energy'])
        self.kernel_size = kwargs.get('kernel_size', default_params['kernel_size'])
        if self.kernel_size <= 0 or self.kernel_size % 2 == 0:
            raise InvalidOptionError(
                'blur_size', self.kernel_size, "kernel_size must be a positive odd integer.")
        self.blur_size = kwargs.get('blur_size', default_params['blur_size'])
        if self.blur_size <= 0 or self.blur_size % 2 == 0:
            raise InvalidOptionError(
                'blur_size', self.blur_size, "blur_size must be a positive odd integer.")
        self.energy_sigma_color = kwargs.get(
            'energy_sigma_color', default_params['energy_sigma_color'])
        self.energy_sigma_space = kwargs.get(
            'energy_sigma_space', default_params['energy_sigma_space'])
        self.temperature = kwargs.get('temperature', default_params['temperature'])
        self.mode = kwargs.get('mode', default_params['mode'])
        self.memory_limit = kwargs.get('memory_limit', focus_stack_params['memory_limit'])
        self.steps_count = 0
        self.cv_float = cv2.CV_64F if self.float_type == np.float64 else cv2.CV_32F
        self.plot_depth_map = kwargs.get('plot_depth_map', default_params['plot_depth_map'])

    def get_sobel_map(self, gray_img):
        sobel_energy = np.abs(cv2.Sobel(gray_img, self.cv_float, 1, 0, ksize=3)) + \
            np.abs(cv2.Sobel(gray_img, self.cv_float, 0, 1, ksize=3))
        return sobel_energy.astype(self.float_type)

    def get_laplacian_map(self, gray_img):
        blurred = cv2.GaussianBlur(gray_img, (self.blur_size, self.blur_size), 0)
        lap_result = cv2.Laplacian(blurred, self.cv_float, ksize=self.kernel_size)
        return np.abs(lap_result)

    def get_modified_laplacian(self, gray_img):
        dx = cv2.Sobel(gray_img, self.cv_float, 1, 0, ksize=3)
        dy = cv2.Sobel(gray_img, self.cv_float, 0, 1, ksize=3)
        mod_laplacian = np.abs(dx) + np.abs(dy)
        return mod_laplacian.astype(self.float_type)

    def get_variance_map(self, gray_img, window_size=5):
        mean = cv2.boxFilter(gray_img, -1, (window_size, window_size))
        mean_sq = cv2.boxFilter(gray_img**2, -1, (window_size, window_size))
        return mean_sq - mean**2

    def get_tenengrad(self, gray_img, threshold=5):
        gx = cv2.Sobel(gray_img, self.cv_float, 1, 0, ksize=3)
        gy = cv2.Sobel(gray_img, self.cv_float, 0, 1, ksize=3)
        tenengrad = gx * gx + gy * gy
        return np.where(tenengrad > threshold, tenengrad, 0)

    def smooth_energy(self, energy_map):
        energy_32f = energy_map.astype(np.float32)
        smoothed_32f = cv2.bilateralFilter(
            energy_32f, self.energy_smooth_size,
            self.energy_sigma_color, self.energy_sigma_space)
        return smoothed_32f.astype(energy_map.dtype)

    def get_focus_map(self, energies):
        if self.map_type == constants.DM_MAP_AVERAGE:
            self.print_message(": compute weight")
            sum_energies = np.sum(energies, axis=0, dtype=energies.dtype)
            mask = sum_energies != 0
            weights = np.zeros_like(energies)
            weights[:, mask] = energies[:, mask] / sum_energies[mask]
        elif self.map_type == constants.DM_MAP_MAX:
            max_energy = np.max(energies, axis=0)
            if self.temperature < 1e-4:
                self.print_message(": counting maxima")
                mask = energies == max_energy
                num_max = np.sum(mask, axis=0, dtype=energies.dtype)
                weights = mask / np.where(num_max == 0, 1, num_max)
            else:
                self.print_message(": apply temperature")
                relative = np.exp((energies - max_energy) / self.temperature)
                sum_relative = np.sum(relative, axis=0)
                weights = relative / np.where(sum_relative == 0, 1, sum_relative)
        else:
            raise InvalidOptionError("map_type", self.map_type, details=f" valid values are "
                                     f"{constants.DM_MAP_AVERAGE} and {constants.DM_MAP_MAX}.")
        return weights

    def compute_energy_map(self, gray_img):
        if self.energy == constants.DM_ENERGY_SOBEL:
            return self.get_sobel_map(gray_img)
        if self.energy == constants.DM_ENERGY_LAPLACIAN:
            return self.get_laplacian_map(gray_img)
        if self.energy == constants.DM_ENERGY_MOD_LAPLACIAN:
            return self.get_modified_laplacian(gray_img)
        if self.energy == constants.DM_ENERGY_VARIANCE:
            return self.get_variance_map(gray_img)
        if self.energy == constants.DM_ENERGY_TENENGRAD:
            return self.get_tenengrad(gray_img)
        raise InvalidOptionError(
            'energy', self.energy,
            details=f"Valid values are {constants.DM_ENERGY_SOBEL} and "
                    f"{constants.DM_ENERGY_LAPLACIAN}.")

    def compute_steps_per_frame(self):
        self.steps_per_frame = 2
        if self.energy_smooth_size > 0:
            self.steps_per_frame += 1

    def total_steps(self, n_frames):
        extra_steps = 4 if self.weight_power != 1.0 else 2
        steps = BaseStackAlgo.total_steps(self, n_frames) + extra_steps
        return steps

    def focus_stack(self):
        n_images = len(self.filenames)
        self.process.callback(constants.CALLBACKS_SET_TOTAL_ACTIONS,
                              self.process.output_path, self.output_filename,
                              self.total_steps(n_images))
        energy_memory_gb = (n_images * self.shape[0] * self.shape[1] *
                            np.dtype(self.float_type).itemsize) / (1024**3)
        if self.mode == 'auto':
            use_disk = energy_memory_gb > self.memory_limit
        else:
            use_disk = self.mode == 'i/o'
        if use_disk:
            self.print_message(
                f": using disk-based processing (estimated {energy_memory_gb:.1f} GB)")
            temp_dir = self.temp_dir_path
            energy_files = []
            if self.map_type == constants.DM_MAP_AVERAGE:
                sum_energies = np.zeros(self.shape, dtype=self.float_type)
            else:
                max_energy = np.zeros(self.shape, dtype=self.float_type)
        else:
            self.print_message(
                f": using in-memory processing (estimated {energy_memory_gb:.1f} GB)")
        energies = None if use_disk else np.empty((n_images, *self.shape), dtype=self.float_type)
        step_count = [0]
        for i, img_path in enumerate(self.filenames):
            self.print_message(f": computing energy for {self.image_str(i)}")
            self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                  self.process.input_path, img_path, 200)
            img = read_and_validate_img(img_path, self.shape, self.dtype)
            gray = img_bw(img).astype(self.float_type)
            energy_map = self.compute_energy_map(gray)
            step_count[0] += 1
            self.after_step(step_count[0])
            self.check_running()
            if self.energy_smooth_size > 0:
                self.print_message(f": smoothing energy for {self.image_str(i)}")
                energy_map = self.smooth_energy(energy_map)
                step_count[0] += 1
                self.after_step(step_count[0])
                self.check_running()
            if use_disk:
                temp_file = os.path.join(temp_dir, f"energy_{i:06d}.npy")
                np.save(temp_file, energy_map)
                energy_files.append(temp_file)
                if self.map_type == constants.DM_MAP_AVERAGE:
                    sum_energies += energy_map
                else:
                    max_energy = np.maximum(max_energy, energy_map)
            else:
                energies[i] = energy_map
        self.steps_count += 1
        self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                              self.process.name, self.output_filename,
                              self.steps_count)
        self.print_message(": create focus map")
        step_count[0] += 1
        self.after_step(step_count[0])
        if use_disk:
            if self.map_type == constants.DM_MAP_AVERAGE:
                weights = self.get_focus_map_from_disk_average(energy_files, sum_energies, n_images)
            else:
                weights = self.get_focus_map_from_disk_max(energy_files, max_energy, n_images)
        else:
            weights = self.get_focus_map(energies)
            del energies
        if self.weight_power != 1.0:
            self.print_message(": apply weights power correction")
            weights = np.power(weights, self.weight_power)
            step_count[0] += 1
            self.after_step(step_count[0])
            self.check_running()
            self.print_message(": normalize weights")
            sum_weights = np.sum(weights, axis=0)
            mask = sum_weights != 0
            weights[:, mask] /= sum_weights[mask]
            step_count[0] += 1
            self.after_step(step_count[0])
            self.check_running()
        if self.plot_depth_map:
            self.save_depth_map_plot(weights)
        result = self.weighted_pyramid_blend(weights, step_count)
        self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                              self.process.name, self.output_filename,
                              self.steps_count)
        return result

    def get_focus_map_from_disk_average(self, energy_files, sum_energies, n_images):
        sum_energies = np.where(sum_energies == 0, np.finfo(self.float_type).eps, sum_energies)
        weights = np.empty((n_images, *self.shape), dtype=self.float_type)
        for i, energy_file in enumerate(energy_files):
            self.print_message(f": compute weight, {self.image_str(i)}")
            energy_map = np.load(energy_file)
            weights[i] = energy_map / sum_energies
            self.check_running()
        self.cleanup_temp_files(energy_files)
        return weights

    def get_focus_map_from_disk_max(self, energy_files, max_energy, n_images):
        if self.temperature < 1e-4:
            num_max = np.zeros(self.shape, dtype=self.float_type)
            for i, energy_file in enumerate(energy_files):
                self.print_message(f": counting maxima, {self.image_str(i)}")
                energy_map = np.load(energy_file)
                num_max += (energy_map == max_energy).astype(self.float_type)
                self.check_running()
            weights = np.empty((n_images, *self.shape), dtype=self.float_type)
            for i, energy_file in enumerate(energy_files):
                self.print_message(f": compute weight, {self.image_str(i)}")
                energy_map = np.load(energy_file)
                mask = energy_map == max_energy
                weights[i] = mask / np.where(num_max == 0, self.float_type(1.0), num_max)
                self.check_running()
            self.cleanup_temp_files(energy_files)
            return weights
        sum_relative = np.zeros(self.shape, dtype=self.float_type)
        relative_maps = []
        for i, energy_file in enumerate(energy_files):
            self.print_message(f": apply temperature, {self.image_str(i)}")
            energy_map = np.load(energy_file)
            relative = np.exp((energy_map - max_energy) / self.temperature)
            relative_maps.append(relative)
            sum_relative += relative
            self.check_running()
        sum_relative = np.where(sum_relative == 0, self.float_type(1.0), sum_relative)
        weights = np.empty((n_images, *self.shape), dtype=self.float_type)
        for i, relative in enumerate(relative_maps):
            self.print_message(f": compute weight, {self.image_str(i)}")
            weights[i] = relative / sum_relative
            self.check_running()
        self.cleanup_temp_files(energy_files)
        return weights

    def weighted_pyramid_blend(self, weights, step_count):
        self.print_message(": begin pyramid blending")
        h, w = self.shape[:2]
        pyramid_shapes_f2c = [(h, w)]
        for _ in range(self.pyramid_levels - 1):
            h = (h + 1) // 2
            w = (w + 1) // 2
            pyramid_shapes_f2c.append((h, w))
        pyramid_shapes_c2f = list(reversed(pyramid_shapes_f2c))
        n_ch = 4 if self.alpha_mode else 3
        blended_pyramid = [np.zeros((*shape, n_ch), dtype=self.float_type)
                           for shape in pyramid_shapes_c2f]
        weight_pyramid_accum = [np.zeros(shape, dtype=self.float_type)
                                for shape in pyramid_shapes_c2f]
        temp_laplacian = [np.zeros_like(level_arr) for level_arr in blended_pyramid]
        for i, img_path in enumerate(self.filenames):
            self.print_message(f": pyramid blending {self.image_str(i)}")
            filename = os.path.basename(img_path)
            weight = weights[i]
            if self.pyramid_smooth_size > 0:
                ksize = self.pyramid_smooth_size
                if ksize % 2 == 0:
                    ksize += 1
                weight = cv2.GaussianBlur(weight, (ksize, ksize), 0)
            img = read_img(img_path)
            if img.dtype == np.uint8:
                img_float = img.astype(self.float_type) / 255.0
            elif img.dtype == np.uint16:
                img_float = img.astype(self.float_type) / 65535.0
            else:
                img_float = img.astype(self.float_type)
                if img_float.max() > 1.0:
                    img_float = img_float / self.num_pixel_values
            if self.alpha_mode:
                img_float = img_float.copy()
                img_float[..., :3] *= img_float[..., 3:4]
            gp_weight, lp_img = self._build_pyramids_for_image(img_float, weight)
            for level in range(self.pyramid_levels):
                np.multiply(lp_img[level],
                            gp_weight[self.pyramid_levels - 1 - level][..., np.newaxis],
                            out=temp_laplacian[level])
                blended_pyramid[level] += temp_laplacian[level]
                weight_pyramid_accum[level] += gp_weight[self.pyramid_levels - 1 - level]
            step_count[0] += 1
            self.after_step(step_count[0])
            self.check_running()
            self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                  self.process.input_path, filename, 201)
            self.check_running()
        for level in range(self.pyramid_levels):
            mask = weight_pyramid_accum[level] > 1e-8
            if np.any(mask):
                if len(blended_pyramid[level].shape) == 3:
                    weight_expanded = weight_pyramid_accum[level][:, :, np.newaxis]
                else:
                    weight_expanded = weight_pyramid_accum[level]
                blended_pyramid[level][mask] = blended_pyramid[level][mask] / weight_expanded[mask]
        self.print_message(': reconstructing pyramid')
        result = blended_pyramid[0]
        for level in range(1, self.pyramid_levels):
            size = (blended_pyramid[level].shape[1], blended_pyramid[level].shape[0])
            result = cv2.pyrUp(result, dstsize=size) + blended_pyramid[level]
        if self.alpha_mode:
            alpha = np.clip(result[..., 3:4], 0.0, 1.0)
            floor = 2.0 / 255.0
            color = np.where(alpha > floor, result[..., :3] / np.maximum(alpha, floor), 0.0)
            result = np.concatenate([np.clip(color, 0.0, 1.0), alpha], axis=2)
        if self.dtype == np.uint8:
            result = np.clip(result * 255.0, 0, 255).astype(np.uint8)
        elif self.dtype == np.uint16:
            result = np.clip(result * 65535.0, 0, 65535).astype(np.uint16)
        else:
            result = np.clip(result, 0, 1.0).astype(self.dtype)
        step_count[0] += 1
        self.after_step(step_count[0])
        return result

    def _build_pyramids_for_image(self, img, weight):
        gp_img = [img]
        gp_weight = [weight]
        for level in range(self.pyramid_levels - 1):
            gp_img.append(cv2.pyrDown(gp_img[-1]))
            gp_weight.append(cv2.pyrDown(gp_weight[-1]))
        lp_img = [gp_img[-1]]
        for level in range(self.pyramid_levels - 1, 0, -1):
            size = (gp_img[level - 1].shape[1], gp_img[level - 1].shape[0])
            expanded = cv2.pyrUp(gp_img[level], dstsize=size)
            laplacian = gp_img[level - 1] - expanded
            lp_img.append(laplacian)
        return gp_weight, lp_img

    def cleanup_temp_files(self, energy_files):
        for energy_file in energy_files:
            try:
                os.remove(energy_file)
            except OSError:
                pass
        if self.temp_dir_manager is not None:
            self.temp_dir_manager.cleanup()

    def save_depth_map_plot(self, weights):
        filepath = os.path.join(self.process.working_path, self.process.plot_path,
                                f"{self.process.name}-depth-map.png")
        dirname = os.path.dirname(filepath)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        n_images = weights.shape[0]
        i_max = max(n_images - 1, 1)
        weights_clean = np.nan_to_num(weights, nan=0.0, posinf=0.0, neginf=0.0)
        indices = np.arange(n_images).reshape(-1, 1, 1)
        weighted_sum = np.sum(weights_clean * indices, axis=0)
        sum_weights = np.sum(weights_clean, axis=0)
        depth_map = np.zeros_like(sum_weights)
        mask = sum_weights > 1e-10
        if np.any(mask):
            depth_map[mask] = (weighted_sum[mask] / sum_weights[mask]) / i_max * 255.0
        depth_map = np.nan_to_num(depth_map, nan=0.0, posinf=255.0, neginf=0.0)
        img = np.clip(depth_map, 0, 255).astype(np.uint8)
        self.print_message(": writing depth map")
        write_img(filepath, img)
        self.process.callback(
            constants.CALLBACK_SAVE_PLOT, self.process.id, self.process.output_path,
            "Depth map", filepath, "depthmap")
