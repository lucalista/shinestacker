# pylint: disable=C0114, C0115, C0116, E1101, R0914, E0606, R0912
import os
import logging
import cv2
import tifffile
import imagecodecs
import numpy as np
from psdtags import (PsdBlendMode, PsdChannel, PsdChannelId, PsdClippingType, PsdColorSpaceType,
                     PsdCompressionType, PsdEmpty, PsdFilterMask, PsdFormat, PsdKey, PsdLayer,
                     PsdLayerFlag, PsdLayerMask, PsdLayers, PsdRectangle, PsdString, PsdUserMask,
                     TiffImageSourceData, overlay)
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. core.colors import color_str
from .. core.framework import TaskBase
from .utils import (
    EXTENSIONS_TIF, EXTENSIONS_JPG, EXTENSIONS_PNG, EXTENSIONS_RAW, EXTENSIONS_SUPPORTED_IN)
from .stack_framework import ImageSequenceManager
from .exif import exif_extra_tags_for_tif, get_exif


def read_multilayer_tiff(input_file):
    return TiffImageSourceData.fromtiff(input_file)


def write_multilayer_tiff(input_files, output_file, labels=None, exif_path='', callbacks=None):
    extensions = list({file.split(".")[-1] for file in input_files})
    if len(extensions) > 1:
        msg = ", ".join(extensions)
        raise RuntimeError("All input files must have the same extension. "
                           f"Input list has the following extensions: {msg}.")
    extension = extensions[0].lower()
    if extension in EXTENSIONS_RAW:
        raise RuntimeError("RAW image formats not yet supported.")
    if extension in EXTENSIONS_TIF:
        images = [tifffile.imread(p) for p in input_files]
    elif extension in EXTENSIONS_JPG:
        images = [cv2.imread(p) for p in input_files]
        images = [cv2.cvtColor(i, cv2.COLOR_BGR2RGB) for i in images]
    elif extension in EXTENSIONS_PNG:
        images = [cv2.imread(p, cv2.IMREAD_UNCHANGED) for p in input_files]
        images = [cv2.cvtColor(i, cv2.COLOR_BGR2RGB) for i in images]
    if labels is None:
        image_dict = {file.split('/')[-1].split('.')[0]: image
                      for file, image in zip(input_files, images)}
    else:
        if len(labels) != len(input_files):
            raise RuntimeError("input_files and labels "
                               "must have the same length if labels are provided.")
        image_dict = dict(zip(labels, images))
    write_multilayer_tiff_from_images(image_dict, output_file,
                                      exif_path=exif_path, callbacks=callbacks)


def write_multilayer_tiff_from_images(image_dict, output_file, exif_path='', callbacks=None):
    if isinstance(image_dict, (list, tuple, np.ndarray)):
        fmt = 'Layer {:03d}'
        image_dict = {fmt.format(i + 1): img for i, img in enumerate(image_dict)}
    shapes = list({image.shape[:2] for image in image_dict.values()})
    if len(shapes) > 1:
        raise RuntimeError("All input files must have the same dimensions.")
    shape = shapes[0]
    dtypes = list({image.dtype for image in image_dict.values()})
    if len(dtypes) > 1:
        raise RuntimeError("All input files must all have 8 bit or 16 bit depth.")
    dtype = dtypes[0]
    bytes_per_pixel = 3 * np.dtype(dtype).itemsize
    est_memory = shape[0] * shape[1] * bytes_per_pixel * len(image_dict)
    if est_memory > constants.MULTILAYER_WARNING_MEM_GB * constants.ONE_GIGA:
        if callbacks:
            callback = callbacks.get('memory_warning', None)
            if callback:
                callback(float(est_memory) / constants.ONE_GIGA)
    max_pixel_value = constants.MAX_UINT16 if dtype == np.uint16 else constants.MAX_UINT8
    transp = np.full_like(list(image_dict.values())[0][..., 0], max_pixel_value)
    compression_type = PsdCompressionType.ZIP_PREDICTED
    psdformat = PsdFormat.LE32BIT
    key = PsdKey.LAYER_16 if dtype == np.uint16 else PsdKey.LAYER
    layers = [PsdLayer(
        name=label,
        rectangle=PsdRectangle(0, 0, *shape),
        channels=[
            PsdChannel(
                channelid=PsdChannelId.TRANSPARENCY_MASK,
                compression=compression_type,
                data=transp,
            ),
            PsdChannel(
                channelid=PsdChannelId.CHANNEL0,
                compression=compression_type,
                data=image[..., 0],
            ),
            PsdChannel(
                channelid=PsdChannelId.CHANNEL1,
                compression=compression_type,
                data=image[..., 1],
            ),
            PsdChannel(
                channelid=PsdChannelId.CHANNEL2,
                compression=compression_type,
                data=image[..., 2],
            ),
        ],
        mask=PsdLayerMask(), opacity=255,
        blendmode=PsdBlendMode.NORMAL, blending_ranges=(),
        clipping=PsdClippingType.BASE, flags=PsdLayerFlag.PHOTOSHOP5,
        info=[PsdString(PsdKey.UNICODE_LAYER_NAME, label)],
    ) for label, image in reversed(list(image_dict.items()))]
    image_source_data = TiffImageSourceData(
        name='Layered TIFF',
        psdformat=psdformat,
        layers=PsdLayers(
            key=key,
            has_transparency=False,
            layers=layers,
        ),
        usermask=PsdUserMask(
            colorspace=PsdColorSpaceType.RGB,
            components=(65535, 0, 0, 0),
            opacity=50,
        ),
        info=[
            PsdEmpty(PsdKey.PATTERNS),
            PsdFilterMask(
                colorspace=PsdColorSpaceType.RGB,
                components=(65535, 0, 0, 0),
                opacity=50,
            ),
        ],
    )
    tiff_tags = {
        'photometric': 'rgb',
        'resolution': ((720000, 10000), (720000, 10000)),
        'resolutionunit': 'inch',
        'extratags': [image_source_data.tifftag(maxworkers=4),
                      (34675, 7, None, imagecodecs.cms_profile('srgb'), True)]
    }
    if exif_path != '':
        if callbacks:
            callback = callbacks.get('exif_msg', None)
            if callback:
                callback(exif_path)
        if os.path.isfile(exif_path):
            extra_tags, exif_tags = exif_extra_tags_for_tif(get_exif(exif_path))
        elif os.path.isdir(exif_path):
            _dirpath, _, fnames = next(os.walk(exif_path))
            fnames = [name for name in fnames
                      if os.path.splitext(name)[-1][1:].lower() in EXTENSIONS_SUPPORTED_IN]
            file_path = os.path.join(exif_path, fnames[0])
            extra_tags, exif_tags = exif_extra_tags_for_tif(get_exif(file_path))
        extra_tags = [tag for tag in extra_tags if isinstance(tag[0], int)]
        tiff_tags['extratags'] += extra_tags
        tiff_tags = {**tiff_tags, **exif_tags}
    if callbacks:
        callback = callbacks.get('write_msg', None)
        if callback:
            callback(os.path.basename(output_file))
    compression = 'adobe_deflate'
    overlayed_images = overlay(
        *((np.concatenate((image, np.expand_dims(transp, axis=-1)),
          axis=-1), (0, 0)) for image in image_dict.values()), shape=shape
    )
    tifffile.imwrite(output_file, overlayed_images,
                     compression=compression, metadata=None, **tiff_tags)


class MultiLayer(TaskBase, ImageSequenceManager):
    def __init__(self, name, enabled=True, **kwargs):
        ImageSequenceManager.__init__(self, name, **kwargs)
        TaskBase.__init__(self, name, enabled)
        self.exif_path = kwargs.get('exif_path', '')
        self.reverse_order = kwargs.get(
            'reverse_order', DEFAULTS['multilayer_params']['file_reverse_order'])

    def init(self, job):
        ImageSequenceManager.init(self, job)
        if self.exif_path == '':
            self.exif_path = job.action_path(0)
        if self.exif_path != '':
            self.exif_path = os.path.join(self.working_path, self.exif_path)

    def run_core(self):
        if isinstance(self.input_full_path(), str):
            paths = [self.input_path]
        elif hasattr(self.input_full_path(), "__len__"):
            paths = self.input_path
        else:
            raise RuntimeError("input_path option must contain a path or an array of paths")
        if len(paths) == 0:
            self.print_message(color_str("no input paths specified",
                                         constants.LOG_COLOR_ALERT),
                               level=logging.WARNING)
            return False
        input_files = self.input_filepaths()
        if len(input_files) == 0:
            self.print_message(
                color_str(f"no input in {len(paths)} specified path" +
                          ('s' if len(paths) > 1 else '') + ": "
                          ", ".join([f"'{p}'" for p in paths]),
                          constants.LOG_COLOR_ALERT),
                level=logging.WARNING)
            return False
        self.print_message(color_str("merging frames in " + self.folder_list_str(),
                           constants.LOG_COLOR_LEVEL_2))
        self.print_message(
            color_str("frames: " + ", ".join([os.path.basename(i) for i in input_files]),
                      constants.LOG_COLOR_LEVEL_2))
        self.print_message(color_str("reading files", constants.LOG_COLOR_LEVEL_2))
        filename = ".".join(os.path.basename(input_files[0]).split(".")[:-1])
        output_file = f"{self.working_path}/{self.output_path}/{filename}.tif"
        callbacks = {
            'exif_msg': lambda path: self.print_message(
                color_str(f"copying exif data from path: {path}", constants.LOG_COLOR_LEVEL_2)),
            'write_msg': lambda path: self.print_message(
                color_str(f"writing multilayer tiff file: {path}", constants.LOG_COLOR_LEVEL_2)),
            'memory_warning': lambda mem: self.print_message(
                color_str(f"warning: estimated file size: {mem:.2f} GBytes",
                          constants.LOG_COLOR_WARNING))
        }
        write_multilayer_tiff(input_files, output_file, labels=None, exif_path=self.exif_path,
                              callbacks=callbacks)
        self.callback(constants.CALLBACK_OPEN_APP, self.id, self.name, output_file)
        return True
