# Luminosity and color balance

```python
job.add_action(Actions("balance", [BalanceFrames(*options)])
```
  
Arguments for the constructor of ```BalanceFrames``` are:
*```channel``` (optional, default: BALANCE_LUMI): channels to be balanced. Possible values are: ```BALANCE_LUMI``` (default): balance equally for R, G and B channels, should be reasonably fine for most of the cases; ```BALANCE_RGB```: balance luminosity separately for R, G and B channels, it may be needed if some but not all of the images have a undesired color dominance; ```BALANCE_HSV```: balance saturation a luminosity value in the HSV (Hue, Saturation, brightness Value) representation, it may be needed in cases of extreme luminosity variation that affects saturation; ```BALANCE_HLS```: balance saturation a luminosity value in the HLS (Hue, Lightness, Saturation) representation, it may be needed in cases of extreme luminosity variation that affects saturation. Note that ```BALANCE_HSV``` and ```BALANCE_HLS``` are only supported for 8-bit images.
* ```mask_size``` (optional): if specified, luminosity and color balance is only applied to pixels within a circle of radius equal to the minimum between the image width and height times ```mask_size```, i.e: 0.8 means 80% of a portrait image width or landscape image height. It may beuseful for images with vignetting, in order to avoid including in the balance processing the outer darker pixels.
* ```intensity_interval``` (optional): if specifies, only pixels with intensity within the specified range are used. It may be useful to remove very dark areas or very light areas. Not used if ```MATCH_HIST``` is specified as value for ```corr_map```. The argument has to be a dictionary where one or both values corresponding to the keys ```min``` and ```max``` can be specified. The default values are:
```python
intensity_interval = {
    'min': 0,
    'max': -1
}
```
Note that for 8-bit images the maximum intensity is 255, while for 16-bit images the maximum intensity is 65536.
* ```subsample``` (optional, default: 8): extracts intensity histogram using every n-th pixel in each dimension in order to reduce processing time. By default, it takes one every 8 pixels in horizontal and vertical directions, i.e.: one every 100 pixels in total. This option is not ised if ```corr_map``` is equal to ```BALANCE_MATCH_HIST```.
* ```fast_subsampling``` (optional, default: ```False```): perform fast image subsampling without interpolation. Used if ```subsample``` is set to ```True```.
* ```corr_map``` (optional, default: ```BALANCE_LINEAR```, possible values: ```BALANCE_LINEAR```, ```BALANCE_GAMMA``` and ```MATCH_HIST```): specifies the type of intensity correction.
   * ```BALANCE_LINEAR```: a linear correction is applied in order to balance the average intensity of the corrected images to the reference image in the specified channels.
   * ```BALANCE_GAMMA```: a gamma correction, i.e.: a power law, is applied in order to balance the average intensity of the corrected images to reference image in the specified channels. The gamma correction avoids saturation of low or high intensity pixels which may occur for a linear coorection, but may introduce more distortion than a linear mapping.
   * ```BALANCE_MATCH_HIST```: the intensity histogram of the corrected image matches the histogram of the reference image in the specified channels. This options shoudl better be used with the value ```BALANCE_RGB``` for the ```channel``` option. If this option is specified, the options ```intensity_interval``` and ```subsample```are not used.  This option may be somewhat slow for 16-bit images.
* ```plot_histograms```  (optional, default: ```False```): if ```True```, plot hisograms for each image and for the reference frame.
* ```plot_summary```  (optional, default: ```False```): if ```True```, plot a summary of the corrections.
* ```enabled``` (optional, default: ```True```): allows to switch on and off this module. 
