# Focus Stacking

```python
job.add_action(FocusStack(name, stacker, *options))
```
Arguments for the ```FocusStack``` constructor are:
* ```name```: the name of the action, used for printout, and possibly for output path
* ```stacker```: an object defining the focus-stacking algorithm. It can be ```PyramidStack```, ```PyramidTilesStack```, or ```DepthMapStack```. See below for the available algorithms.
* ```input_path``` (optional): the subdirectory within ```working_path``` that contains the input images. If not specified, the last output path is used, or, for the first action, the ```input_path``` specified when creating the ```StackJob```. If the ```StackJob``` specifies no ```input_path```, the first action must specify one.
* ```output_path``` (optional): the subdirectory within ```working_path``` where output images are written. If not specified, it is set to ```name```.
* ```working_path```: the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.
* ```plot_path``` (optional, default: ```plots```): the directory within ```working_path``` that contains plots produced by the algorithm.
* ```exif_path``` (optional): if specified, EXIF data are copied to the output file from a file in this directory. If not specified, the source directory used as input for the first action is used. If set to ```''```, no EXIF data is saved.
* ```denoise_amount``` (optional; default: 0): if greater than 0, a denoising algorithm is applied. Values from 0.75 to 1.00 provide modest noise reduction without appreciably reducing detail. Denoising may be useful for 8-bit images or images taken at high ISO. 16-bit images taken at low ISO usually do not need denoising. See [Image Denoising](https://docs.opencv.org/3.4/d5/d69/tutorial_py_non_local_means.html) for more details.
* ```sharpen_amount_percent``` (optional; default: 0): if > 0, a unsharp mask algorithm is applied. Values from 50% up apply a visible amount of sharpening.
* ```sharpen_radius``` (optional; default: 1): specifies the radius, in pixels, of the unsharp mask algorithm.
* ```sharpen_threshold``` (optional; default: 0): specifies the threshold value of the unsharp mask algorithm.
* ```naming_mode``` (optional, default: `'PREFIX'`): Determines which filename mode to use. Can be `'PREFIX'` or `'TEMPLATE'`. When `'PREFIX'`, the `prefix` parameter is used and `output_file_template` is ignored. When `'TEMPLATE'`, the `output_file_template` is used and `prefix` is ignored. This parameter resolves conflicts when both are present in a project file.
* ```prefix``` (optional): if specified, this string is prepended to the filename. This can be useful when running multiple algorithms and using different output filenames. It cannot be used with ```output_file_template```.
* ```output_file_template``` (optional): defines a template for the output filename. Alternative to `prefix` - cannot be used together. Supports `{method}`, `{input_count}`, `{input_prefix}`, `{input_min}`, and `{input_max}` placeholders.
* ```enabled``` (optional, default: ``True```): enables or disables this module.
* ```scratch_output_dir``` (optional, default: ```True```): scratch output directory before processing. This avoids that existing files pollute the output.
* ```delete_output_at_end``` (optional, default: ```False```): deletes the output after processing, freeing disk space when the step is intermediate and not part of the final output.

## Focus Stacking in bunches of frames

```python
job.add_action(FocusStackBunch(name, stacker, *options))
```
Arguments for the ```FocusStackBunch``` constructor are:
* ```name```: the name of the action, used for printout, and possibly for output path
* ```stacker```: an object defining the focus-stacking algorithm. It can be ```PyramidStack```, ```PyramidTilesStack```, or ```DepthMapStack```. See below for the available algorithms.
* ```input_path``` (optional): the subdirectory within ```working_path``` that contains the input images. If not specified, the last output path is used, or, for the first action, the ```input_path``` specified when creating the ```StackJob```. If the ```StackJob``` specifies no ```input_path```, the first action must specify one.
* ```output_path``` (optional): the subdirectory within ```working_path``` where output images are written. If not specified, it is set to ```name```.
* ```working_path```: the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.
* ```plot_path``` (optional, default: ```plots```): the directory within ```working_path``` that contains plots produced by the algorithm.
* ```exif_path``` (optional): if specified, EXIF data are copied to the output file from a file in this directory. If not specified, the source directory used as input for the first action is used. If set to ```''```, no EXIF data is saved.
* ```frames``` (optional, default: 10): the number of frames that are fused together. 
* ```overlap``` (optional, default: 0): the number of overlapping frames between a bunch and the following one. 
* ```denoise_amount``` (optional): if specified, a denoising algorithm is applied. Values from 0.75 to 1.00 provide modest noise reduction without appreciably reducing detail. Denoising may be useful for 8-bit images or images taken at high ISO. 16-bit images taken at low ISO usually do not need denoising. See [Image Denoising](https://docs.opencv.org/3.4/d5/d69/tutorial_py_non_local_means.html) for more details.
* ```naming_mode``` (optional, default: `'PREFIX'`): Determines which filename mode to use. Can be `'PREFIX'` or `'TEMPLATE'`. When `'PREFIX'`, the `prefix` parameter is used and `output_file_template` is ignored. When `'TEMPLATE'`, the `output_file_template` is used and `prefix` is ignored. This parameter resolves conflicts when both are present in a project file.
* ```prefix``` (optional): if specified, this string is prepended to the filename. This can be useful when running multiple algorithms and using different output filenames. It cannot be used with ```output_file_template```.
* ```output_file_template``` (optional): defines a template for the output filename. Alternative to `prefix` - cannot be used together. Supports `{method}`, `{input_count}`, `{input_prefix}`, `{input_min}`, `{input_max}`, and `{bunch_index:03d}` placeholders.
* ```enabled``` (optional, default: ```True```): enables or disables this module.
* ```scratch_output_dir``` (optional, default: ```True```): scratch output directory before processing. This avoids that existing files pollute the output.
* ```delete_output_at_end``` (optional, default: ```False```): deletes the output after processing, freeing disk space when the step is intermediate and not part of the final output.

## Template Placeholders

When using `output_file_template`, the following placeholders are available:

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{method}` | Stacking algorithm name | `pyramid` or `depth_map` |
| `{input_count}` | Total number of input frames | `9` |
| `{input_prefix}` | Common prefix of input filenames | `flies_` |
| `{input_min}` | Variable part of first input filename | `0000` |
| `{input_max}` | Variable part of last input filename | `0008` |
| `{bunch_index:format}` | Bunch index with optional format specifier (FocusStackBunch only) | `{bunch_index:03d}` → `001`<br>`{bunch_index:04d}` → `0001` |

**Examples** with input files `flies_0000.jpg` to `flies_0008.jpg`:

| Template | Result |
|----------|--------|
| `"{input_prefix}{input_min}-{input_max}_{input_count}frames"` | `flies_0000-0008_9frames.tif` |
| `"{method}_{input_count}frames_stack"` | `pyramid_9frames_stack.tif` |
| `"{method}_{input_min}-{input_max}"` | `pyramid_0000-0008.tif` |
| `"{input_prefix}{input_min}-{input_max}_bunch-{bunch_index:03d}"` | `flies_0000-0008_bunch-001.tif` |
| `"{input_prefix}{input_min}-{input_max}_bunch-{bunch_index:04d}"` | `flies_0000-0008_bunch-0001.tif` |

## Stack algorithms

```PyramidStack```, a Laplacian-pyramid focus-stacking algorithm

Arguments for the constructor are:
   * ```pyramid_min_size``` (optional, default: 32)
   * ```kernel_size``` (optional, default: 5)
   * ```gen_kernel``` (optional, default: 0.4)
   * ```float_type``` (optional, default: ```FLOAT_32```, possible values: ```FLOAT_32```, ```FLOAT_64```): precision for internal image representation

```PyramidTilesStack```, a pyramid algorithm that uses I/O-buffered tile merging to optimize memory use for large files

Tiles include overlapping pixels for focus-energy calculation so that internal tile boundaries
are treated like the full-image pyramid. The overlap uses the convolution kernel's radius and
requires slightly more temporary disk space.

Arguments for the constructor are, in addition to the ones for ```PyramidStack```:
   * ```tile_size``` (optional, default: 512): size of each tile
   * ```n_tiled_layers``` (optional, default: 2): number of layers to tile. Usually, the last one or two layers use the most memory.
   * ```max_threads``` (optional, default: number of cores, up to a maximum of 8): maximum number of threads used for parallel processing. The actual number of threads does not exceed the number of available cores.
* ```chunk_submit``` (optional, default: ```True```): if enabled, submits tasks in chunks of at most ```max_threads```. If disabled, submits all tasks at once, which may improve performance at the cost of significantly higher memory use.


```PyramidAutoStack```, a pyramid algorithm that can automatically switch from in-memory processing to I/O-buffered tiling.

Arguments for the constructor are, in addition to the ones for ```PyramidTilesStack```:
   * ```mode``` (optional, default: ```auto```): can be ```auto```, ```memory``` or ```tiled```.
   * ```memory_limit``` (optional, default: 8 GiB): memory limit used to determine optimal processing parameters


The constructor accepts the same arguments as ```PyramidStack```, plus:
   * ```tile_size``` (optional, default: 512): size of the tile used for partial image merging

```DepthMapStack```, a depth-map focus-stacking algorithm

Arguments for the constructor are:
   * ```map_type``` (optional): possible values are ```DM_MAP_AVERAGE``` and ```DM_MAP_MAX``` (default). ```DM_MAP_MAX``` selects the best-focused layer for each pixel. ```DM_MAP_AVERAGE``` computes a weighted average of all layers for each pixel, based on focus quality.
   * ```energy``` (optional): possible values are ```DM_ENERGY_TENENGRAD```, ```DM_ENERGY_LAPLACIAN``` (default), ```DM_ENERGY_MOD_LAPLACIAN```, ```DM_ENERGY_SOBEL``` and ```DM_ENERGY_VARIANCE```. For more information, see [Sobel Derivatives](https://docs.opencv.org/4.x/d2/d2c/tutorial_sobel_derivatives.html), 
   * ```kernel_size``` (optional, default: 5): size in pixels of Laplacian kernel. Used only with the ```DM_ENERGY_LAPLACIAN``` ```energy``` option.
   * ```blur_size``` (optional, default: 5): size in pixels of the pre-Laplacian Gaussian blur. Used only with the ```DM_ENERGY_LAPLACIAN``` ```energy``` option.
   * ```weight_power``` (optional, default: 1.0): applies a power-law correction to energy weights. This correction only has an effect if ```map_type=DM_MAP_AVERAGE``` or if ```map_type=DM_MAP_MAX``` and ```temperature``` is greater than zero.
   * ```pyramid_smooth_size``` (optional, default: 1): smoothing size for the pyramid algorithm used to blend frames.
   * ```pyramid_levels``` (optional, default: 5): number of levels in the pyramid algorithm used to blend frames.
   * ```energy_smooth_size``` (optional, default: 1): size of energy smoothing. Note: larger values require slower computation.
   * ```energy_sigma_color``` (optional, default: 0.8): controls how much energy values can differ while still being smoothed together in the energy map.
   * ```energy_sigma_space``` (optional, default: 2): controls the spatial distance for the smoothing neighborhood. Larger values require more computation time.
   * ```energy_gauss_sigma``` (optional, default: 0, i.e. off): standard deviation in pixels of a Gaussian smoothing of each frame's energy map, applied after the optional bilateral smoothing. In areas with little texture (a plain background, a mount) the per-pixel energy is dominated by sensor noise, and the frame with the highest energy is then close to random. Averaging the energy over a few pixels lets the real texture decide; values around 8 worked well on 33 MP frames. It is fast at any value, unlike a large ```energy_smooth_size```.
   * ```temperature``` (optional, default: 0): controls fusion transition. Lower value means sharper transitions. This correction is only applied if ```map_type=DM_MAP_MAX```.
   * ```plot_depth_map``` (optional, default: ```False```): produces a grayscale depth map and saves it in the ```plot_path``` folder.
   * ```max_threads``` (optional, default: number of cores): number of threads that read and process frames in parallel. Frames are still combined in frame order, so the result does not depend on this number. Fewer frames are processed at once if their buffers would exceed ```memory_limit```.
   * ```memory_limit``` (optional, default: 8 GB): memory budget. In ```mode='auto'```, energy maps are kept on disk when needed to stay within this limit; it also limits how many frames are processed in parallel.

For more details about bilateral filters applied to energy and weights map, see [Bilateral Filtering](https://www.geeksforgeeks.org/python/python-bilateral-filtering/).