import sys
import re


class _Constants:
    APP_TITLE = "Shine Stacker"
    APP_STRING = "ShineStacker"
    EXTENSIONS = set(["jpeg", "jpg", "png", "tif", "tiff"])

    NUM_UINT8 = 256
    NUM_UINT16 = 65536
    MAX_UINT8 = 255
    MAX_UINT16 = 65535

    LOG_FONTS = ['Monaco', 'Menlo', ' Lucida Console', 'Courier New', 'Courier', 'monospace']
    LOG_FONTS_STR = ", ".join(LOG_FONTS)

    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    ACTION_JOB = "Job"
    ACTION_COMBO = "CombinedActions"
    ACTION_NOISEDETECTION = "NoiseDetection"
    ACTION_FOCUSSTACK = "FocusStack"
    ACTION_FOCUSSTACKBUNCH = "FocusStackBunch"
    ACTION_MULTILAYER = "MultiLayer"
    ACTION_TYPES = [ACTION_COMBO, ACTION_FOCUSSTACKBUNCH, ACTION_FOCUSSTACK,
                    ACTION_MULTILAYER, ACTION_NOISEDETECTION]
    COMPOSITE_TYPES = [ACTION_COMBO]
    ACTION_MASKNOISE = "MaskNoise"
    ACTION_VIGNETTING = "Vignetting"
    ACTION_ALIGNFRAMES = "AlignFrames"
    ACTION_BALANCEFRAMES = "BalanceFrames"
    SUB_ACTION_TYPES = [ACTION_MASKNOISE, ACTION_VIGNETTING, ACTION_ALIGNFRAMES,
                        ACTION_BALANCEFRAMES]
    STACK_ALGO_PYRAMID = 'Pyramid'
    STACK_ALGO_DEPTH_MAP = 'Depth map'
    STACK_ALGO_OPTIONS = [STACK_ALGO_PYRAMID, STACK_ALGO_DEPTH_MAP]
    STACK_ALGO_DEFAULT = STACK_ALGO_PYRAMID
    DEFAULT_PLOTS_PATH = 'plots'

    PATH_SEPARATOR = ';'

    DEFAULT_FILE_REVERSE_ORDER = False
    DEFAULT_MULTILAYER_FILE_REVERSE_ORDER = True

    DEFAULT_NOISE_MAP_FILENAME = "noise-map/hot_pixels.png"
    DEFAULT_MN_KERNEL_SIZE = 3
    INTERPOLATE_MEAN = 'MEAN'
    INTERPOLATE_MEDIAN = 'MEDIAN'
    RGB_LABELS = ['r', 'g', 'b']
    RGBA_LABELS = ['r', 'g', 'b', 'a']
    DEFAULT_CHANNEL_THRESHOLDS = [13, 13, 13]
    DEFAULT_BLUR_SIZE = 5
    DEFAULT_NOISE_PLOT_RANGE = [5, 30]
    VALID_INTERPOLATE = {INTERPOLATE_MEAN, INTERPOLATE_MEDIAN}

    ALIGN_HOMOGRAPHY = "ALIGN_HOMOGRAPHY"
    ALIGN_RIGID = "ALIGN_RIGID"
    BORDER_CONSTANT = "BORDER_CONSTANT"
    BORDER_REPLICATE = "BORDER_REPLICATE"
    BORDER_REPLICATE_BLUR = "BORDER_REPLICATE_BLUR"
    DETECTOR_SIFT = "SIFT"
    DETECTOR_ORB = "ORB"
    DETECTOR_SURF = "SURF"
    DETECTOR_AKAZE = "AKAZE"
    DETECTOR_BRISK = "BRISK"
    DESCRIPTOR_SIFT = "SIFT"
    DESCRIPTOR_ORB = "ORB"
    DESCRIPTOR_AKAZE = "AKAZE"
    DESCRIPTOR_BRISK = "BRISK"
    MATCHING_KNN = "KNN"
    MATCHING_NORM_HAMMING = "NORM_HAMMING"
    ALIGN_RANSAC = "RANSAC"
    ALIGN_LMEDS = "LMEDS"

    VALID_DETECTORS = [DETECTOR_SIFT, DETECTOR_ORB, DETECTOR_SURF, DETECTOR_AKAZE, DETECTOR_BRISK]
    VALID_DESCRIPTORS = [DESCRIPTOR_SIFT, DESCRIPTOR_ORB, DESCRIPTOR_AKAZE, DESCRIPTOR_BRISK]
    VALID_MATCHING_METHODS = [MATCHING_KNN, MATCHING_NORM_HAMMING]
    VALID_TRANSFORMS = [ALIGN_RIGID, ALIGN_HOMOGRAPHY]
    VALID_BORDER_MODES = [BORDER_CONSTANT, BORDER_REPLICATE, BORDER_REPLICATE_BLUR]
    VALID_ALIGN_METHODS = [ALIGN_RANSAC, ALIGN_LMEDS]
    NOKNN_METHODS = {'detectors': [DETECTOR_ORB, DETECTOR_SURF, DETECTOR_AKAZE, DETECTOR_BRISK],
                     'descriptors': [DESCRIPTOR_ORB, DESCRIPTOR_AKAZE, DESCRIPTOR_BRISK]}

    DEFAULT_DETECTOR = DETECTOR_SIFT
    DEFAULT_DESCRIPTOR = DESCRIPTOR_SIFT
    DEFAULT_MATCHING_METHOD = MATCHING_KNN
    DEFAULT_FLANN_IDX_KDTREE = 2
    DEFAULT_FLANN_TREES = 5
    DEFAULT_FLANN_CHECKS = 50
    DEFAULT_ALIGN_THRESHOLD = 0.75
    DEFAULT_TRANSFORM = ALIGN_RIGID
    DEFAULT_BORDER_MODE = BORDER_REPLICATE_BLUR
    DEFAULT_ALIGN_METHOD = 'RANSAC'
    DEFAULT_RANS_THRESHOLD = 3.0  # px
    DEFAULT_REFINE_ITERS = 100
    DEFAULT_ALIGN_CONFIDENCE = 99.9
    DEFAULT_ALIGN_MAX_ITERS = 2000
    DEFAULT_BORDER_VALUE = [0] * 4
    DEFAULT_BORDER_BLUR = 50
    DEFAULT_ALIGN_SUBSAMPLE = 1
    DEFAULT_ALIGN_FAST_SUBSAMPLING = False

    BALANCE_LINEAR = "LINEAR"
    BALANCE_GAMMA = "GAMMA"
    BALANCE_MATCH_HIST = "MATCH_HIST"
    VALID_BALANCE = [BALANCE_LINEAR, BALANCE_GAMMA, BALANCE_MATCH_HIST]

    BALANCE_LUMI = "LUMI"
    BALANCE_RGB = "RGB"
    BALANCE_HSV = "HSV"
    BALANCE_HLS = "HLS"
    VALID_BALANCE_CHANNELS = [BALANCE_LUMI, BALANCE_RGB, BALANCE_HSV, BALANCE_HLS]

    DEFAULT_BALANCE_SUBSAMPLE = 8
    DEFAULT_CORR_MAP = BALANCE_LINEAR
    DEFAULT_CHANNEL = BALANCE_LUMI
    DEFAULT_INTENSITY_INTERVAL = {'min': 0, 'max': -1}

    DEFAULT_R_STEPS = 100
    DEFAULT_BLACK_THRESHOLD = 1
    DEFAULT_MAX_CORRECTION = 1

    FLOAT_32 = 'float-32'
    FLOAT_64 = 'float-64'
    VALID_FLOATS = [FLOAT_32, FLOAT_64]

    DEFAULT_FRAMES = 10
    DEFAULT_OVERLAP = 2
    DEFAULT_STACK_PREFIX = "stack_"
    DEFAULT_BUNCH_PREFIX = "bunch_"

    DEFAULT_DM_FLOAT = FLOAT_32
    DM_ENERGY_LAPLACIAN = "laplacian"
    DM_ENERGY_SOBEL = "sobel"
    DM_MAP_AVERAGE = "average"
    DM_MAP_MAX = "max"
    VALID_DM_MAP = [DM_MAP_AVERAGE, DM_MAP_MAX]
    VALID_DM_ENERGY = [DM_ENERGY_LAPLACIAN, DM_ENERGY_SOBEL]
    DEFAULT_DM_MAP = DM_MAP_AVERAGE
    DEFAULT_DM_ENERGY = DM_ENERGY_LAPLACIAN
    DEFAULT_DM_KERNEL_SIZE = 5
    DEFAULT_DM_BLUR_SIZE = 5
    DEFAULT_DM_SMOOTH_SIZE = 15
    DEFAULT_DM_TEMPERATURE = 0.1
    DEFAULT_DM_LEVELS = 3

    DEFAULT_PY_FLOAT = FLOAT_32
    DEFAULT_PY_MIN_SIZE = 32
    DEFAULT_PY_KERNEL_SIZE = 5
    DEFAULT_PY_GEN_KERNEL = 0.4

    DEFAULT_PLOT_STACK_BUNCH = False
    DEFAULT_PLOT_STACK = True

    STATUS_RUNNING = 1
    STATUS_PAUSED = 2
    STATUS_STOPPED = 3

    RUN_COMPLETED = 0
    RUN_ONGOING = 1
    RUN_FAILED = 2
    RUN_STOPPED = 3

    def __setattr__aux(self, name, value):
        raise AttributeError(f"Can't reassign constant '{name}'")

    def __init__(self):
        self.PYTHON_APP = sys.executable
        self.RETOUCH_APP = "shinestacker-retouch"
        _Constants.__setattr__ = _Constants.__setattr__aux


constants = _Constants()
