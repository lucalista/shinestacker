# Noisy pixel masking

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
job.add_action(Actions("mask", [MaskNoise(*options)]))
```

Or as preliminary stage to more actions:
```python
job.add_action(Actions("align", [MaskNoise(),
                                 AlignFrames(),
                                 BalanceFrames(mask_size=0.9,
                                               intensity_interval={'min': 150, 'max':65385})]))
```

Arguments for the constructor of ```NoiseDetection``` are:
* ```noise_mask``` (optional, default: ```noise-map/hot-rgb.png```): filename of the noise mask
*  ```kernel_size``` (optional, default: 3): blur size use to extract noisy pixels
*  ```method``` (optional, default: ```INTERPOLATE_MEAN```): possible values: ```INTERPOLATE_MEAN```, ```INTERPOLATE_MEDIAN```. Interpolate using mean or median of neighborhood pixels to replace a noisy pixel.
