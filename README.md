# Focus Stacking Processing Framework

<img src='img/flies.gif' width="400">  <img src='img/flies_stack.jpg' width="400">

## Quick Start
```python
from focus_stack import *
job = StackJob("demo", "/path/to/images", input_path="src")
job.add_action(Actions("align", actions=[AlignFrames()]))
job.add_action(FocusStack("result", PyramidStack()))
job.run()
```

## Usage example

```python
from focus_stack import *

job = StackJob("job", "E:/Focus stacking/My image directory/", input_path="src")
job.add_action(NoiseDetection())
job.run()

job = StackJob("job", "E:/Focus stacking/My image directory/", input_path="src")
job.add_action(Actions("align",
                       actions=[MaskNoise(), Vignetting(), AlignFrames(),
                                BalanceFrames(mask_size=0.9,
                                              intensity_interval={'min': 150, 'max': 65385})]))
job.add_action(FocusStackBunch("batches", PyramidStack(), frames=10, overlap=2, denoise=0.8))
job.add_action(FocusStack("stack", PyramidStack(), postfix='_py', denoise=0.8))
job.add_action(FocusStack("stack", DepthMapStack(), input_path='batches', postfix='_dm', denoise=0.8))
job.add_action(MultiLayer("multilayer", input_path=['batches', 'stack']))
job.run()
```

## Documentation
- [Job creation and processing pipeline](docs/job.md)
- [Image alignment](docs/alignment.md)
- [Luminosity and color balancing](docs/balancing.md)
- [Vignetting correction](docs/vignetting.md)
- [Stacking algorithms](docs/focus_stacking.md)
- [Multilayer image](docs/multilayer.md)
- [Noisy pixel masking](docs/noise.md)

## Requirements

* python version 3.10 or greater

The following python modules:
* open cv (opencv-python)
* numpy
* scipy
* matplotlib
* termcolor
* tqdm
* PIL (pillow)
* tifffile
* imagecodecs
* psdtags
* 
## Installation
You can clone the pagkage from GitHub:

```bash
pip install git+https://github.com/lucalista/focusstack.git
```

### Credits:

based on [Laplacian pyramids method](https://github.com/sjawhar/focus-stacking) implementation by Sami Jawhar. The original code was used under permission of the author.

**Resources:**

* [Pyramid Methods in Image Processing](https://www.researchgate.net/publication/246727904_Pyramid_Methods_in_Image_Processing), E. H. Adelson, C. H. Anderson,  J. R. Bergen, P. J. Burt, J. M. Ogden, RCA Engineer, 29-6, Nov/Dec 1984
Pyramid methods in image processing
* [A Multi-focus Image Fusion Method Based on Laplacian Pyramid](http://www.jcomputers.us/vol6/jcp0612-07.pdf), Wencheng Wang, Faliang Chang, Journal of Computers 6 (12), 2559, December 2011
* Another [original implementation on GitHub](https://github.com/bznick98/Focus_Stacking) by Zongnan Bao

## Issues

PNG files have not been tested so far.

The support of TIFF, in particular 16-bit images, is still partial:
* ```BALANCE_HSV``` and ```BALANCE_HLS``` are only supported for 8-bit images
* Even if ```exif_path``` is explicitly specified, for 16-bit TIFF exif data for the moment are not be saved because of incomplete support of EXIF data for TIFF files.
* Focus stacking modules crashes for TIFF files if  ```denoise``` is set ifferent from zero due to an assertion failure in the Open CV library. This is similar to a [known issue on stackoverflow](https://stackoverflow.com/questions/76647895/opencv-fastnlmeansdenoisingmulti-should-support-16-bit-images-but-does-it).

## License

The software is provided as is under the [GNU Lesser General Public License v3.0](https://choosealicense.com/licenses/lgpl-3.0/).

