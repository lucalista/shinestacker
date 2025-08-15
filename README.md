# Shine Stacker

## Focus Stacking Processing Framework and GUI

[![CI multiplatform](https://github.com/lucalista/shinestacker/actions/workflows/ci-multiplatform.yml/badge.svg)](https://github.com/lucalista/shinestacker/actions/workflows/ci-multiplatform.yml)
[![PyPI version](https://img.shields.io/pypi/v/shinestacker?color=success)](https://pypi.org/project/shinestacker/)
[![Python Versions](https://img.shields.io/pypi/pyversions/shinestacker)](https://pypi.org/project/shinestacker/)
[![codecov](https://codecov.io/github/lucalista/shinestacker/graph/badge.svg?token=Y5NKW6VH5G)](https://codecov.io/github/lucalista/shinestacker)
[![Documentation Status](https://readthedocs.org/projects/shinestacker/badge/?version=latest)](https://shinestacker.readthedocs.io/en/latest/?badge=latest)
[![pylint](https://img.shields.io/badge/PyLint-9.92-yellow?logo=python&logoColor=whitehttps://img.shields.io/badge/PyLint-9.92-yellow?logo=python&logoColor=white)

<img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/flies.gif' width="400" referrerpolicy="no-referrer">  <img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/flies_stack.jpg' width="400" referrerpolicy="no-referrer">

<img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/coins.gif' width="400" referrerpolicy="no-referrer">  <img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/coins_stack.jpg' width="400" referrerpolicy="no-referrer">
> **Focus stacking** for microscopy, macro photography, and computational imaging

## Key Features
- 🚀 **Batch Processing**: Align, balance, and stack hundreds of images
- 🎨 **Hybrid Workflows**: Combine Python scripting with GUI refinement
- 🧩 **Modular Architecture**: Mix-and-match processing modules
- 🖌️ **Non-Destructive Editing**: Save multilayer TIFFs for retouching
- 📊 **Jupyter Integration**: Reproducible research notebooks

## Interactive GUI

The GUI has two main working areas: 

* *Project*: manage and run focus stacking workflows in a flexible and configurable way, with optional intermediate batch stacking.

<img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/gui-project-run.png' width="600" referrerpolicy="no-referrer">

* *Retouch*: select interactively details from individual frames and apply final filters to the blended image.

<img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/gui-retouch.png' width="600" referrerpolicy="no-referrer">

# Documentation

📖 [Main documentation](https://github.com/lucalista/shinestacker/blob/main/docs/main.md) • 📝 [Changelog](https://github.com/lucalista/shinestacker/blob/main/CHANGELOG.md)


# Credits

The main pyramid stack algorithm was initially inspired by the [Laplacian pyramids method](https://github.com/sjawhar/focus-stacking) implementation by Sami Jawhar that was used under permission of the author for initial versions of this package. The implementation in the latest releases was rewritten from the original code.

# Resources

* [Pyramid Methods in Image Processing](https://www.researchgate.net/publication/246727904_Pyramid_Methods_in_Image_Processing), E. H. Adelson, C. H. Anderson,  J. R. Bergen, P. J. Burt, J. M. Ogden, RCA Engineer, 29-6, Nov/Dec 1984
Pyramid methods in image processing
* [A Multi-focus Image Fusion Method Based on Laplacian Pyramid](http://www.jcomputers.us/vol6/jcp0612-07.pdf), Wencheng Wang, Faliang Chang, Journal of Computers 6 (12), 2559, December 2011
* Another [original implementation on GitHub](https://github.com/bznick98/Focus_Stacking) by Zongnan Bao

# License

The software is provided as is under the [GNU Lesser General Public License v3.0](https://choosealicense.com/licenses/lgpl-3.0/).

