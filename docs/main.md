# Shine Stacker

## Focus Stacking Processing Framework and GUI

<img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/flies.gif' width="400" referrerpolicy="no-referrer">  <img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/flies_stack.jpg' width="400" referrerpolicy="no-referrer">

<img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/coffee.gif' width="400" referrerpolicy="no-referrer">  <img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/coffee_stack.jpg' width="400" referrerpolicy="no-referrer">

> **Focus stacking** for microscopy, macro photography, and computational imaging

## Key Features
- 🚀 **Batch Processing**: Align, balance, and stack hundreds of images
- 🧩 **Modular Architecture**: Mix-and-match processing modules
- 🖌️ **Retouch Editing**: Final interactive retouch of stacked image from individual frames
- 📊 **Jupyter Integration**: Image processing python notebooks


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
git clone https://github.com/lucalista/shinestacker.git
cd shinestacker
pip install -e .
```

## GUI Workflow
Launch GUI

```bash
shinestacker
```

Follow [GUI guide](gui.md) for batch processing and retouching.


## Advanced Processing Pipeline

```python
from shinestacker import *

job = StackJob("job", "E:/focus_stacking/project_directory/", input_path="tiff_images")
job.add_action(CombinedActions("align", actions=[AlignFrames(), BalanceFrames()]))
job.add_action(FocusStackBunch("batches", PyramidStack(), frames=12, overlap=2))
job.add_action(FocusStack("stack", PyramidStack(), prefix='pyram_'))
job.add_action(FocusStack("stack", DepthMapStack(), prefix='dmap_'))
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
