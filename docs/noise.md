# Noisy pixel masking

First, the mask of noisy pixels has to be determined and stored in a PNG file using the action ```NoiseDetection```:

```python
job = StackJob("job", "E:/Focus stacking/My image directory/")
job.add_action(NoiseDetection("noise-map", input_path=["src"]))
job.run()
```

Run this job first with ```plot_histograms``` enabled. Adjust the plot range (the ```plot_range``` option) to determine suitable threshold values (```channel_thresholds```) for masking a reasonable number of pixels. Then add the ```MaskNoise``` sub-action before ```AlignFrames``` and ```BalanceFrames``` in the main focus-stacking job.

Arguments for the constructor of ```NoiseDetection``` are:
* ```name``` (optional, default: ```noise-map```): name of the action and the default name of the subdirectory within ```working_path``` where the noise map is written.
* ```input_path``` (optional): one or more subdirectories within ```working_path``` containing the input images. If not specified, the last output path is used, or, for the first action, the ```input_path``` specified when creating the ```StackJob```. If the ```StackJob``` specifies no ```input_path```, the first action must specify one.
* ```output_path``` (optional): the subdirectory within ```working_path``` where the noise map is written. If not specified, it defaults to ```name```.
* ```working_path``` (optional): the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.
* ```max_frames``` (optional): if provided, at most ```max_frames``` images are analyzed to extract noisy pixel mask.
* ```method``` (optional, default: ```norm_lab```): if ```rgb```, noisy pixels are determined separately for the R, G, and B channels. If set to ```norm_rgb```, the norm in RGB color space is used to identify noisy pixels. If set to ```norm_lab```, the norm in LAB color space is used.
* ```plot_path``` (optional, default: ```plots```): the directory within ```working_path``` that contains plots produced by the different actions.
* ```plot_histograms```  (optional, default: ```False```): if ```True```, plots the number of hot pixels per channel as a function of the applied threshold. This can help determine suitable threshold values.
* ```noisy_masked_px``` (optional, default: ```(100, 100, 100)```): target number of noisy pixels to mask. If set to a value greater than zero, the threshold is computed automatically to mask approximately that number of pixels. If ```method``` is ```norm```, only the first of the three thresholds is used.
* ```channel_thresholds``` (optional, default: ```(13, 13, 13)```): threshold values for detecting noisy pixels in the R, G, and B channels, respectively. Each threshold is used only if the corresponding value in ```noisy_masked_px``` is zero. If ```method``` is ```norm```, only the first of the three values is used.
* ```blur_size``` (optional, default: 5): amount of image blurring used for pixel detection.
* ```file_name``` (optional, default: ```hot_pixels.png```): noise map filename.
* ```enabled``` (optional, default: ```True```): enables or disables this module.

After the noisy pixel mask has been determined, noisy pixels are then masked adding the action ```MaskNoise``` to the ```Actions``` module:

```python
job.add_action(Actions("mask", [MaskNoise(*options)]))
```

Or as preliminary stage to more actions:
```python
job.add_action(Actions("align", [MaskNoise(),
                                 AlignFrames(),
                                 BalanceFrames(mask_size=0.9,
                                               intensity_interval={'min': 150, 'max':65385})]))
```

Note that if the number of pixels contained in the mask file (```noise_mask``` option) is greater than 1000, the job is aborted.

Arguments for the ```MaskNoise``` constructor are:
* ```name``` (optional, default: empty): used only as an identifier in the GUI
* ```enabled``` (optional, default: ```True```): enable or disable the sub-action
* ```noise_mask``` (optional, default: ```hot-rgb.png```): filename of the noise mask
*  ```kernel_size``` (optional, default: 3): blur size used to identify noisy pixels
*  ```method``` (optional, default: ```INTERPOLATE_MEAN```): possible values: ```INTERPOLATE_MEAN```, ```INTERPOLATE_MEDIAN```. Interpolate using mean or median of neighborhood pixels to replace a noisy pixel.
* ```enabled``` (optional, default: ```True```): enables or disables this module.
