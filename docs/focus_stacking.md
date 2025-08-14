# Focus Stacking

```python
job.add_action(FocusStack(name, stacker, *options))
```
Arguments for the constructor of ```FocusStack``` are:
* ```name```: the name of the action, used for printout, and possibly for output path
* ```stacker```: an object defining the focus stacking algorithm. Can be ```PyramidStack```, ```PyramidBlock``` or ```DepthMapStack```, see below for possible algorithms. 
* ```input_path``` (optional): the subdirectory within ```working_path``` that contains input images to be processed. If not specified, the last output path is used, or, if this is the first action, the ```input_path``` specified with the ```StackJob``` construction is used. If the ```StackJob``` specifies no ```input_path```, at least the first action must specify an  ```input_path```.
* ```output_path``` (optional): the subdirectory within ```working_path``` where aligned images are written. If not specified,  it is equal to  ```name```.
* ```working_path```: the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.
* ```exif_path``` (optional): if specified, EXIF data are copied to the output file from file in the specified directory. If not specified, it is the source directory used as input for the first action. If set equal to ```''``` no EXIF data is saved.
* ```denoise_amount``` (optoinal): if specified, a denois algorithm is applied. A value of 0.75 to 1.00 does not reduce details in an appreciable way, and is suitable for modest noise reduction. denoise may be useful for 8-bit images, or for images taken at large ISO. 16-bits images at low ISO usually don't require denoise. See [Image Denoising](https://docs.opencv.org/3.4/d5/d69/tutorial_py_non_local_means.html) for more details.
* ```prefix``` (optional): if specified, the specified string is pre-pended to the file name. May be useful if more algorithms are ran, and different file names are used for the output of different algorithms.
* ```enabled``` (optional, default: ``True```): allows to switch on and off this module.

## Focus Stacking in bunches of frames

```python
job.add_action(FocusStackBunch(name, stacker, *options))
```
Arguments for the constructor of ```FocusStackBunch``` are:
* ```name```: the name of the action, used for printout, and possibly for output path
* ```stacker```: an object defining the focus stacking algorithm. Can be ```PyramidStack```, ```PyramidStack``` or ```DepthMapStack```, see below for possible algorithms. 
* ```input_path``` (optional): the subdirectory within ```working_path``` that contains input images to be processed. If not specified, the last output path is used, or, if this is the first action, the ```input_path``` specified with the ```StackJob``` construction is used. If the ```StackJob``` specifies no ```input_path```, at least the first action must specify an  ```input_path```.
* * ```output_path``` (optional): the subdirectory within ```working_path``` where aligned images are written. If not specified,  it is equal to  ```name```.
* ```working_path```: the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.
* ```exif_path``` (optional): if specified, EXIF data are copied to the output file from file in the specified directory. If not specified, it is the source directory used as * ```frames``` (optional, default: 10): the number of frames in each bunch that are stacked together.
* ```frames``` (optional, default: 10): the number of frames that are fused together. 
* ```overlap``` (optional, default: 0): the number of overlapping frames between a bunch and the following one. 
* ```denoise_amount``` (optoinal): if specified, a denois algorithm is applied. A value of 0.75 to 1.00 does not reduce details in an appreciable way, and is suitable for modest noise reduction. denoise may be useful for 8-bit images, or for images taken at large ISO. 16-bits images at low ISO usually don't require denoise. See [Image Denoising](https://docs.opencv.org/3.4/d5/d69/tutorial_py_non_local_means.html) for more details.
* ```prefix``` (optional): if specified, the specified string is pre-pended to the file name. May be useful if more algorithms are ran, and different file names are used for the output of different algorithms.
* ```enabled``` (optional, default: ```True```): allows to switch on and off this module.

## Stack algorithms

```PyramidStack```, Laplacian pyramid focus stacking algorithm, optimized implementation

Arguments for the constructor are:
   * ```pyramid_min_size``` (optional, default: 32)
   * ```kernel_size``` (optional, default: 5)
   * ```gen_kernel``` (optional, default: 0.4)
   * ```float_type``` (optional, default: ```FLOAT_32```, possible values: ```FLOAT_32```, ```FLOAT_64```): precision for internal image representation

```DepthMapStack```, Depth map focus stacking algorithm

Arguments for the constructor are:
   * ```map_type``` (optional), possible values are  ```MAP_MAX``` (default) and ```MAP_AVERAGE```. ```MAP_MAX``` select for wach pixel the layer which has the best focus. ```MAP_AVERAGE``` performs for each pixel an average of all layers weighted by the quality of focus.
   * ```energy``` (optional), possible values are ```ENERGY_LAPLACIAN``` (default) and ```ENERGY_SOBEL```.
   * ```kernel_size``` (optional, default: 5) size in pixels of Laplacian kernel.
   * ```blur_size``` (optional, default: 5) size in pixels of the pre-Laplacian Gaussian blur.
   * ```smooth_size``` (optional, default: 15) size of energy smoothing.
   * ```temperature``` (optional, default: 0.1) controls fision transition: lower value means sharper transitions.
   * ```levels``` (optional, defauls: 3) number of levels for the Laplacian pyramid.
