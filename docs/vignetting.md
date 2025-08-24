# Vignetting correction

```python
job.add_action(Actions("vignette", [Vignetting(*options)])
```

Applies a radial luminosity correction determined from the mean pixel luminosity, spotting vignetting effect at the image borders. The correction is determined by modeling the mean luminosity as a function of the distance $r$ from the image center with the following asymmetric sigmoid model:

$\displaystyle i(r) = \frac{i_0}{1 + \exp(\exp(k(r - r_0)))}\,$

where the parameters $i_0$, $k$ and $r_0$ are estimated from the image luminosity data.
               
Arguments for the constructor of ```Vignetting``` are:
* ```r_steps``` (optional, default: 100): number of radial steps to determine mean pixel luminosity.
* ```black_threshold``` (optional, default: 1): apply correction only on pixels with luminosity greater than.
* ```max_correction``` (optional, default: 1): if less than one, the correction is rescaled in order to be at most the specified valye.
* ```plot_correction```  (optional, default: ```False```): if ```True```, plot vignetting correction curve for each frame.
* ```plot_summary```  (optional, default: ```False```): if ```True```, plot a summary histogram with the vignetting correction levels.
* ```enabled``` (optional, default: ```True```): allows to switch on and off this module.

## Extreme vignetting

⚠️ Vignetting may be very strong at the outer edges of the image in extreme macro photography with the use of [reversed lenses](https://digital-photography-school.com/reverse-lens-macro-close-up-photography-lesson-3/), and in the worse cases the outer part of the image becomes almost or completely black. In those cases, vignetting correction cannot recover those very dark areas, but recovers at least a uniform luminosity in the central part, and the image will require anyway to be cropped.

<img src='https://raw.githubusercontent.com/lucalista/shinestacker/main/img/extreme-vignetting.jpg' width="600" referrerpolicy="no-referrer">
