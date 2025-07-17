from termcolor import colored
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
from focusstack.config.constants import constants
from focusstack.config.config import config
from focusstack.core.framework import JobBase
from focusstack.algorithms.stack_framework import FrameMultiDirectory
from focusstack.algorithms.exif import exif_extra_tags_for_tif, get_exif


def read_multilayer_tiff(input_file):
    return TiffImageSourceData.fromtiff(input_file)


def write_multilayer_tiff(input_files, output_file, labels=None, exif_path='', callbacks=None):
    extensions = list(set([file.split(".")[-1] for file in input_files]))
    if len(extensions) > 1:
        msg = ", ".join(extensions)
        raise Exception(f"All input files must have the same extension. Input list has the following extensions: {msg}.")
    extension = extensions[0]
    if extension == 'tif' or extension == 'tiff':
        images = [tifffile.imread(p) for p in input_files]
    elif extension == 'jpg' or extension == 'jpeg':
        images = [cv2.imread(p) for p in input_files]
        images = [cv2.cvtColor(i, cv2.COLOR_BGR2RGB) for i in images]
    elif extension == 'png':
        images = [cv2.imread(p, cv2.IMREAD_UNCHANGED) for p in input_files]
        images = [cv2.cvtColor(i, cv2.COLOR_BGR2RGB) for i in images]
    if labels is None:
        image_dict = {file.split('/')[-1].split('.')[0]: image for file, image in zip(input_files, images)}
    else:
        if len(labels) != len(input_files):
            raise Exception("input_files and labels must have the same length if labels are provided.")
        image_dict = {label: image for label, image in zip(labels, images)}
    write_multilayer_tiff_from_images(image_dict, output_file, exif_path=exif_path, callbacks=callbacks)


def write_multilayer_tiff_from_images(image_dict, output_file, exif_path='', callbacks=None):
    if isinstance(image_dict, (list, tuple, np.ndarray)):
        fmt = 'Layer {:03d}'
        image_dict = {fmt.format(i + 1): img for i, img in enumerate(image_dict)}
    shapes = list(set([image.shape[:2] for image in image_dict.values()]))
    if len(shapes) > 1:
        raise Exception("All input files must have the same dimensions.")
    shape = shapes[0]
    dtypes = list(set([image.dtype for image in image_dict.values()]))
    if len(dtypes) > 1:
        raise Exception("All input files must all have 8 bit or 16 bit depth.")
    dtype = dtypes[0]
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
        dirpath, _, fnames = next(os.walk(exif_path))
        fnames = [name for name in fnames if os.path.splitext(name)[-1][1:].lower() in constants.EXTENSIONS]
        exif_filename = exif_path + '/' + fnames[0]
        extra_tags, exif_tags = exif_extra_tags_for_tif(get_exif(exif_filename))
        tiff_tags['extratags'] += extra_tags
        tiff_tags = {**tiff_tags, **exif_tags}
    if callbacks:
        callback = callbacks.get('write_msg', None)
        if callback:
            callback(output_file.split('/')[-1])
    compression = 'adobe_deflate'
    overlayed_images = overlay(*((np.concatenate((image, np.expand_dims(transp, axis=-1)), axis=-1), (0, 0)) for image in image_dict.values()), shape=shape)
    tifffile.imwrite(output_file, overlayed_images, compression=compression, metadata=None, **tiff_tags)


class MultiLayer(FrameMultiDirectory, JobBase):
    def __init__(self, name, enabled=True, **kwargs):
        FrameMultiDirectory.__init__(self, name, **kwargs)
        JobBase.__init__(self, name, enabled)
        self.exif_path = kwargs.get('exif_path', '')
        self.reverse_order = kwargs.get('reverse_order', constants.DEFAULT_MULTILAYER_FILE_REVERSE_ORDER)

    def init(self, job):
        FrameMultiDirectory.init(self, job)
        if self.exif_path == '':
            self.exif_path = job.paths[0]
        if self.exif_path != '':
            self.exif_path = self.working_path + "/" + self.exif_path

    def run_core(self):
        if isinstance(self.input_full_path, str):
            paths = [self.input_path]
        elif hasattr(self.input_full_path, "__len__"):
            paths = self.input_path
        else:
            raise Exception("input_path option must contain a path or an array of paths")
        if len(paths) == 0:
            self.print_message(colored("no input paths specified", "red"), level=logging.WARNING)
            return
        files = self.folder_filelist()
        if len(files) == 0:
            self.print_message(colored("no input in {} specified path{}: ".format(len(paths),
                                                                                  's' if len(paths) > 1 else '') + ", ".join([f"'{p}'" for p in paths]),
                                       "red"), level=logging.WARNING)
            return
        self.print_message(colored("merging frames in " + self.folder_list_str(), "blue"))
        input_files = [f"{self.working_path}/{f}" for f in files]
        self.print_message(colored("frames: " + ", ".join([i.split("/")[-1] for i in files]), "blue"))
        self.print_message(colored("reading files", "blue"))
        filename = ".".join(files[0].split("/")[-1].split(".")[:-1])
        output_file = f"{self.working_path}/{self.output_path}/{filename}.tif"
        callbacks = {
            'exif_msg': lambda path: self.print_message(colored(f"copying exif data from path: {path}", "blue")),
            'write_msg': lambda path: self.print_message(colored(f"writing multilayer tiff file: {path}", "blue"))
        }
        write_multilayer_tiff(input_files, output_file, labels=None, exif_path=self.exif_path, callbacks=callbacks)
        if config.COMBINED_APP:
            self.callback('open_app', self.id, self.name, 'internal_retouch_app', output_file)
        else:
            self.callback('open_app', self.id, self.name, f'{constants.RETOUCH_APP}', output_file)
