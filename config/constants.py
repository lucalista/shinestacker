class _Constants:
    DEFAULT_NOISE_MAP_FILENAME = "noise-map/hot_pixels.png"
    DEFAULT_MN_KERNEL_SIZE = 3
    INTERPOLATE_MEAN = 'MEAN'
    INTERPOLATE_MEDIAN = 'MEDIAN'
    RGB_LABELS = ['r', 'g', 'b']
    DEFAULT_CHANNEL_THRESHOLDS = [13, 13, 13]
    DEFAULT_BLUR_SIZE = 5
    DEFAULT_NOISE_PLOT_RANGE = [5, 30]
    VALID_INTERPOLATE = {INTERPOLATE_MEAN, INTERPOLATE_MEDIAN}

    def __setattr__(self, name, value):
        raise AttributeError(f"Can't reassign constant '{name}'")


constants = _Constants()
