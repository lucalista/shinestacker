# Focus Stacking Processing Framework

[![CI multiplatform](https://github.com/lucalista/focusstack/actions/workflows/ci-multiplatform.yml/badge.svg)](https://github.com/lucalista/focusstack/actions/workflows/ci-multiplatform.yml)

<img src='../img/flies.gif' width="400">  <img src='../img/flies_stack.jpg' width="400">

> **Professional focus stacking** for microscopy, macro photography, and computational imaging

## Key Features
- 🚀 **Batch Processing**: Align, balance, and stack hundreds of images
- 🎨 **Hybrid Workflows**: Combine Python scripting with GUI refinement
- 🧩 **Modular Architecture**: Mix-and-match processing modules
- 🖌️ **Non-Destructive Editing**: Save multilayer TIFFs for retouching
- 📊 **Jupyter Integration**: Reproducible research notebooks


## Quick start
### Command Line Processing
```python
from focusstack.algorithms import *

# Minimal workflow: Alignment → Stacking
job = StackJob("demo", "/path/to/images", input_path="src")
job.add_action(CombinedActions("align", [AlignFrames()]))
job.add_action(FocusStack("result", PyramidStack()))
job.run()
```

## Installation
Clone the pagkage from GitHub:

```bash
git clone https://github.com/lucalista/focusstack.git
cd focusstack
pip install -e .
```

## GUI Workflow
Launch GUI

```bash
focusstack
```

Follow [GUI guide](gui.md) for batch processing and retouching.


## Advanced Processing Pipeline

```python
from focusstack.algorithms import *

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

## Workflow Options

| Method            | Best For         |
|-------------------|------------------|
| Python API        | batch processing | 
| GUI Interactive   | refinement       |
| Jupyter notebooks | prototyping      |

## Documentation Highlights
### Core Processing
- [Graphical User Interface](../docs/gui.md)
- [Image alignment](../docs/alignment.md)
- [Luminosity and color balancing](../docs/balancing.md)
- [Stacking algorithms](../docs/focus_stacking.md)
### Advanced Modules
- [Noisy pixel masking](../docs/noise.md)
- [Vignetting correction](../docs/vignetting.md)
- [Multilayer image](../docs/multilayer.md)

## Requirements

* Python: 3.12 (3.13 may not work due to garbage collection issues)
* RAM: 16GB+ recommended for >15 images

## Dependencies

### Core processing
```bash
pip install imagecodecs matplotlib numpy opencv-python pillow psdtags scipy setuptools-scm termcolor tifffile tqdm
```
# GUI support
```bash
pip install argparse PySide6 jsonpickle webbrowser
```

# Jupyter support
```bash
pip install ipywidgets
```

## Known Issues

| Issue    |  Workaround    |
|----------|----------------|
| Balance modes ```HSV```/```HLS``` fail with 16-bit images | convert to 8-bit or use ```RGB``` or luminosity |
|  ```denoise>0``` crashes with TIFFs (see [here](https://stackoverflow.com/questions/76647895/opencv-fastnlmeansdenoisingmulti-should-support-16-bit-images-but-does-it)) | set ```denoise=0```or use JPEG sources
| PNG support untested  | Convert to TIFF/JPEG first |
| GUI tests limited     | Report bugs as GitHub issuse |
