# Focus stacking with image batches

based on [Laplacian pyramids method](https://github.com/sjawhar/focus-stacking) implementation by Sami Jawhar. The original code was used under permission of the author.

**Resources:**

* [Pyramid Methods in Image Processing](https://www.researchgate.net/publication/246727904_Pyramid_Methods_in_Image_Processing), E. H. Adelson, C. H. Anderson,  J. R. Bergen, P. J. Burt, J. M. Ogden, RCA Engineer, 29-6, Nov/Dec 1984
Pyramid methods in image processing
* [A Multi-focus Image Fusion Method Based on Laplacian Pyramid](http://www.jcomputers.us/vol6/jcp0612-07.pdf), Wencheng Wang, Faliang Chang, Journal of Computers 6 (12), 2559, December 2011
* [Original core implementation on GitHub](https://github.com/bznick98/Focus_Stacking) by Zongnan Bao
* [Align with OpenCV](https://magamig.github.io/posts/accurate-image-alignment-and-registration-using-opencv/)
* [Balancing contrast and brightness between stitched images](https://itecnote.com/tecnote/opencv-balancing-contrast-and-brightness-between-stitched-images/)

### Usage example:

```python
from focus_stack import *
job = StackJob("job", "E:/Focus stacking/My image directory/")
job.add_action(AlignLayers(job.working_directory, "align", input_path="source"))
job.add_action(BalanceLayersLumi(job.working_directory, "balance", input_path="align", mask_radius=0.8, i_min=10, i_max=255))
job.add_action(FocusStackBunch(job.working_directory, "batches", PyramidStack(), input_path="balance", exif_dir="Immagini modificate", frames=10, overlap=2, denoise=0.8))
job.add_action(FocusStack(job.working_directory, "stack", PyramidStack(), input_path="batches", exif_dir="Immagini modificate", postfix='_stack_pyr', denoise=0.8))
job.run()
```
### Required software:

* python
* open cv
* numpy
* scipy
* matplotlib
* termcolor
* tqdm
* PIL
