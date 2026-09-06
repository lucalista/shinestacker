# pylint: disable=C0114, C0115, C0116, E1101, R0913, R0902, R0914, R0917
import os
import logging
import numpy as np
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. core.exceptions import RunStopException
from .. core.colors import color_str
from .base_stack_algo import BaseStackAlgo
from .pyramid import PyramidStack
from .pyramid_tiles import PyramidTilesStack


class PyramidAutoStack(BaseStackAlgo):
    supports_alpha = True

    def __init__(self, **kwargs):
        pyramid_default_params = DEFAULTS['pyramid_params']
        focus_stack_defaults_params = DEFAULTS['focus_stack_params']
        self.float_type_opt = kwargs.get('float_type', pyramid_default_params['float_type'])
        super().__init__("auto_pyramid", 1, self.float_type_opt)
        self.mode = kwargs.get('mode', pyramid_default_params['mode'])
        self.min_size = kwargs.get('min_size', pyramid_default_params['min_size'])
        self.kernel_size = kwargs.get('kernel_size', pyramid_default_params['kernel_size'])
        self.gen_kernel = kwargs.get('gen_kernel', pyramid_default_params['gen_kernel'])
        self.tile_size = kwargs.get('tile_size', pyramid_default_params['tile_size'])
        self.n_tiled_layers = kwargs.get('n_tiled_layers', pyramid_default_params['n_tiled_layers'])
        self.memory_limit = kwargs.get(
            'memory_limit', focus_stack_defaults_params['memory_limit']) * constants.ONE_GIGA
        max_threads = kwargs.get(
            'max_threads', focus_stack_defaults_params['max_threads'])
        available_cores = os.cpu_count() or 1
        self.num_threads = min(max_threads, available_cores)
        self.max_tile_size = kwargs.get('max_tile_size', pyramid_default_params['max_tile_size'])
        self.min_tile_size = kwargs.get('min_tile_size', pyramid_default_params['min_tile_size'])
        self.min_n_tiled_layers = kwargs.get(
            'min_n_tiled_layers', pyramid_default_params['min_n_tiled_layers'])
        self._implementation = None
        self.dtype = None
        self.shape = None
        self.n_levels = None
        self.n_frames = 0
        self.channels = 3  # r, g, b
        self.bytes_per_pixel = self.channels * np.dtype(self.float_type).itemsize
        self.overhead = constants.PY_MEMORY_OVERHEAD

    def init(self, filenames):
        super().init(filenames)
        if self.alpha_mode:
            self.channels = 4
            self.bytes_per_pixel = self.channels * np.dtype(self.float_type).itemsize
        self.n_levels = int(np.log2(min(self.shape) / self.min_size))
        self.n_frames = len(filenames)
        memory_required_memory = self._estimate_memory_memory()
        if self.mode == 'memory' or (self.mode == 'auto' and
                                     memory_required_memory <= self.memory_limit):
            self._implementation = PyramidStack(
                min_size=self.min_size,
                kernel_size=self.kernel_size,
                gen_kernel=self.gen_kernel,
                float_type=self.float_type_opt
            )
            self.print_message(": using memory-based pyramid stacking")
        else:
            optimal_params = self._find_optimal_tile_params()
            self._implementation = PyramidTilesStack(
                min_size=self.min_size,
                kernel_size=self.kernel_size,
                gen_kernel=self.gen_kernel,
                float_type=self.float_type_opt,
                tile_size=optimal_params['tile_size'],
                n_tiled_layers=optimal_params['n_tiled_layers'],
                max_threads=self.num_threads
            )
            self.print_message(f": using tile-based pyramid stacking, "
                               f"tile size: {optimal_params['tile_size']}, "
                               f"n. tiled layers: {optimal_params['n_tiled_layers']}, "
                               f"{self.num_threads} cores.")
        self.init_implementation(self._implementation)

    def init_implementation(self, impl):
        impl.init(self.filenames)
        impl.set_do_step_callback(self.do_step_callback)
        if self.process is not None:
            impl.set_process(self.process)
        else:
            raise RuntimeError("self.process must be initialized.")

    def _estimate_memory_memory(self):
        h, w = self.shape[:2]
        total_memory = 0
        for _ in range(self.n_levels):
            total_memory += h * w * self.bytes_per_pixel
            h, w = max(1, h // 2), max(1, w // 2)
        return self.overhead * total_memory * self.n_frames

    def _find_optimal_tile_params(self):
        h, w = self.shape[:2]
        base_level_memory = h * w * self.bytes_per_pixel
        available_memory = self.memory_limit - base_level_memory
        available_memory /= self.overhead
        tile_size_max = int(np.sqrt(available_memory /
                            (self.num_threads * self.n_frames * self.bytes_per_pixel)))
        tile_size = min(self.max_tile_size, tile_size_max, self.shape[0], self.shape[1])
        tile_size = max(self.min_tile_size, tile_size)
        n_tiled_layers = 0
        for layer in range(self.n_levels):
            h_layer = max(1, self.shape[0] // (2 ** layer))
            w_layer = max(1, self.shape[1] // (2 ** layer))
            if h_layer > tile_size or w_layer > tile_size:
                n_tiled_layers = layer + 1
            else:
                break
        n_tiled_layers = max(n_tiled_layers, self.min_n_tiled_layers)
        n_tiled_layers = min(n_tiled_layers, self.n_levels)
        return {'tile_size': tile_size, 'n_tiled_layers': n_tiled_layers}

    def set_output_filename(self, filename):
        self._implementation.set_output_filename(filename)

    def set_process(self, process):
        super().set_process(process)
        if self._implementation is not None:
            self._implementation.set_process(process)

    def total_steps(self, n_frames):
        if self._implementation is None:
            return super().total_steps(n_frames)
        return self._implementation.total_steps(n_frames)

    def focus_stack(self):
        if self._implementation is None:
            raise RuntimeError("PyramidAutoStack not initialized")
        try:
            return self._implementation.focus_stack()
        except RunStopException:
            self.print_message(
                color_str(": reverting to sequential processing", constants.LOG_COLOR_WARNING),
                level=logging.WARNING
            )
            self._implementation = PyramidStack(
                min_size=self.min_size,
                kernel_size=self.kernel_size,
                gen_kernel=self.gen_kernel,
                float_type=self.float_type_opt
            )
            self.init_implementation(self._implementation)
            return self._implementation.focus_stack()

    def after_step(self, step):
        if self._implementation is not None:
            self._implementation.after_step(step)
        else:
            super().after_step(step)

    def check_running(self, cleanup_callback=None):
        if self._implementation is not None:
            self._implementation.check_running(cleanup_callback)
        else:
            super().check_running(cleanup_callback)
