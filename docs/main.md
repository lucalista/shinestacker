# Focus Stacking Processing Framework

<img src='../img/flies.gif' width="400">  <img src='../img/flies_stack.jpg' width="400">

## Quick Start
```python
from focus_stack import *

job = StackJob("demo", "/path/to/images", input_path="src")
job.add_action(CombinedActions("align", [AlignFrames()]))
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
job.add_action(CombinedActions("align",
			       [MaskNoise(),Vignetting(), AlignFrames(),
                                BalanceFrames(mask_size=0.9,
                                              intensity_interval={'min': 150, 'max': 65385})]))
job.add_action(FocusStackBunch("batches", PyramidStack(), frames=10, overlap=2, denoise=0.8))
job.add_action(FocusStack("stack", PyramidStack(), postfix='_pyramid', denoise=0.8))
job.add_action(FocusStack("stack", DepthMapStack(), input_path='batches', postfix='_depthmap', denoise=0.8))
job.add_action(MultiLayer("multilayer", input_path=['batches', 'stack']))
job.run()
```

## Graphical User Interface

A GUI is also available, still experimental and undocumented.
To run the GUI, from the main package directory run:

```console
python -m gui.main
```

## Documentation
- [Job creation and processing pipeline](../docs/job.md)
- [Image alignment](../docs/alignment.md)
- [Luminosity and color balancing](../docs/balancing.md)
- [Stacking algorithms](../docs/focus_stacking.md)
- [Multilayer image](../docs/multilayer.md)
- [Noisy pixel masking](../docs/noise.md)
- [Vignetting correction](../docs/vignetting.md)

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

## Installation
You can clone the pagkage from GitHub:

```bash
pip install git+https://github.com/lucalista/focusstack.git
```
## Issues

* ```BALANCE_HSV``` and ```BALANCE_HLS``` are only supported for 8-bit images
* Focus stacking modules crashes for TIFF files if  ```denoise``` is set different from zero due to an assertion failure in the Open CV library. This is similar to a [known issue on stackoverflow](https://stackoverflow.com/questions/76647895/opencv-fastnlmeansdenoisingmulti-should-support-16-bit-images-but-does-it).
* PNG files have not been tested so far.
