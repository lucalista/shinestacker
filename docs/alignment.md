# Alignment and registration: scale, tanslation and rotation correction, or full perspective correction

```python
job.add_action(Actions("align", [AlignFrames(*options)])
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
    'match_method': MATCHING_KNN,
    'flann_idx_kdtree': 2,
    'flann_trees': 5,
    'flann_checks': 50,
    'threshold': 0.75
}
```
* ```match_method``` (optional): the method used to find matches. See [Feature Matching](https://docs.opencv.org/4.x/dc/dc3/tutorial_py_matcher.html) for more details. Possible values are:
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
    'align_methid': RANSAC,
    'rans_threshold': 5.0,
    'border_mode': BORDER_REPLICATE_BLUR,
    'border_value': (0, 0, 0, 0),
    'border_blur': 50
}
```
* ```transform``` (optional): the transformation applied to register images. Possible values are:
  * ```ALIGN_RIGID``` (default): allow scale, tanslation and rotation correction. This should be used for image acquired with tripode or microscope.
  * ```ALIGN_HOMOGRAPHY```: allow full perspective correction. This should be used for images taken with hand camera.
* ```align_method``` (optional): the method used to find matches. Valid options are:
  * ```RANSAC``` (*Random Sample Consensus*)
  * ```LMEDS``` (*Least Medians of Squares*)
* ```rans_threshold``` (optional, default: 5.0): parameter used if ```ALIGN_HOMOGRAPHY``` is choosen as tansformation, see [Feature Matching + Homography to find Objects](https://docs.opencv.org/3.4/d1/de0/tutorial_py_feature_homography.html) for more details.
* ```subsample``` (optional, default: 4): subsample image for faster alignment. Faster, but alignment could be less accurate.
* ```fast_subsampling``` (optiona, default: ```False```): perform fast image subsampling without interpolation. Used if ```subsample``` is set to ```True```.
* ```border_mode``` (optional, default: ```BORDER_REPLICATE_BLUR```): border mode. See [Adding borders to your images](https://docs.opencv.org/3.4/dc/da3/tutorial_copyMakeBorder.html) for more details.  Possible values are:
  * ```BORDER_CONSTANT```: pad the image with a constant value. The border value is specified with the parameter ```border_value```.
  * ```BORDER_REPLICATE```: the rows and columns at the very edge of the original are replicated to the extra border.
  * ```BORDER_REPLICATE_BLUR``` (default): same as above, but the border is blurred. The amount of blurring is specified by the parameter ```border_blur```.
* ```border_value``` (optional, default: ```(0, 0, 0, 0)```): border value. See [Adding borders to your images](https://docs.opencv.org/3.4/dc/da3/tutorial_copyMakeBorder.html) for more details.
* ```border_blur``` (optional, default: ```50```): amount of border blurring, in pixels. Only applied if ```border_mode``` is set to ```BORDER_REPLICATE_BLUR```, which is the default option.
* ```plot_summary```  (optional, default: ```False```): if ```True```, plot a summary histogram with number of matches in each frame. May be useful for inspection and debugging.
* ```plot_matches```  (optional, default: ```False```): if ```True```, for each image matches with reference frame are drawn. May be useful for inspection and debugging.
* ```enabled``` (optional, default: ```True```): allows to switch on and off this module.