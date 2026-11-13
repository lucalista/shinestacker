# Luminosity and color balance

```python
job.add_action(Actions("balance", [BalanceFrames(*options)])
```
  
Arguments for the constructor of ```BalanceFrames``` are:
* ```name``` (optional, default: empty): only used in the GUI as identifier
* ```enabled``` (optional, default: ```True```): enable or disable the sub-action
* ```channel``` (optional, default: BALANCE_LUMI): channels to balance. Possible values are:
   - ```BALANCE_LUMI``` (default): balance equally for R, G and B channels, should be reasonably fine for most of the cases;
   - ```BALANCE_RGB```: balance luminosity separately for R, G and B channels, it may be needed if some but not all of the images have a undesired color dominance;
   - ```BALANCE_HSV```: balance saturation and luminosity value in the HSV (Hue, Saturation, brightness Value) color space, it may be needed in cases of extreme luminosity variation that affects saturation;
   - ```BALANCE_HLS```: balance saturation and luminosity value in the HLS (Hue, Lightness, Saturation) color space, it may be needed in cases of extreme luminosity variation that affects saturation;
   - ```BALANCE_LAB```: balance luminosity in the LAB color space.
* ```mask_size``` (optional): if specified, luminosity and color balancing is applied only to pixels within a circle whose radius is the smaller of the image width and height multiplied by ```mask_size```. For example, 0.8 means 80% of the width for a portrait image or 80% of the height for a landscape image. This can be useful for images with vignetting, so the darker pixels near the edges are excluded from balancing.
* ```intensity_interval``` (optional): if specified, only pixels within the given intensity range are used. This can exclude very dark or very bright areas. This option is not used when ```corr_map``` is set to ```MATCH_HIST```. The argument must be a dictionary with one or both of the keys ```min``` and ```max```. The default values are:
```python
intensity_interval = {
    'min': 0,
    'max': -1
}
```
Note that for 8-bit images the maximum intensity is 255, while for 16-bit images the maximum intensity is 65536.
* ```subsample``` (optional, default: 0=automatic): extracts the intensity histogram using every n-th pixel in each dimension to reduce processing time. This option is not used if ```corr_map``` is equal to ```BALANCE_MATCH_HIST```.
* ```fast_subsampling``` (optional, default: ```False```): perform fast image subsampling without interpolation. Used if ```subsample``` is set to ```True```.
* ```corr_map``` (optional, default: ```BALANCE_LINEAR```, possible values: ```BALANCE_LINEAR```, ```BALANCE_GAMMA``` and ```MATCH_HIST```): specifies the type of intensity correction.
   * ```BALANCE_LINEAR```: applies a linear correction to match the average intensity of the corrected images to that of the reference image in the specified channels.
   * ```BALANCE_GAMMA```: applies a power-law gamma correction to balance the average intensity of corrected images with the reference image in the specified channels. Gamma correction avoids the saturation of dark or bright pixels that may occur with linear correction, but it may introduce more distortion.
   * ```BALANCE_MATCH_HIST```: matches the intensity histogram of each corrected image to that of the reference image in the specified channels. This option is best used with ```BALANCE_RGB``` for the ```channel``` option. When enabled, ```intensity_interval``` and ```subsample``` are ignored. This option may be slow for 16-bit images.
* ```plot_histograms```  (optional, default: ```False```): if ```True```, plots histograms for each image and the reference frame.
* ```plot_summary```  (optional, default: ```False```): if ```True```, plots a summary of the corrections.
* ```enabled``` (optional, default: ```True```): enables or disables this module.
