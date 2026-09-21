# Shine Stacker
[![CI multiplatform](https://github.com/lucalista/shinestacker/actions/workflows/ci-multiplatform.yml/badge.svg)](https://github.com/lucalista/shinestacker/actions/workflows/ci-multiplatform.yml)
[![PyPI version](https://img.shields.io/pypi/v/shinestacker?color=success)](https://pypi.org/project/shinestacker/)
[![Python Versions](https://img.shields.io/pypi/pyversions/shinestacker)](https://pypi.org/project/shinestacker/)
[![Qt Versions](https://img.shields.io/badge/Qt-6-blue.svg?&logo=Qt&logoWidth=18&logoColor=white)](https://www.qt.io/qt-for-python)
[![pylint](https://img.shields.io/badge/PyLint-10.00-brightgreen?logo=python&logoColor=white)](https://github.com/lucalista/shinestacker/blob/main/.github/workflows/pylint.yml)
[![codecov](https://codecov.io/github/lucalista/shinestacker/graph/badge.svg?token=Y5NKW6VH5G)](https://codecov.io/github/lucalista/shinestacker)
[![Documentation Status](https://readthedocs.org/projects/shinestacker/badge/?version=latest)](https://shinestacker.readthedocs.io/en/latest/?badge=latest)
 [![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![PyPI Downloads](https://static.pepy.tech/badge/shinestacker)](https://pepy.tech/projects/shinestacker)

<center><img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/src/shinestacker/gui/ico/shinestacker.png' width="150" referrerpolicy="no-referrer" alt="Shine Stacker Logo"></center>

**Shine Stacker** is a focus stacking application that combines multiple images taken at different focus distances to produce images with extended depth of field. It provides an interactive GUI and a Python API for advanced image processing workflows in macro photography and microscopy. 👉 [Learn more about focus stacking on Wikipedia](https://en.wikipedia.org/wiki/Focus_stacking).

Shine Stacker provides multiple stacking algorithms and gives users detailed control over image alignment, normalization, fusion, and retouching. It can be used interactively through the GUI or programmatically through its Python API.

## Key Features

- 🪟 **Cross-Platform GUI:** Native app built with Qt6, available for Windows, macOS, and Linux.
- 🔬 **Multiple Stacking Algorithms:** Pyramid-based and depth-map methods with configurable processing options.
- 🚀 **Batch Processing:** Automatically align, balance, and stack hundreds of images — suitable for macro or microscopy datasets.
- 🎨 **Image Processing:** Automatic image alignment, colour balancing, noise and vignetting correction, and other processing options.
- 🧩 **Modular Architecture:** Combine configurable modules for alignment, normalization, and blending to build custom workflows.
- 🖌️ **Retouch Editor:** Interactively refine your stacked image by painting in details from individual frames and applying filters.
- 📊 **Jupyter & Python Integration:** Use Shine Stacker as a library inside your Python or Jupyter workflows.
- 🎞️ **Supported Formats:** TIFF 8–16 bits, PNG 8–16 bits, JPEG, including transparency layer, and most RAW formats via [`rawpy`](https://github.com/letmaik/rawpy).

## Interactive GUI

The graphical interface provides an integrated workflow for configuring, running, and refining focus stacks:

- **Project View** – Configure, preview, and run stacking workflows with optional intermediate results.
- **Retouch View** – Manually refine the final image by blending details from selected frames and applying filters.

Ideal for users who want the power of scripting and the convenience of an interactive GUI.

## See Shine Stacker in Action

[![Shine Stacker demo](https://img.youtube.com/vi/Ut5tJw63_HU/maxresdefault.jpg)](https://www.youtube.com/watch?v=Ut5tJw63_HU)

A short demonstration of the interactive project and retouching interface.

## Who is Shine Stacker for?

Shine Stacker is designed for photographers, microscopists, and researchers who need precise control over focus stacking and reproducible image-processing workflows.

<img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/flies.gif' width="400" referrerpolicy="no-referrer">  <img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/flies_stack.jpg' width="400" referrerpolicy="no-referrer">

<img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/coffee.gif' width="400" referrerpolicy="no-referrer">  <img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/coffee_stack.jpg' width="400" referrerpolicy="no-referrer">

## Get Started

- 📦 [Install via PyPI](https://pypi.org/project/shinestacker/)
- 💻 [Run the GUI](https://shinestacker.readthedocs.io/)
- 🧠 [Python API reference](https://shinestacker.readthedocs.io/)
- 🐛 [Report an issue](https://github.com/lucalista/shinestacker/issues)

## Resources

🌍 [Website](https://shinestacker.wordpress.com/) • 📖 [Documentation](https://shinestacker.readthedocs.io/) • 📝 [Changelog](https://github.com/lucalista/shinestacker/blob/main/CHANGELOG.md) • 💬 [Community & reviews](https://shinestacker.wordpress.com/community/)

## Installation

See the [main documentation](https://github.com/lucalista/shinestacker/blob/main/docs/main.md) for detailed installation instructions.

**Platform notes:**

- **Windows:** If you download the installer or ZIP archive, you may need to whitelist the app in your antivirus software.
- **macOS:** See the [installation note for macOS users](https://github.com/lucalista/shinestacker/blob/main/docs/macos-install.md).

## Acknowledgements & References

The first version of the core focus stack algorithm was inspired by the 
[Laplacian pyramids method](https://github.com/sjawhar/focus-stacking) implementation 
by Sami Jawhar, used under permission. The implementation in the latest releases 
was rewritten from the original code.

Key references:
* [Pyramid Methods in Image Processing](https://www.researchgate.net/publication/246727904_Pyramid_Methods_in_Image_Processing), E. H. Adelson, C. H. Anderson,  J. R. Bergen, P. J. Burt, J. M. Ogden, RCA Engineer, 29-6, Nov/Dec 1984
Pyramid methods in image processing
* [A Multi-focus Image Fusion Method Based on Laplacian Pyramid](http://www.jcomputers.us/vol6/jcp0612-07.pdf), Wencheng Wang, Faliang Chang, Journal of Computers 6 (12), 2559, December 2011

## License

<img src="https://www.gnu.org/graphics/lgplv3-147x51.png" alt="LGPL 3 logo">

- **Code**: The software is provided as is under the [GNU Lesser General Public License v3.0](https://www.gnu.org/licenses/lgpl-3.0.en.html). See [LICENSE](https://github.com/lucalista/shinestacker/blob/main/LICENSE) for details.

- **Logo**: The Shine Stacker logo was designed by [Alessandro Lista](https://linktr.ee/alelista). Copyright © Alessandro Lista. All rights reserved. The logo is not covered by the LGPL-3.0 license of this project.

## Attribution request

📸 If you publish images created with Shine Stacker, please consider adding a note such as:

*Created with Shine Stacker – https://github.com/lucalista/shinestacker*

This is not mandatory, but highly appreciated.

---
> Developed and maintained by [Luca Lista](https://github.com/lucalista).
> 💡 Contributions, feedback, and feature suggestions are warmly welcome.
> If you enjoy Shine Stacker, consider giving it a ⭐️ on GitHub — it really helps visibility!
