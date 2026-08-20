# pylint: disable=C0114, C0115, C0116, R0913, R0917, W0718, R0902, R0912, R0914, R0915, R1702
import os
import traceback
import logging
import numpy as np
from ..config.constants import constants
from ..config.defaults import DEFAULTS
from ..core.framework import TaskBase
from ..core.colors import color_str
from ..core.exceptions import InvalidOptionError
from .utils import (
    read_img, write_img, extension_supported_input, get_output_filename, extension_raw)
from .stack_framework import ImageSequenceManager, SequentialTask
from .exif import copy_exif_from_file_to_file
from .denoise import denoise
from .sharpen import unsharp_mask


class FocusStackBase(TaskBase, ImageSequenceManager):
    def __init__(self, name, stack_algo, defaults_key, enabled=True, apply_postifx=False, **kwargs):
        ImageSequenceManager.__init__(self, name, **kwargs)
        TaskBase.__init__(self, name, enabled)
        common_params = DEFAULTS["focus_stack_params"]
        specific_params = DEFAULTS[defaults_key]
        self.apply_postifx = apply_postifx
        self.stack_algo = stack_algo
        self.exif_path = kwargs.pop("exif_path", "")
        self.naming_mode = kwargs.pop("naming_mode", specific_params.get("naming_mode", "PREFIX"))
        
        prefix_provided = "prefix" in kwargs and kwargs.get("prefix", "") != ""
        template_provided = "output_file_template" in kwargs and kwargs.get("output_file_template", "") != ""

        self.prefix = kwargs.pop("prefix", specific_params.get("prefix", ""))
        self.output_file_template = kwargs.pop("output_file_template",
                                               specific_params.get("output_file_template", ""))

        if prefix_provided and template_provided:
            raise ValueError(
                "Cannot specify both 'prefix' and 'output_file_template'. "
                "Use 'naming_mode' to choose between 'PREFIX' and 'TEMPLATE'."
            )
        
        self.denoise_amount = kwargs.pop("denoise_amount", common_params["denoise_amount"])
        self.sharpen_amount = (
            kwargs.pop("sharpen_amount_percent", common_params["sharpen_amount_percent"])
            / 100.0
        )
        self.sharpen_radius = kwargs.pop("sharpen_radius", common_params["sharpen_radius"])
        self.sharpen_threshold = kwargs.pop("sharpen_threshold", common_params["sharpen_threshold"])
        self.plot_stack = kwargs.pop("plot_stack", common_params["plot_stack"])
        self.stack_algo.set_process(self)
        self.plot_path = kwargs.pop("plot_path", DEFAULTS["image_sequence_manager"]["plots_path"])
        self.frame_count = -1
        self.bunch_index = None

    def replace_template_placeholders(self, filename):
        method_name = self.stack_algo.algo_name()
        filename = filename.replace("{method}", method_name)
        filename = filename.replace("{input_count}", str(len(self.input_filepaths())))
        common_prefix, _, identifiers = extract_frame_identifiers(self.input_filepaths())
        if identifiers:
            filename = filename.replace("{input_prefix}", common_prefix)
            filename = filename.replace("{input_min}", identifiers[0])
            filename = filename.replace("{input_max}", identifiers[-1])
        return filename

    def resolve_output_filename(self, base_filename):
        if self.naming_mode == 'TEMPLATE':
            filename = self.replace_template_placeholders(self.output_file_template)
            _, ext = os.path.splitext(base_filename)
            return filename + ext
        filename = self.prefix + base_filename
        if self.apply_postifx:
            filename = self.add_postfix(filename)
        return filename

    def add_postfix(self, filename):
        if self.apply_postifx:
            algo_class = self.stack_algo.__class__.__name__
            postfix = ""
            if algo_class.startswith("Pyramid"):
                postfix = "_pyram"
            elif algo_class.startswith("DepthMap"):
                postfix = "_depmp"
            root, ext = os.path.splitext(filename)
            return root + postfix + ext
        return filename

    def focus_stack(self, filenames):
        self.sub_message_r(
            color_str(": reading input files", constants.LOG_COLOR_LEVEL_3)
        )
        input_filename = os.path.basename(filenames[0])
        base_output = get_output_filename(input_filename)
        resolved_filename = self.resolve_output_filename(base_output)
        output_filename = os.path.join(self.output_full_path(), resolved_filename)
        filename = os.path.basename(output_filename)
        self.callback(constants.CALLBACK_UPDATE_FRAME_STATUS, self.name, filename, 0)
        n_frames = len(filenames)
        if n_frames > 1:
            self.sub_message_r(
                color_str(
                    f": focus stacking: blending {n_frames} frames",
                    constants.LOG_COLOR_LEVEL_3,
                )
            )
            self.stack_algo.set_output_filename(filename)
            stacked_img = self.stack_algo.focus_stack()
        else:
            self.sub_message_r(
                color_str(
                    ": focus stack made of a single file, skip blending",
                    constants.LOG_COLOR_LEVEL_3,
                )
            )
            stacked_img = read_img(filenames[0])
        if self.denoise_amount > 0.0:
            self.sub_message_r(
                color_str(": denoise image", constants.LOG_COLOR_LEVEL_3)
            )
            stacked_img = denoise(stacked_img, self.denoise_amount)
        if self.sharpen_amount > 0.0:
            self.sub_message_r(
                color_str(": sharpen image", constants.LOG_COLOR_LEVEL_3)
            )
            stacked_img = unsharp_mask(
                stacked_img,
                self.sharpen_amount,
                self.sharpen_radius,
                self.sharpen_threshold,
            )
        write_img(output_filename, stacked_img)
        if self.exif_path != "":
            if (
                stacked_img.dtype == np.uint16
                and os.path.splitext(output_filename)[-1].lower() == ".png"
            ):
                self.sub_message_r(
                    color_str(
                        ": exif not supported for 16-bit PNG format",
                        constants.LOG_COLOR_WARNING,
                    ),
                    level=logging.WARNING,
                )
            else:
                self.sub_message_r(
                    color_str(": copy exif data", constants.LOG_COLOR_LEVEL_3)
                )
                if not os.path.exists(self.exif_path):
                    raise RuntimeError(f"path {self.exif_path} does not exist.")
                try:
                    _dirpath, _, fnames = next(os.walk(self.exif_path))
                    fnames = sorted(
                        [name for name in fnames if extension_supported_input(name)]
                    )
                    if len(fnames) == 0:
                        raise RuntimeError(
                            f"path {self.exif_path} does not contain image files."
                        )

                    # Try to match the extension of the first input file
                    input_ext = os.path.splitext(filenames[0])[1].lower()
                    exif_filename_only = fnames[0]
                    for name in fnames:
                        if os.path.splitext(name)[1].lower() == input_ext:
                            exif_filename_only = name
                            break
                    else:
                        # Fallback: prefer non-RAW files (JPG/TIFF/PNG) over RAW
                        for name in fnames:
                            if not extension_raw(name):
                                exif_filename_only = name
                                break

                    exif_filename = os.path.join(self.exif_path, exif_filename_only)
                    copy_exif_from_file_to_file(exif_filename, output_filename)
                    self.sub_message_r(" " * 60)
                except Exception as e:
                    traceback.print_exc()
                    self.sub_message_r(
                        color_str(
                            f": failed to copy EXIF data: {str(e)}",
                            constants.LOG_COLOR_WARNING,
                        ),
                        level=logging.WARNING,
                    )
        self.callback(constants.CALLBACK_UPDATE_FRAME_STATUS, self.name, filename, 1000)
        if self.plot_stack:
            idx_str = f"{self.frame_count + 1:04d}" if self.frame_count >= 0 else ""
            caption = f"{self.name}: {self.stack_algo.algo_name()}"
            if idx_str != "":
                caption += f"\nbunch: {idx_str}"
            self.callback(
                constants.CALLBACK_SAVE_PLOT,
                self.id,
                self.output_path,
                caption,
                output_filename,
            )
        if self.frame_count >= 0:
            self.frame_count += 1

    def init(self, job, working_path=""):
        if working_path == "":
            working_path = job.working_path
        ImageSequenceManager.init(self, job)
        if self.exif_path is None:
            self.exif_path = job.action_path(0)
        if self.exif_path != "":
            self.exif_path = os.path.join(working_path, self.exif_path)

    def end_job(self):
        ImageSequenceManager.end_job(self)


def get_bunches(collection, n_frames, n_overlap):
    if n_frames == n_overlap:
        raise RuntimeError(
            f"Can't get bunch collection, total number of frames ({n_frames}) "
            "is equal to the number of overlapping grames"
        )
    if len(collection) < n_frames:
        return [collection]
    bunches = [
        collection[x: x + n_frames]
        for x in range(0, len(collection) - n_overlap, n_frames - n_overlap)
    ]
    return bunches


def extract_frame_identifiers(filenames):
    if not filenames:
        return "", "", []
    basenames = [os.path.basename(f) for f in filenames]
    if len(basenames) == 1:
        return "", "", [basenames[0]]
    common_prefix = os.path.commonprefix(basenames)
    common_suffix = os.path.commonprefix([s[::-1] for s in basenames])[::-1]
    identifiers = []
    for name in basenames:
        if common_prefix and common_suffix:
            middle = name[len(common_prefix):]
            if middle.endswith(common_suffix):
                middle = middle[:-len(common_suffix)]
            identifiers.append(middle)
        elif common_prefix:
            identifiers.append(name[len(common_prefix):])
        elif common_suffix:
            identifiers.append(name[:-len(common_suffix)])
        else:
            identifiers.append(name)
    return common_prefix, common_suffix, identifiers


class FocusStackBunch(SequentialTask, FocusStackBase):
    def __init__(self, name, stack_algo, enabled=True, **kwargs):
        bunch_defaults = DEFAULTS["focus_stack_bunch_params"]
        SequentialTask.__init__(self, name, enabled)
        FocusStackBase.__init__(self, name, stack_algo, "focus_stack_bunch_params",
                                enabled, False, **kwargs)
        self._chunks = None
        self.frame_count = 0
        self.frames = kwargs.get("frames", bunch_defaults["frames"])
        self.overlap = kwargs.get("overlap", bunch_defaults["overlap"])
        self.denoise_amount = kwargs.get("denoise_amount", 0)
        self.stack_algo.set_do_step_callback(False)
        if self.overlap >= self.frames:
            raise InvalidOptionError(
                "overlap", self.overlap, "overlap must be smaller than batch size"
            )

    def sequential_processing(self):
        return True

    def init(self, job, _working_path=""):
        FocusStackBase.init(self, job, self.working_path)

    def begin(self):
        SequentialTask.begin(self)
        self._chunks = get_bunches(
            sorted(self.input_filepaths()), self.frames, self.overlap
        )
        self.callback(constants.CALLBACK_ADD_STATUS_BOX, self.output_path)
        for idx, chunk in enumerate(self._chunks):
            self.bunch_index = idx + 1
            filename = chunk[0]
            base_filename = os.path.basename(filename)
            resolved_filename = self.resolve_output_filename(base_filename)
            self.callback(constants.CALLBACK_ADD_FRAME, self.output_path, resolved_filename, 1)
        self.set_counts(len(self._chunks))

    def end(self):
        SequentialTask.end(self)

    def end_job(self):
        FocusStackBase.end_job(self)

    def run_step(self, action_count=-1):
        self.print_message(
            color_str(
                f"fusing bunch {action_count + 1}/{self.total_action_counts}",
                constants.LOG_COLOR_LEVEL_2,
            )
        )
        img_files = self._chunks[action_count]
        self.bunch_index = action_count + 1
        base_filename = os.path.basename(img_files[0])
        resolved_filename = self.resolve_output_filename(base_filename)
        self.stack_algo.init(img_files)
        self.focus_stack(self._chunks[action_count])
        self.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                      self.output_path, resolved_filename, 1000)
        return True

    def resolve_output_filename(self, base_filename):
        if self.naming_mode == 'TEMPLATE':
            filename = self.replace_template_placeholders(self.output_file_template)
            if hasattr(self, 'bunch_index') and self.bunch_index is not None:
                filename = filename.replace("{bunch_index:03d}", f"{self.bunch_index:03d}")
            _, ext = os.path.splitext(base_filename)
            return filename + ext
        filename = self.prefix + base_filename
        if self.apply_postifx:
            filename = self.add_postfix(filename)
        return filename


class FocusStack(FocusStackBase):
    def __init__(self, name, stack_algo, enabled=True, **kwargs):
        super().__init__(name, stack_algo, "focus_stack_params", enabled, True, **kwargs)
        self.stack_algo.set_do_step_callback(True)
        self.shape = None

    def run_core(self):
        self.set_filelist()
        img_files = sorted(self.input_filepaths())
        self.stack_algo.init(img_files)
        self.callback(
            "step_counts",
            self.id,
            self.name,
            self.stack_algo.total_steps(self.num_input_filepaths()),
        )
        self.callback(constants.CALLBACK_ADD_STATUS_BOX, self.output_path)
        filename = img_files[0]
        file_path = self.output_full_path()
        base_filename = os.path.basename(filename)
        resolved_filename = self.resolve_output_filename(base_filename)
        filename = os.path.join(file_path, resolved_filename)
        self.callback(constants.CALLBACK_ADD_FRAME, self.output_path, filename, 1)
        self.focus_stack(img_files)
        return True

    def init(self, job, _working_path=""):
        FocusStackBase.init(self, job, self.working_path)

    def end_job(self):
        FocusStackBase.end_job(self)
