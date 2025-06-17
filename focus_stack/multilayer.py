from focus_stack.stack_framework import FrameMultiDirectory, JobBase
from focus_stack.exif import exif_extra_tags, get_exif
from termcolor import colored
import tifffile
import numpy as np
import imagecodecs
import cv2
import os
import logging
from psdtags import (PsdBlendMode, PsdChannel, PsdChannelId, PsdClippingType, PsdColorSpaceType,
                     PsdCompressionType, PsdEmpty, PsdFilterMask, PsdFormat, PsdKey, PsdLayer,
                     PsdLayerFlag, PsdLayerMask, PsdLayers, PsdRectangle, PsdString, PsdUserMask,
                     TiffImageSourceData, overlay)

EXTENSIONS = set(["jpeg", "jpg", "png", "tif", "tiff"])


class MultiLayer(FrameMultiDirectory, JobBase):
    def __init__(self, name, enabled=True, exif_path='', **kwargs):
        FrameMultiDirectory.__init__(self, name, **kwargs)
        JobBase.__init__(self, name, enabled)
        self.exif_path = exif_path

    def init(self, job):
        FrameMultiDirectory.init(self, job)
        if self.exif_path is None:
            self.exif_path = job.paths[0]
        if self.exif_path != '':
            self.exif_path = self.working_path + "/" + self.exif_path

    def run_core(self):
        if isinstance(self.input_dir, str):
            paths = [self.input_path]
        elif hasattr(self.input_dir, "__len__"):
            paths = self.input_path
        else:
            raise Exception("input_dir option must contain a path or an array of paths")
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
        in_paths = [self.working_path + "/" + f for f in files]
        self.print_message(colored("frames: " + ", ".join([i.split("/")[-1] for i in files]), "blue"))
        self.print_message(colored("reading files", "blue"))
        extension = files[0].split(".")[-1]
        if extension == 'tif' or extension == 'tiff':
            images = [tifffile.imread(p) for p in in_paths]
        elif extension == 'jpg' or extension == 'jpeg':
            images = [cv2.imread(p) for p in in_paths]
            images = [cv2.cvtColor(i, cv2.COLOR_BGR2RGB) for i in images]
        elif extension == 'png':
            images = [cv2.imread(p, cv2.IMREAD_UNCHANGED) for p in in_paths]
            images = [cv2.cvtColor(i, cv2.COLOR_BGR2RGB) for i in images]
        shape = images[0].shape[:2]
        dtype = images[0].dtype
        transp = np.full_like(images[0][..., 0], 65535 if dtype == np.uint16 else 255)
        fmt = 'Layer {:03d}'
        layers = [PsdLayer(
            name=fmt.format(i + 1),
            rectangle=PsdRectangle(0, 0, *shape),
            channels=[
                PsdChannel(
                    channelid=PsdChannelId.TRANSPARENCY_MASK,
                    compression=PsdCompressionType.ZIP_PREDICTED,
                    data=transp,
                ),
                PsdChannel(
                    channelid=PsdChannelId.CHANNEL0,
                    compression=PsdCompressionType.ZIP_PREDICTED,
                    data=image[..., 0],
                ),
                PsdChannel(
                    channelid=PsdChannelId.CHANNEL1,
                    compression=PsdCompressionType.ZIP_PREDICTED,
                    data=image[..., 1],
                ),
                PsdChannel(
                    channelid=PsdChannelId.CHANNEL2,
                    compression=PsdCompressionType.ZIP_PREDICTED,
                    data=image[..., 2],
                ),
            ],
            mask=PsdLayerMask(), opacity=255,
            blendmode=PsdBlendMode.NORMAL, blending_ranges=(),
            clipping=PsdClippingType.BASE, flags=PsdLayerFlag.PHOTOSHOP5,
            info=[PsdString(PsdKey.UNICODE_LAYER_NAME, fmt.format(i + 1))],
        ) for i, image in enumerate(images)]
        image_source_data = TiffImageSourceData(
            name='Layered TIFF',
            psdformat=PsdFormat.LE32BIT,
            layers=PsdLayers(
                key=PsdKey.LAYER,
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
        if self.exif_path != '':
            self.print_message(colored('copying exif data', 'blue'))
            dirpath, _, fnames = next(os.walk(self.exif_path))
            fnames = [name for name in fnames if os.path.splitext(name)[-1][1:].lower() in EXTENSIONS]
            exif_filename = self.exif_path + '/' + fnames[0]
            extra_tags, exif_tags = exif_extra_tags(get_exif(exif_filename))
            tiff_tags['extratags'] += extra_tags
            tiff_tags = {**tiff_tags, **exif_tags}
        filename = ".".join(files[-1].split("/")[-1].split(".")[:-1])
        self.print_message(colored("writing multilayer tiff " + self.output_path + '/' + filename + '.tif', "blue"))
        tifffile.imwrite(
            self.working_path + '/' + self.output_path + '/' + filename + '.tif',
            overlay(*((np.concatenate((image, np.expand_dims(transp, axis=-1)), axis=-1), (0, 0)) for image in images),
                    shape=shape),
            compression='adobe_deflate',
            metadata=None, **tiff_tags)
