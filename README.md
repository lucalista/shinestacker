# Focus stacking framework

<img src='img/flies.gif' width="400">  <img src='img/flies_stack.jpg' width="400">

## Usage example

```python
from focus_stack import *

job = StackJob("job", "E:/Focus stacking/My image directory/", input_path="src")
job.add_action(NoiseDetection())
job.run()

job = StackJob("job", "E:/Focus stacking/My image directory/", input_path="src")
job.add_action(Actions("align", actions=[MaskNoise(), Vignetting(), AlignFrames(),
                                         BalanceFrames(mask_size=0.9, i_min=150, i_max=65385)]))
job.add_action(FocusStackBunch("batches", PyramidStack(), frames=10, overlap=2, denoise=0.8))
job.add_action(FocusStack("stack", PyramidStack(), postfix='_py', denoise=0.8))
job.add_action(FocusStack("stack", DepthMapStack(), input_path='batches', postfix='_dm', denoise=0.8))
job.add_action(MultiLayer("multilayer", input_path=['batches', 'stack']))
job.run()
```
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

## Documentation

### Job creation

Create a job, then schedule the desired actions in a job, then run the job.

```python
job = StackJob(name, working_path [, input_path])
```

Arguments are:
* ```working_path```: the directory that contains input and output images, organized in subdirectories as specified by each action
* ```name```: the name of the job, used for printout
* ```input_path``` (optional): the subdirectory within ```working_path``` that contains input images for subsequent action. If not specified, at least the first action must specify an ```input_path```.

### Schedule multiple actions based on a reference image: align and/or balance images

The class ```Actions``` runs multiple actions on each of the frames appearing in a path.

```python
job.add_action(Actions(name, actions=[...], *options))
```
Arguments for the constructor of ```Actions``` are for the :
* ```name```: the name of the action, used for printout, and possibly for output path
* ```actions```: array of action object to be applied in cascade
* ```input_path``` (optional): the subdirectory within ```working_path``` that contains input images to be processed. If not specified, the last output path is used, or, if this is the first action, the ```input_path``` specified with the ```StackJob``` construction is used. If the ```StackJob``` specifies no ```input_path```, at least the first action must specify an  ```input_path```.
* ```output_path``` (optional): the subdirectory within ```working_path``` where aligned images are written. If not specified,  it is equal to  ```name```.
* ```working_path```: the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.
* ```plot_path``` (optional, default: ```plots```): the directory within ```working_path``` that contains plots produced by the different actions
* ```resample``` (optione, default: 1): take every *n*<sup>th</sup> frame in the selected directory. Default: take all frames.
* ```ref_idx``` (optional): the index of the image used as reference. Images are numbered starting from zero. If not specified, it is the index of the middle image.
* ```step_process``` (optional): if equal to ```True``` (default), each image is aligned with respect to the previous or next image, depending if it is after or befor the reference image.

### Image registration: scale, tanslation and rotation correction, or full perspective correction

```python
job.add_action(Actions("align", actions=[AlignFrames(*options)])
```
Arguments for the constructor ```AlignFrames``` of are:
* ```feature_config``` (optional, default: ```None```): a dictionary specifying the following parameters, with the corresponding default values:
```python
{
    'detector': DETECTOR_SIFT,
    'descriptor': DESCRIPTOR_SIFT
}
```
* ```detector``` (optional): the feature detector is used to find matches. See [Feature Detection and Description](https://docs.opencv.org/4.x/db/d27/tutorial_py_table_of_contents_feature2d.html) for more details. Possible values are:
  * ```DETECTOR_SIFT``` (default): [Scale-Invariant Feature Transform](https://docs.opencv.org/4.x/da/df5/tutorial_py_sift_intro.html)]
  * ```DETECTOR_ORB```: [Oriented FAST and Rotated BRIEF](https://docs.opencv.org/4.x/d1/d89/tutorial_py_orb.html)
  * ```DETECTOR_SURF```: [Speeded-Up Robust Features](https://docs.opencv.org/3.4/df/dd2/tutorial_py_surf_intro.html)
  * ```DETECTOR_AKAZE```: [AKAZE local features matching](https://docs.opencv.org/3.4/db/d70/tutorial_akaze_matching.html)
* ```descriptor``` (optional): the feature descriptor is used to find matches. Possible values are:
  * ```DESCRIPTOR_SIFT``` (default)
  * ```DESCRIPTOR_ORB```
  * ```DESCRIPTOR_AKAZE```

```matching_config``` (optional, default; ```None```): a dictionary specifying the following parameters, with the corresponding default values:
```python
{
    'method': MATCHING_KNN,
    'flann_idx_kdtree': 2,
    'flann_trees': 5,
    'flann_checks': 50,
    'threshold': 0.75
}
```
* ```method``` (optional): the method used to find matches. See [Feature Matching](https://docs.opencv.org/4.x/dc/dc3/tutorial_py_matcher.html) for more details. Possible values are:
  * ```MATCHING_KNN``` (default): [Feature Matching with FLANN](https://docs.opencv.org/3.4/d5/d6f/tutorial_feature_flann_matcher.html)
  * ```MATCHING_NORM_HAMMING```: [Use Hamming distance](https://docs.opencv.org/4.x/d2/de8/group__core__array.html#ggad12cefbcb5291cf958a85b4b67b6149fa4b063afd04aebb8dd07085a1207da727)
* ```flann_idx_kdtree``` (optional, default: 2): parameter used by the FLANN matching algorithm.
* ```flann_tree``` (optional, default: 5): parameter used by the FLANN matching algorithm.
* ```flann_checks``` (optional, default: 50): parameter used by the FLANN matching algorithm.
* ```threshold``` (optional, default: 0.75): parameter used to select good matches. See [Feature Matching](https://docs.opencv.org/4.x/dc/dc3/tutorial_py_matcher.html) for more details. 

* ```alignment_config``` (optional, default; ```None```): a dictionary specifying the following parameters, with the corresponding default values:
```python
{
    'transform': ALIGN_RIGID,
    'rans_threshold': 5.0,
    'border_mode': BORDER_REPLICATE_BLUR,
    'border_value': (0, 0, 0, 0),
    'border_blur': 50
}
```
* ```transform``` (optional): the transformation applied to register images. Possible values are:
  * ```ALIGN_RIGID``` (default): allow scale, tanslation and rotation correction. This should be used for image acquired with tripode or microscope.
  * ```ALIGN_HOMOGRAPHY```: allow full perspective correction. This should be used for images taken with hand camera.
* ```rans_threshold``` (optional, default: 5.0): parameter used if ```ALIGN_HOMOGRAPHY``` is choosen as tansformation, see [Feature Matching + Homography to find Objects](https://docs.opencv.org/3.4/d1/de0/tutorial_py_feature_homography.html) for more details.
* ```border_mode``` (optional, default: ```BORDER_REPLICATE_BLUR```): border mode. See [Adding borders to your images](https://docs.opencv.org/3.4/dc/da3/tutorial_copyMakeBorder.html) for more details.  Possible values are:
  * ```BORDER_CONSTANT```: pad the image with a constant value. The border value is specified with the parameter ```border_value```.
  * ```BORDER_REPLICATE```: the rows and columns at the very edge of the original are replicated to the extra border.
  * ```BORDER_REPLICATE_BLUR``` (default): same as above, but the border is blurred. The amount of blurring is specified by the parameter ```border_blur```.
* ```border_value``` (optional, default: ```(0, 0, 0, 0)```): border value. See [Adding borders to your images](https://docs.opencv.org/3.4/dc/da3/tutorial_copyMakeBorder.html) for more details.
* ```border_blur``` (optional, default: ```50```): amount of border blurring, in pixels. Only applied if ```border_mode``` is set to ```BORDER_REPLICATE_BLUR```, which is the default option.


* ```plot_config``` (optional, default; ```None```): a dictionary specifying the following parameters, with the corresponding default values:
```python
{
    'enabled': False,
    'path': ''
}
```
* ```enabled``` (optional, default: ```False```): if ```True```, for each image the matches identified with respect to the reference image are plotted. May be useful for inspection and debugging.
* ```path``` (optional, default: ```''```): unused, applied only for internal testing.
 
### Luminosity and color balance

```python
job.add_action(Actions("balance", actions=[BalanceFrames(*options)])
```
  
Arguments for the constructor of ```BalanceFrames``` are:
*```channel``` (optional, default: LUMI): channels to be balanced. Possible values are: ```LUMI``` (default): balance equally for R, G and B channels, should be reasonably fine for most of the cases; ```RGB```: balance luminosity separately for R, G and B channels, it may be needed if some but not all of the images have a undesired color dominance; ```HSV```: balance saturation a luminosity value in the HSV (Hue, Saturation, brightness Value) representation, it may be needed in cases of extreme luminosity variation that affects saturation; ```HLS```: balance saturation a luminosity value in the HLS (Hue, Lightness, Saturation) representation, it may be needed in cases of extreme luminosity variation that affects saturation.
* ```mask_size``` (optional): if specified, luminosity and color balance is only applied to pixels within a circle of radius equal to the minimum between the image width and height times ```mask_size```, i.e: 0.8 means 80% of a portrait image width or landscape image height. It may beuseful for images with vignetting, in order to avoid including in the balance processing the outer darker pixels.
* ```intensity_interval``` (optional): if specifies, only pixels with intensity within the specified range are used. It may be useful to remove very dark areas or very light areas. Not used if ```MATCH_HIST``` is specified as value for ```corr_map```. The argument has to be a dictionary where one or both values corresponding to the keys ```min``` and ```max``` can be specified. The default values are:
```python
{
    'min': 0,
    'max': -1
}
```
Note that for 8-bit images the maximum intensity is 255, while for 16-bit images the maximum intensity is 65536.
* ```img_scale``` (optional, default: 8): gets luminosity histogram using every n-th pixel in each dimension. By default, it takes one every 10 pixels in horizontal and vertical directions, i.e.: one every 100 pixels in total.  
* ```corr_map``` (optional, default: ```LINEAR```, possible values: ```LINEAR```, ```GAMMA``` and ```MATCH_HIST```): applies either a linear mapping or a gamma correction or matches histograms of reference and source images. The gamma correction avoids saturation of high luminosity pixels, but may introduce more distortion than a linear mapping. If ```MATCH_HIST``` is specified as value for ```corr_map```, option ```intensity_interval``` is not used. Note that ```MATCH_HIST``` should be used with ```RGBCorrection```, and it is safer to set ```img_scale=1```.
* ```plot_histograms```  (optional, default: ```False```): if ```True```, for each image and for the reference image histograms with pixel content are plotted. May be useful for inspection and debugging.
  
### Vignetting correction

```python
job.add_action(Actions("vignette", actions=[Vignetting(*options)])
```

Applies a radial luminosity correction determined from the mean pixel luminosity, spotting vignetting effect at the image borders. The correction is determined by modeling the mean luminosity as a function of the distance $r$ from the image center with the following asymmetric sigmoid model:

$\displaystyle i(r) = \frac{i_0}{1 + \exp(\exp(k(r - r_0)))}\,$

where the parameters $i_0$, $k$ and $r_0$ are estimated from the image luminosity data.
               
Arguments for the constructor of ```Vignetting``` are:
* ```r_steps``` (optional, default: 100): number of radial steps to determine mean pixel luminosity.
* ```black_threshold``` (optional, default: 1): apply correction only on pixels with luminosity greater than.
* ```max_correction``` (optional, default: 1): if less than one, the correction is rescaled in order to be at most the specified valye.
* ```apply_correction``` (optional, default: ```True```): if ```False```, the correction is computed but not applied to the image. It may be useful in order to determine a value of the parameter ```mask_size``` for the action ```BalanceFrames``` by looking at the output curve plot.


### Focus Stacking

```python
job.add_action(FocusStack(name, stacker, *options))
```
Arguments for the constructor of ```FocusStack``` are:
* ```name```: the name of the action, used for printout, and possibly for output path
* ```stacker```: an object defining the focus stacking algorithm. Can be ```PyramidStack``` or ```DepthMapStack```, see below for possible algorithms. 
* ```input_path``` (optional): the subdirectory within ```working_path``` that contains input images to be processed. If not specified, the last output path is used, or, if this is the first action, the ```input_path``` specified with the ```StackJob``` construction is used. If the ```StackJob``` specifies no ```input_path```, at least the first action must specify an  ```input_path```.
* ```output_path``` (optional): the subdirectory within ```working_path``` where aligned images are written. If not specified,  it is equal to  ```name```.
* ```working_path```: the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.
* ```exif_path``` (optional): if specified, EXIF data are copied to the output file from file in the specified directory. If not specified, it is the source directory used as input for the first action. If set equal to ```''``` no EXIF data is saved.
* ```postfix``` (optional): if specified, the specified string is appended to the file name. May be useful if more algorithms are ran, and different file names are used for the output of different algorithms.
* ```denoise``` (optoinal): if specified, a denois algorithm is applied. A value of 0.75 to 1.00 does not reduce details in an appreciable way, and is suitable for modest noise reduction. denoise may be useful for 8-bit images, or for images taken at large ISO. 16-bits images at low ISO usually don't require denoise. See [Image Denoising](https://docs.opencv.org/3.4/d5/d69/tutorial_py_non_local_means.html) for more details.

### Focus Stacking in bunches of frames

```python
job.add_action(FocusStackBunch(name, stacker, *options))
```
Arguments for the constructor of ```FocusStackBunch``` are:
* ```name```: the name of the action, used for printout, and possibly for output path
* ```stacker```: an object defining the focus stacking algorithm. Can be ```PyramidStack``` or ```DepthMapStack```, see below for possible algorithms. 
* ```input_path``` (optional): the subdirectory within ```working_path``` that contains input images to be processed. If not specified, the last output path is used, or, if this is the first action, the ```input_path``` specified with the ```StackJob``` construction is used. If the ```StackJob``` specifies no ```input_path```, at least the first action must specify an  ```input_path```.
* * ```output_path``` (optional): the subdirectory within ```working_path``` where aligned images are written. If not specified,  it is equal to  ```name```.
* ```working_path```: the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.
* ```exif_path``` (optional): if specified, EXIF data are copied to the output file from file in the specified directory. If not specified, it is the source directory used as * ```frames``` (optional, default: 10): the number of frames in each bunch that are stacked together.
* ```overlap``` (optional, default: 0): the number of overlapping frames between a bunch and the following one. 
* ```postfix``` (optional): if specified, the specified string is appended to the file name. May be useful if more algorithms are ran, and different file names are used for the output of different algorithms.
* ```denoise``` (optoinal): if specified, a denois algorithm is applied. A value of 0.75 to 1.00 does not reduce details in an appreciable way, and is suitable for modest noise reduction. See [Image Denoising](https://docs.opencv.org/3.4/d5/d69/tutorial_py_non_local_means.html) for more details

#### Stack algorithms

* ```PyramidStack```, based on [Laplacian pyramids method](https://github.com/sjawhar/focus-stacking) implementation by Sami Jawhar. Arguments are:
   * ```pyramid_min_size``` (optional, default: 32)
   * ```kernel_size``` (optional, default: 5)
   * ```gen_kernel``` (optional, default: 0.4) 
* ```DepthMapStack```, based on [Laplacian pyramids method](https://github.com/sjawhar/focus-stacking) implementation by Sami Jawhar. Arguments are:
   * ```map_type``` (optional), possible values are  ```MAP_MAX``` (default) and ```MAP_AVERAGE```. ```MAP_MAX``` select for wach pixel the layer which has the best focus. ```MAP_AVERAGE``` performs for each pixel an average of all layers weighted by the quality of focus.
   * ```energy``` (optional), possible values are ```ENERGY_LAPLACIAN``` (default) and ```ENERGY_SOBEL```.
   * ```kernel_size``` (optional, default: 5) 
   * ```blur_size``` (optional, default: 5) 
   * ```smooth_size``` (optional, default: 32)

### Combine frames into a single multilayer tiff

```python
job.add_action(MultiLayer(name, *options))
```
Typically, one may want to combine the output of focus stacking and intermediate frames, or bunches, in order to perform fine retouch using an image manipulation application.

Arguments for the constructor of ```MultiLayer``` are:
* ```input_path``` (optional): one or more subdirectory within ```working_path``` that contains input images to be combined. If not specified, the last output path is used, or, if this is the first action, the ```input_path``` specified with the ```StackJob``` construction is used. If the ```StackJob``` specifies no ```input_path```, at least the first action must specify an  ```input_path```.
* ```output_path``` (optional): the subdirectory within ```working_path``` where aligned images are written. If not specified,  it is equal to  ```name```.
* ```working_path```: the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.

### Noisy pixel masking

First, the mask of noisy pixels has to be determined and stored in a PNG file using the action ```NoiseDetection```:

```python
job = StackJob("job", "E:/Focus stacking/My image directory/")
job.add_action(NoiseDetection("noise-map", input_path=["src"]))
job.run()
```

Arguments for the constructor of ```NoiseDetection``` are:
* ```name``` (optional, default: ```noise-map```): name of the action and default name of the subdirectory within ```working_path``` where aligned noise map is written. 
* ```input_path``` (optional): one or more subdirectory within ```working_path``` that contains input images to be combined. If not specified, the last output path is used, or, if this is the first action, the ```input_path``` specified with the ```StackJob``` construction is used. If the ```StackJob``` specifies no ```input_path```, at least the first action must specify an  ```input_path```.
* ```output_path``` (optional): the subdirectory within ```working_path``` where aligned noise map is written. If not specified,  it is equal to  ```name```.
* ```working_path```: the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.
* ```plot_path``` (optional, default: ```plots```): the directory within ```working_path``` that contains plots produced by the different actions
* ```channel_thresholds``` (optional, default: ```(13, 13, 13)```): threshold values for noisy pixel detections in the color channels R, G, B, respectively.
* ```blur_size``` (optional, default: 5): image blur amount for pixel detection.
* ```file_name``` (optional, default: ```hot```): noise map filename. The noisy pixel map is stored bydefault in the file ```hot-rgb.png```. Noisy pixel maps individyally for the R, G and B channels are also stored in  ```hot-r.png```,  ```hot-g.png``` and  ```hot-b.png```, respectively.

After the noisy pixel mask has been determined, noisy pixels are then masked adding the action ```MaskNoise``` to the ```Actions``` module:

```python
job.add_action(Actions("mask", actions=[MaskNoise(*options)]))
```

Or as preliminary stage to more actions:
```python
job.add_action(Actions("align", actions=[MaskNoise(),
                                         AlignFrames(),
                                         BalanceFrames(mask_size=0.9,
                                         intensity_interval={'min': 150, 'max':65385})]))
```

Arguments for the constructor of ```NoiseDetection``` are:
* ```noise_mask``` (optional, default: ```noise-map/hot-rgb.png```): filename of the noise mask
*  ```kernel_size``` (optional, default: 3): blur size use to extract noisy pixels
*  ```method``` (optional, default: ```INTERPOLATE_MEAN```): possible values: ```INTERPOLATE_MEAN```, ```INTERPOLATE_MEDIAN```. Interpolate using mean or median of neighborhood pixels to replace a noisy pixel.

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
* ```SVCorrection``` and ```LSCorrection``` are only supported for 8-bit images
* Even if ```exif_path``` is explicitly specified, for 16-bit TIFF exif data for the moment are not be saved because of incomplete support of EXIF data for TIFF files.
* Focus stacking modules crashes for TIFF files if  ```denoise``` is set ifferent from zero due to an assertion failure in the Open CV library. This is similar to a [known issue on stackoverflow](https://stackoverflow.com/questions/76647895/opencv-fastnlmeansdenoisingmulti-should-support-16-bit-images-but-does-it).

## License

The software is provided as is under the [GNU Lesser General Public License v3.0](https://choosealicense.com/licenses/lgpl-3.0/).

