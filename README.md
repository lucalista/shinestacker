# Focus stacking framework

based on [Laplacian pyramids method](https://github.com/sjawhar/focus-stacking) implementation by Sami Jawhar. The original code was used under permission of the author.

**Resources:**

* [Pyramid Methods in Image Processing](https://www.researchgate.net/publication/246727904_Pyramid_Methods_in_Image_Processing), E. H. Adelson, C. H. Anderson,  J. R. Bergen, P. J. Burt, J. M. Ogden, RCA Engineer, 29-6, Nov/Dec 1984
Pyramid methods in image processing
* [A Multi-focus Image Fusion Method Based on Laplacian Pyramid](http://www.jcomputers.us/vol6/jcp0612-07.pdf), Wencheng Wang, Faliang Chang, Journal of Computers 6 (12), 2559, December 2011
* Another [original implementation on GitHub](https://github.com/bznick98/Focus_Stacking) by Zongnan Bao

### Usage example with jupyter notebook:

```python
from focus_stack import *
job = StackJob("job", "E:/Focus stacking/My image directory/")
job.add_action(AlignLayers(job.working_directory, "align", input_path="source"))
job.add_action(BalanceLayersLumi(job.working_directory, "balance", input_path="align", mask_size=0.8, i_min=10, i_max=255))
job.add_action(FocusStackBunch(job.working_directory, "batches", PyramidStack(), input_path="balance", exif_dir="Immagini modificate", frames=10, overlap=2, denoise=0.8))
job.add_action(FocusStack(job.working_directory, "stack", PyramidStack(), input_path="batches", exif_dir="Immagini modificate", postfix='_stack_pyr', denoise=0.8))
job.run()
```
### Required python modules:

* open cv
* numpy
* scipy
* matplotlib
* termcolor
* tqdm
* PIL

## Documentation

Schedule the desired actions in a job, then run the job.

### Job creation

```python
job = StackJob(name, working_directory)
```

arguments are:
* ```working_directory```: the directory that contains input and output images, organized in subdirectories as specified by each action
* ```name```: the name of the job, used for printout

### Image registration: scale, tanslation and rotation correction, or full perspective correction

```python
job.add_action(AlignLayers(working_directory, name, input_path, *options))
```
arguments are:
* ```working_directory```: the directory that contains input and output images, normaly it is the same as ```job.working_directory```.
* ```name```: the name of the action, used for printout.
* ```input_path```: the subdirectory within ```working_directory``` that contains input images to be aligned.
* ```output_path``` (optional): the subdirectory within ```working_directory``` where aligned images are written. If not specified,  it is equal to  ```name```.
* ```ref_idx``` (optional): the index of the image used as reference. Images are numbered starting from zero. If not specified, it is the index of the middle image.
* ```step_align``` (optional): if equal to ```True``` (default), each image is aligned with respect to the previous or next image, depending if it is after or befor the reference image.
* ```transform``` (optional): the transformation applied to register images. Possible values are:
  * ```ALIGN_RIGID``` (default): allow scale, tanslation and rotation correction. This should be used for image acquired with tripode or microscope.
  * ```ALIGN_HOMOGRAPHY```: allow full perspective correction. This should be used for images taken with hand camera.
* ```detector``` (optional): the feature detector is used to find matches. See [Feature Detection and Description](https://docs.opencv.org/4.x/db/d27/tutorial_py_table_of_contents_feature2d.html) for more details. Possible values are:
  * ```SIFT``` (default): [Scale-Invariant Feature Transform](https://docs.opencv.org/4.x/da/df5/tutorial_py_sift_intro.html)]
  * ```ORB```: [Oriented FAST and Rotated BRIEF](https://docs.opencv.org/4.x/d1/d89/tutorial_py_orb.html)
  * ```SURF```: [Speeded-Up Robust Features](https://docs.opencv.org/3.4/df/dd2/tutorial_py_surf_intro.html)
  * ```AKAZE```: [AKAZE local features matching](https://docs.opencv.org/3.4/db/d70/tutorial_akaze_matching.html)
* ```descriptor``` (optional): the feature descriptor is used to find matches. Possible values are:
  * ```SIFT``` (default)
  * ```ORB```
  * ```AKAZE```
* ```match_method``` (optional): the method used to find matches. See [Feature Matching](https://docs.opencv.org/4.x/dc/dc3/tutorial_py_matcher.html) for more details. Possible values are:
  * ```KNN``` (default): [Feature Matching with FLANN](https://docs.opencv.org/3.4/d5/d6f/tutorial_feature_flann_matcher.html)
  * ```NORM_HAMMING```: 
* ```flann_idx_kdtree``` (optional, default: 2): parameter used by the FLANN matching algorithm.
* ```flann_tree``` (optional, default: 5): parameter used by the FLANN matching algorithm.
* ```flann_checks``` (optional, default: 50): parameter used by the FLANN matching algorithm.
* ```match_threshold``` (optional, default: 0.75): parameter used to select good matches. See [Feature Matching](https://docs.opencv.org/4.x/dc/dc3/tutorial_py_matcher.html) for more details. 
* ```rans_threshold```  (optional, default: 5.0): parameter used if ```ALIGN_HOMOGRAPHY``` is choosen as tansformation, see [Feature Matching + Homography to find Objects
](https://docs.opencv.org/3.4/d1/de0/tutorial_py_feature_homography.html) for more details
*``` plot_matches``` (optional, default: ```False```): if ```True```, for each image the matches identified with respect to the reference image are plotted. May be needed for inspection and debugging.

### Luminosity and color balance

There are four possible luminosity and color balance methods:
* ```BalanceLayersLumi```: balance luminosity equally for R, G and B channels. It should be fine for most of the cases.
* ```BalanceLayersRGB```: balance luminosity separately for R, G and B channels. It may be needed if some but not all of the images have a undesired color dominance.
* ```BalanceLayersLumiSV```: balance saturation a luminosity value in the HSV (Hue, Saturation, brightness Value) representation. It may be needed in cases of extreme luminosity variation that affects saturation.
* ```BalanceLayersLS```: balance saturation a luminosity value in the HLS (Hue, Lightness, Saturation) representation. It may be needed in cases of extreme luminosity variation that affects saturation.

```python
job.add_action(BalanceLayersLumi(working_directory, name, *options))
```
arguments are:
* ```working_directory```: the directory that contains input and output images, normaly it is the same as ```job.working_directory```.
* ```name```: the name of the action, used for printout.
* ```input_path```: the subdirectory within ```working_directory``` that contains input images to be aligned.
* ```output_path``` (optional): the subdirectory within ```working_directory``` where aligned images are written. If not specified,  it is equal to  ```name```.
* ```ref_idx``` (optional): the index of the image used as reference. Images are numbered starting from zero. If not specified, it is the index of the middle image.
* ```mask_size``` (optional): if specified, luminosity and color balance is only applied to pixels within a circle of radius equal to the minimum between the image width and height times ```mask_size```, i.e: 0.8 means 80% of a portrait image height. It may beuseful for images with vignetting, in order to remove the outer darker pixels.
* ```i_min``` (optional): if specifies, only pixels with content greater pr equal tham ```i_min``` are used. It may be useful to remove black areas.
* ```i_max``` (optional): if specifies, only pixels with content less pr equal tham ```i_max``` are used. It may be useful to remove white areas.
* ```plot_histograms```  (optional, default: ```False```): if ```True```, for each image and for the reference image histograms with pixel content are plotted. May be needed for inspection and debugging.

### Focus Stacking

```python
job.add_action(FocusStack(working_directory, name, stacker, input_path, *options))
```
arguments are:
* ```working_directory```: the directory that contains input and output images, normaly it is the same as ```job.working_directory```.
* ```name```: the name of the action, used for printout.
* ```stacker```: an object defining the focus stacking algorithm. Can be ```PyramidStack``` or ```DepthMapStack```, see below for possible algorithms. 
* ```input_path```: the subdirectory within ```working_directory``` that contains input images to be aligned.
* ```output_path``` (optional): the subdirectory within ```working_directory``` where aligned images are written. If not specified,  it is equal to  ```name```.
* ```exif_dir``` (optional): if specified, EXIF data are copied to the output file from file in the specified directory. Usually, it is the source directory used as input for the first action.
* ```postfix``` (optional): if specified, the specified string is appended to the file name. May be useful if more algorithms are ran, and different file names are used for the output of different algorithms.
* ```denoise``` (optoinal): if specified, a denois algorithm is applied. A value of 0.75 to 1.00 does not reduce details in an appreciable way, and is suitable for modest noise reduction. See [Image Denoising](https://docs.opencv.org/3.4/d5/d69/tutorial_py_non_local_means.html) for more details

### Bunch Focus Stacking

```python
job.add_action(FocusStackBunch(working_directory, name,  stacker, input_path, *options))
```
arguments are:
* ```working_directory```: the directory that contains input and output images, normaly it is the same as ```job.working_directory```.
* ```name```: the name of the action, used for printout.
* ```stacker```: an object defining the focus stacking algorithm. See below for possible algorithms.
* ```input_path```: the subdirectory within ```working_directory``` that contains input images to be aligned.
* ```output_path``` (optional): the subdirectory within ```working_directory``` where aligned images are written. If not specified,  it is equal to  ```name```.
* ```frames``` (optional, default: 10): the number of frames in each bunch that are stacked together.
* ```overlap``` (optional, default: 0): the number of overlapping frames between a bunch and the following one. 
* ```exif_dir``` (optional): if specified, EXIF data are copied to the output file from file in the specified directory. Usually, it is the source directory used as input for the first action.
* ```postfix``` (optional): if specified, the specified string is appended to the file name. May be useful if more algorithms are ran, and different file names are used for the output of different algorithms.
* ```denoise``` (optoinal): if specified, a denois algorithm is applied. A value of 0.75 to 1.00 does not reduce details in an appreciable way, and is suitable for modest noise reduction. See [Image Denoising](https://docs.opencv.org/3.4/d5/d69/tutorial_py_non_local_means.html) for more details

#### Stack algorithms

* ```PyramidStack```, based on [Laplacian pyramids method](https://github.com/sjawhar/focus-stacking) implementation by Sami Jawhar. Arguments are:
   * ```pyramid_min_size``` (optiohnal, default: 32)
   * ```kernel_size``` (optional, default: 5) 
* ```DepthMapStack```, based on [Laplacian pyramids method](https://github.com/sjawhar/focus-stacking) implementation by Sami Jawhar. Arguments are:
   * ```map_type``` (optional), possible values are  ```MAP_MAX``` (default) and ```MAP_AVERAGE```. ```MAP_MAX``` select for wach pixel the layer which has the best focus. ```MAP_AVERAGE``` performs for each pixel an average of all layers weighted by the quality of focus.
   * ```energy``` (optional), possible values are ```ENERGY_LAPLACIAN``` (default) and ```ENERGY_SOBEL```.
   * ```kernel_size``` (optional, default: 5) 
   * ```blur_size``` (optional, default: 5) 
   * ```smooth_size``` (optional, default: 32) 

## Issues

The support of 16 bits images is still partial. In particular, with 16 bits images:
* Automatic luminosity and color balance fails due to an assertion failures in the Open CV library.
* Focus stacking modules crashes if  ```denoise``` is different from zero due to an assertion failures in the Open CV library.
* Focus stacking modules may crashes if  ```exif_dir``` is provided and if the directory contains TIFF images, depending on the content of EXIF data. A couple of identified problematic keys, namely 33723, 34665, cause a crash in the PIL library.
