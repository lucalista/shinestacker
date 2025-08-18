# pylint: disable=C0114, C0115, C0116, E0602, R0903
import numpy as np
from .. core.exceptions import InvalidOptionError, ImageLoadError
from .. config.constants import constants
from .. core.colors import color_str
from .utils import read_img, get_img_metadata, validate_image


class BaseStackAlgo:
    def __init__(self, name, steps_per_frame, float_type=constants.DEFAULT_PY_FLOAT):
        self._name = name
        self._steps_per_frame = steps_per_frame
        self.process = None
        if float_type == constants.FLOAT_32:
            self.float_type = np.float32
        elif float_type == constants.FLOAT_64:
            self.float_type = np.float64
        else:
            raise InvalidOptionError(
                "float_type", float_type,
                details=" valid values are FLOAT_32 and FLOAT_64"
            )

    def name(self):
        return self._name

    def steps_per_frame(self):
        return self._steps_per_frame

    def print_message(self, msg):
        self.process.sub_message_r(color_str(msg, constants.LOG_COLOR_LEVEL_3))

    def read_image_and_update_metadata(self, img_path, metadata):
        img = read_img(img_path)
        if img is None:
            raise ImageLoadError(img_path)
        updated = metadata is None
        if updated:
            metadata = get_img_metadata(img)
        else:
            validate_image(img, *metadata)
        return img, metadata, updated
