# Shine Stacker

## Focus Stacking Processing Framework and GUI

<img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/flies.gif' width="400" referrerpolicy="no-referrer">  <img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/flies_stack.jpg' width="400" referrerpolicy="no-referrer">

<img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/coffee.gif' width="400" referrerpolicy="no-referrer">  <img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/coffee_stack.jpg' width="400" referrerpolicy="no-referrer">

<img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/coins.gif' width="400" referrerpolicy="no-referrer">  <img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/coins_stack.jpg' width="400" referrerpolicy="no-referrer">

> **Focus stacking** for microscopy, macro photography, and computational imaging

## Key Features
- 🚀 **Batch Processing**: Align, balance, and stack hundreds of images
- 🎨 **Hybrid Workflows**: Combine Python scripting with GUI refinement
- 🧩 **Modular Architecture**: Mix-and-match processing modules
- 🖌️ **Non-Destructive Editing**: Save multilayer TIFFs for retouching
- 📊 **Jupyter Integration**: Reproducible research notebooks


## Quick start
### Command Line Processing
```python
from shinestacker.algorithms import *

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
from shinestacker.algorithms import *

job = StackJob("job", "E:/Focus stacking/My image directory/", input_path="src")
job.add_action(NoiseDetection())
job.run()

job = StackJob("job", "E:/Focus stacking/My image directory/", input_path="src")
job.add_action(CombinedActions("align",
			       [MaskNoise(),Vignetting(), AlignFrames(),
                                BalanceFrames(mask_size=0.9,
                                              intensity_interval={'min': 150, 'max': 65385})]))
job.add_action(FocusStackBunch("bunches", PyramidStack(), frames=10, overlap=2, denoise=0.8))
job.add_action(FocusStack("stack", PyramidStack(), prefix='pyramid_', denoise=0.8))
job.add_action(FocusStack("stack", DepthMapStack(), input_path='batches', prefix='depthmap_', denoise=0.8))
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
- [Graphical User Interface](gui.md)
- [Image alignment](alignment.md)
- [Luminosity and color balancing](balancing.md)
- [Stacking algorithms](focus_stacking.md)
### Advanced Modules
- [Noisy pixel masking](noise.md)
- [Vignetting correction](vignetting.md)
- [Multilayer image](multilayer.md)

## Requirements

* Python: 3.12 (3.13 may not work due to garbage collection issues)
* RAM: 16GB+ recommended for >15 images at 20Mpx resolution

## Dependencies

### Core processing
```bash
pip install imagecodecs matplotlib numpy opencv-python pillow psdtags scipy setuptools-scm tifffile tqdm
```
## GUI support
```bash
pip install argparse PySide6 jsonpickle webbrowser
```

## Jupyter support
```bash
pip install ipywidgets
```

## Known Issues

| Issue    |  Workaround    |
|----------|----------------|
| Balance modes ```HSV```/```HLS``` don't support 16-bit images | convert to 8-bit or use ```RGB``` or luminosity |
| PNG support untested  | Convert to TIFF/JPEG first |
| GUI tests limited     | Report bugs as GitHub issuse |
