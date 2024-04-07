# Focus stacking with image batches

based on [Laplacian pyramids method](https://github.com/sjawhar/focus-stacking) implementation by Sami Jawhar. The original code was used under permission of the author.

**Resources:**

* [Pyramid Methods in Image Processing](https://www.researchgate.net/publication/246727904_Pyramid_Methods_in_Image_Processing), E. H. Adelson, C. H. Anderson,  J. R. Bergen, P. J. Burt, J. M. Ogden, RCA Engineer, 29-6, Nov/Dec 1984
Pyramid methods in image processing
* [A Multi-focus Image Fusion Method Based on Laplacian Pyramid](http://www.jcomputers.us/vol6/jcp0612-07.pdf), Wencheng Wang, Faliang Chang, Journal of Computers 6 (12), 2559, December 2011
* Another [original implementation on GitHub](https://github.com/bznick98/Focus_Stacking) by Zongnan Bao

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

## Documentation

Schedule the desired actions in a job, then run the job.

Create the job with:

```python
job = StackJob(name, working_directory)
```

arguments are:
* ```working_directory```: the directory that contains input and output images, organized in subdirectories as specified by each action
* ```name```: the name of the job, used for printout

Schedule automatic alignment with:

```python
job.add_action(AlignLayers(working_directory, name, input_path, *arguments))
```
arguments are:
* ```working_directory```: the directory that contains input and output images, normaly it is the same as ```job.working_directory```.
* ```name```: the name of the action, used for printout.
* ```input_path```: the subdirectory within ```working_directory``` that contains input images to be aligned.
* ```output_path``` (optional): the subdirectory within ```working_directory``` where aligned images are written. If not specified,  it is equal to  ```name```.
* ```ref_idx``` (optional): the index of the image used as reference. Images are numbered starting from zero. If not specified, it is the index of to the middle image.
* ```step_align``` (optional): if equal to ```True``` (default), each image is aligned with respect to the previous or next image, depending if it is after or befor the reference image.
* ```detector``` (optional): specifies which feature detector is used to find matches. See [Feature Detection and Description](https://docs.opencv.org/4.x/db/d27/tutorial_py_table_of_contents_feature2d.html) for more details. Possible values are:
  * ```SIFT``` (default): [Scale-Invariant Feature Transform](https://docs.opencv.org/4.x/da/df5/tutorial_py_sift_intro.html)]
  * ```ORB```: [Oriented FAST and Rotated BRIEF](https://docs.opencv.org/4.x/d1/d89/tutorial_py_orb.html)
  * ```SURF```: [Speeded-Up Robust Features](https://docs.opencv.org/3.4/df/dd2/tutorial_py_surf_intro.html)
  * ```AKAZE```: [AKAZE local features matching](https://docs.opencv.org/3.4/db/d70/tutorial_akaze_matching.html)
* ```descriptor``` (optional): specifies which feature descriptor is used to find matches. Possible values are:
  * ```SIFT``` (default)
  * ```ORB```
  * ```AKAZE```
* ```match_method```='KNN'
* ```flann_idx_kdtree```=2
* ```flann_tree```s=5
* ```flann_checks```=50
* ```match_threshold```=0.75
* ```method```=ALIGN_RIGID
* ```rans_threshold```=5.0
*``` plot_matches```=False

