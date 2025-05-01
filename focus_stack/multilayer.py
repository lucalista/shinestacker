from focus_stack.stack_framework import FrameMultiDirectory, JobBase
from termcolor import colored
import tifffile
import numpy as np
import imagecodecs
import tifffile
import cv2
from psdtags import (
    PsdBlendMode,
    PsdChannel,
    PsdChannelId,
    PsdClippingType,
    PsdColorSpaceType,
    PsdCompressionType,
    PsdEmpty,
    PsdFilterMask,
    PsdFormat,
    PsdKey,
    PsdLayer,
    PsdLayerFlag,
    PsdLayerMask,
    PsdLayers,
    PsdRectangle,
    PsdString,
    PsdUserMask,
    TiffImageSourceData,
    __version__,
    overlay,
)

class MultiLayer(FrameMultiDirectory, JobBase):
    def __init__(self, name, input_path=None, output_path=None, working_directory=None, reverse_order=False):
        FrameMultiDirectory.__init__(self, name, input_path, output_path, working_directory, 1, reverse_order)
        JobBase.__init__(self, name)
    def run(self):
        print(colored(self.name, "blue", attrs=["bold"]) + ": merging frames in folders: " + ", ".join([i for i in self.input_dir]))
        files = self.folder_filelist()
        in_paths = [self.working_directory + "/" + f for f in files]
        print(colored(self.name, "blue", attrs=["bold"]) + ": frames: " + ", ".join([i.split("/")[-1] for i in files]))
        print(colored(self.name, "blue", attrs=["bold"]) + ": reading files")
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
        transp = np.full_like(images[0][..., 0], 65535)
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
        ) for i, image in enumerate (images)]
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
        filename = ".".join(files[-1].split("/")[-1].split(".")[:-1])
        print(colored(self.name, "blue", attrs=["bold"]) + ": writing multilayer tiff " + self.output_path + '/' + filename + '.tif')
        tifffile.imwrite(self.working_directory + '/' + self.output_path + '/' + filename + '.tif',
            overlay(*((np.concatenate((image, np.expand_dims(transp, axis=-1)), axis=-1), (0, 0)) for image in images),
                shape=shape,
            ),
            photometric='rgb',
            compression='adobe_deflate',
            resolution=((720000, 10000), (720000, 10000)),
            resolutionunit='inch',
            metadata=None,
            extratags=[
                image_source_data.tifftag(maxworkers=4),
                (34675, 7, None, imagecodecs.cms_profile('srgb'), True),
            ],
        )