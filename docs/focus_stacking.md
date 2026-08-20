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
* ```plot_path``` (optional, default: ```plots```): the directory within ```working_path``` that contains plots produced by the algrithm.
* ```exif_path``` (optional): if specified, EXIF data are copied to the output file from file in the specified directory. If not specified, it is the source directory used as input for the first action. If set equal to ```''``` no EXIF data is saved.
* ```denoise_amount``` (optional; default: 0): if > 0, a denois algorithm is applied. A value of 0.75 to 1.00 does not reduce details in an appreciable way, and is suitable for modest noise reduction. denoise may be useful for 8-bit images, or for images taken at large ISO. 16-bits images at low ISO usually don't require denoise. See [Image Denoising](https://docs.opencv.org/3.4/d5/d69/tutorial_py_non_local_means.html) for more details.
* ```sharpen_amount_percent``` (optional; default: 0): if > 0, a unsharp mask algorithm is applied. Values from 50% up apply a visible amount of sharpening.
* ```sharpen_radius``` (optional; default: 1): specifies the radius, in pixels, of the unsharp mask algorithm.
* ```sharpen_threshold``` (optional; default: 0): specifies the threshold value of the unsharp mask algorithm.
* ```prefix``` (optional): if specified, the specified string is pre-pended to the file name. May be useful if more algorithms are ran, and different file names are used for the output of different algorithms. Cannot be used together with ```output_file_template```.
* ```output_file_template``` (optional): defines a template for the output filename. Alternative to `prefix` - cannot be used together. Supports `{method}`, `{input_count}`, `{input_prefix}`, `{input_min}`, and `{input_max}` placeholders.
* ```enabled``` (optional, default: ``True```): allows to switch on and off this module.
* ```scratch_output_dir``` (optional, default: ```True```): scratch output directory before processing. This avoids that existing files pollute the output.
* ```delete_output_at_end``` (optional, default: ```False```): delete output after processing. This cleans disk space in case of processing an intermediate step that is not part of the final output.

## Focus Stacking in bunches of frames

```python
job.add_action(FocusStackBunch(name, stacker, *options))
```
Arguments for the constructor of ```FocusStackBunch``` are:
* ```name```: the name of the action, used for printout, and possibly for output path
* ```stacker```: an object defining the focus stacking algorithm. Can be ```PyramidStack```, ```PyramidStack``` or ```DepthMapStack```, see below for possible algorithms. 
* ```input_path``` (optional): the subdirectory within ```working_path``` that contains input images to be processed. If not specified, the last output path is used, or, if this is the first action, the ```input_path``` specified with the ```StackJob``` construction is used. If the ```StackJob``` specifies no ```input_path```, at least the first action must specify an  ```input_path```.
* ```output_path``` (optional): the subdirectory within ```working_path``` where aligned images are written. If not specified,  it is equal to  ```name```.
* ```working_path```: the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.
* ```plot_path``` (optional, default: ```plots```): the directory within ```working_path``` that contains plots produced by the algrithm.
* ```exif_path``` (optional): if specified, EXIF data are copied to the output file from file in the specified directory. If not specified, it is the source directory used as input for the first action. If set equal to ```''``` no EXIF data is saved.
* ```frames``` (optional, default: 10): the number of frames that are fused together. 
* ```overlap``` (optional, default: 0): the number of overlapping frames between a bunch and the following one. 
* ```denoise_amount``` (optoinal): if specified, a denois algorithm is applied. A value of 0.75 to 1.00 does not reduce details in an appreciable way, and is suitable for modest noise reduction. denoise may be useful for 8-bit images, or for images taken at large ISO. 16-bits images at low ISO usually don't require denoise. See [Image Denoising](https://docs.opencv.org/3.4/d5/d69/tutorial_py_non_local_means.html) for more details.
* ```prefix``` (optional): if specified, the specified string is pre-pended to the file name. May be useful if more algorithms are ran, and different file names are used for the output of different algorithms. Cannot be used together with ```output_file_template```.
* ```output_file_template``` (optional): defines a template for the output filename. Alternative to `prefix` - cannot be used together. Supports `{method}`, `{input_count}`, `{input_prefix}`, `{input_min}`, `{input_max}`, and `{bunch_index:03d}` placeholders.
* ```enabled``` (optional, default: ```True```): allows to switch on and off this module.
* ```scratch_output_dir``` (optional, default: ```True```): scratch output directory before processing. This avoids that existing files pollute the output.
* ```delete_output_at_end``` (optional, default: ```False```): delete output after processing. This cleans disk space in case of processing an intermediate step that is not part of the final output.

## Template Placeholders

When using `output_file_template`, the following placeholders are available:

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{method}` | Stacking algorithm name | `pyramid` or `depth_map` |
| `{input_count}` | Total number of input frames | `9` |
| `{input_prefix}` | Common prefix of input filenames | `flies_` |
| `{input_min}` | Variable part of first input filename | `0000` |
| `{input_max}` | Variable part of last input filename | `0008` |
| `{bunch_index:03d}` | Zero-padded bunch index (FocusStackBunch only) | `001` |

**Examples** with input files `flies_0000.jpg` to `flies_0008.jpg`:

| Template | Result |
|----------|--------|
| `"{input_prefix}{input_min}-{input_max}_{input_count}frames"` | `flies_0000-0008_9frames.tif` |
| `"{method}_{input_count}frames_stack"` | `pyramid_9frames_stack.tif` |
| `"{method}_{input_min}-{input_max}"` | `pyramid_0000-0008.tif` |
| `"{input_prefix}{input_min}-{input_max}_bunch-{bunch_index:03d}"` | `flies_0000-0008_bunch-001.tif` |

## Stack algorithms

```PyramidStack```, Laplacian pyramid focus stacking algorithm

Arguments for the constructor are:
   * ```pyramid_min_size``` (optional, default: 32)
   * ```kernel_size``` (optional, default: 5)
   * ```gen_kernel``` (optional, default: 0.4)
   * ```float_type``` (optional, default: ```FLOAT_32```, possible values: ```FLOAT_32```, ```FLOAT_64```): precision for internal image representation

```PyramidTilesStack```, pyramid algorithn with I/O buffered tile pyramid merging to optimize memory usage for large files

Arguments for the constructor are, in addition to the ones for ```PyramidStack```:
   * ```tile_size``` (optional, default: 512): size of a time
   * ```n_tiled_layers``` (optional, default: 2): number of layers that are tiled. Usually the last one or two are the ones that take more memory.
   * ```max_threads``` (optional, default: number of cores, up to a maximum of 8): maximum number of thread used for parallel processing. The actual number of threads does not exceed the number of available cores. 
* ```chunk_submit``` (optional, default: ```True```): submit at most ```max_threads``` parallel processes. If ```chunk_submit``` is greater than ```max_threads``` a moderate performance gain is achieved at the cost of a possibly large memory occupancy.


```PyramidAutoStack```, pyramid algorithn with capability to automatically switch from all-in-memory to I/O buffered tiled.

Arguments for the constructor are, in addition to the ones for ```PyramidTilesStack```:
   * ```mode``` (optional, default: ```auto```): can be ```auto```, ```memory``` or ```tiled```.
   * ```memory_limit``` (optional, default: 8×1024<sup>3</sup>sup>): memory limit to determine optimal running parameters


Arguments for the constructor are the same ad for ```PyramidStack``` plus:
   * ```tile_size``` (optional, default: 512): size of the tile used for partial image merging

```DepthMapStack```, Depth map focus stacking algorithm

Arguments for the constructor are:
   * ```map_type``` (optional)_ possible values are   ```DM_MAP_AVERAGE```  (default) and ```DM_MAP_MAX```. ```DM_MAP_MAX``` select for wach pixel the layer which has the best focus. ```DM_MAP_AVERAGE``` performs for each pixel an average of all layers weighted by the quality of focus.
   * ```energy``` (optional): possible values are ```DM_ENERGY_TENENGRAD``` (default), ```DM_ENERGY_LAPLACIAN```, ```DM_ENERGY_MOD_LAPLACIAN```, ```DM_ENERGY_SOBEL``` and ```DM_ENERGY_VARIANCE```. For more information, see [Sobel Derivatives](https://docs.opencv.org/4.x/d2/d2c/tutorial_sobel_derivatives.html), 
   * ```kernel_size``` (optional, default: 5): size in pixels of Laplacian kernel. Used only with the ```DM_ENERGY_MOD_LAPLACIAN``` ```energy``` option.
   * ```blur_size``` (optional, default: 5): size in pixels of the pre-Laplacian Gaussian blur. Used only with the ```DM_ENERGY_MOD_LAPLACIAN``` ```energy``` option.
   * ```weight_power``` (optiona, default: 1.0): apply a power law correction to energy weights. Note that this correction has only effect if ```map_type=DM_MAP_AVERAGE``` or if ```map_type=DM_MAP_MAX``` and ```temperature``` is greater than zero.
   * ```pyramid_smooth_size``` (optional, default: 1): smoothing size for the pyramid algorithm used for frames blending.
   * ```pyramid_levels``` (optional, default: 5): number of levels for the pyramid algorithm used for frames blending.
   * ```energy_smooth_size``` (optional, default: 1): size of energy smoothing. Note: larger values require slower computation.
   * ```energy_sigma_color``` (optiona, default: 0.8): controls how much energy values can differ while still smoothing together for the energy map.
   * ```energy_sigma_space``` (optional, default: 2): controls the spatial distance for smoothing neighborhood. Larger values require slower computation.
   * ```temperature``` (optional, default: 0): controls fusion transition. Lower value means sharper transitions. This correction is only applied if ```map_type=DM_MAP_MAX```.
   * ```plot_depth_map``` (optional, default: ```False```): produces a grayscale depth map and saves it in the ```plot_path``` folder.

For more details about bilateral filters applied to energy and weights map, see [Bilateral Filtering](https://www.geeksforgeeks.org/python/python-bilateral-filtering/).