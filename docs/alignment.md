# Alignment and registration

Automatically align, scale, translate, and rotate images, or apply full perspective correction.

All constants described below are contained in the object ```constants```, imported as:

```python
from shinestacker.config.constants import constants
```

Alignment actions can be added to a job as follows:

```python
job.add_action(Actions("align", [AlignFrames(*options)])
```
Arguments for the ```AlignFrames``` constructor are:
* ```feature_config``` (optional, default: ```None```): a dictionary specifying the following parameters, with the corresponding default values:
```python
feature_config = {
    'detector': constants.DETECTOR_SIFT,
    'descriptor': constants.DESCRIPTOR_SIFT,
    'sift_backend': constants.SIFT_BACKEND_OPENCV
}
```
* ```name``` (optional, default: empty): only used in the GUI as identifier
* ```enabled``` (optional, default: ```True```): enable or disable the sub-action
* ```detector``` (optional, default: ```DETECTOR_ORB```): the feature detector used to find matches. See [Feature Detection and Description](https://docs.opencv.org/4.x/db/d27/tutorial_py_table_of_contents_feature2d.html) for more details. Possible values are:
  * ```DETECTOR_SIFT```: [Scale-Invariant Feature Transform](https://docs.opencv.org/4.x/da/df5/tutorial_py_sift_intro.html)
  * ```DETECTOR_ORB``` (default): [Oriented FAST and Rotated BRIEF](https://docs.opencv.org/4.x/d1/d89/tutorial_py_orb.html)
  * ```DETECTOR_SURF```: [Speeded-Up Robust Features](https://docs.opencv.org/3.4/df/dd2/tutorial_py_surf_intro.html)
  * ```DETECTOR_AKAZE```: [AKAZE local features matching](https://docs.opencv.org/3.4/db/d70/tutorial_akaze_matching.html)
  * ```DETECTOR_BRISK```: [Binary Robust Invariant Scalable Keypoints](https://medium.com/analytics-vidhya/feature-matching-using-brisk-277c47539e8)
* ```descriptor``` (optional, default: ```DESCRIPTOR_ORB```): the feature descriptor used to find matches. Possible values are:
  * ```DESCRIPTOR_SIFT``` (default)
  * ```DESCRIPTOR_ORB```
  * ```DESCRIPTOR_AKAZE```
  * ```DESCRIPTOR_BRISK```

* ```sift_backend``` (optional, default: ```SIFT_BACKEND_OPENCV```): the implementation of SIFT, used only with the SIFT detector and descriptor. Possible values are:
  * ```SIFT_BACKEND_OPENCV``` (```'opencv'```, default): OpenCV on the CPU
  * ```SIFT_BACKEND_SILX``` (```'silx'```): [silx](https://github.com/silx-kit/silx) on an OpenCL device: the GPU if one is found, the CPU otherwise

  The OpenCL implementation requires the optional ```silx``` and ```pyopencl``` packages, which can be installed with ```pip install shinestacker[opencl]``` (the release installers and archives include them), and an OpenCL driver for the GPU or a CPU OpenCL runtime. In the GUI, the detector menu offers *SIFT (silx)* only when the packages are installed. If the packages or driver are missing, or the OpenCL run fails, a warning is issued and OpenCV is used instead. The log identifies the SIFT implementation at the start of alignment, for example: ```feature extraction: SIFT (silx, OpenCL: <device name>)```. It is much faster than OpenCV when features are extracted at full resolution (```subsample``` is set to 1 or ```resolution_target``` is large), and has similar overall performance with the default resolution target. Its results are not bit-reproducible between runs, but its transformations agree with OpenCV's to within a fraction of a pixel.

  For a quantitative comparison of the different methods, see the publication [S. A. K. Tareen and Z. Saleem, "A comparative analysis of SIFT, SURF, KAZE, AKAZE, ORB, and BRISK", doi:10.1109/ICOMET.2018.8346440](https://ieeexplore.ieee.org/document/8346440).

```matching_config``` (optional, default: ```None```): a dictionary specifying the following parameters and their default values:
```python
matching_config= {
    'match_method': constants.MATCHING_KNN,
    'flann_idx_kdtree': 2,
    'flann_trees': 5,
    'flann_checks': 50,
    'threshold': 0.75
}
```
* ```match_method``` (optional, default: ```MATCHING_KNN```): the method used to find matches. See [Feature Matching](https://docs.opencv.org/4.x/dc/dc3/tutorial_py_matcher.html) for more details. Possible values are:
  * ```MATCHING_KNN``` (default): [Feature Matching with FLANN](https://docs.opencv.org/3.4/d5/d6f/tutorial_feature_flann_matcher.html)
  * ```MATCHING_NORM_HAMMING```: [Use Hamming distance](https://docs.opencv.org/4.x/d2/de8/group__core__array.html#ggad12cefbcb5291cf958a85b4b67b6149fa4b063afd04aebb8dd07085a1207da727)
* ```flann_idx_kdtree``` (optional, default: 2): parameter used by the FLANN matching algorithm.
* ```flann_trees``` (optional, default: 5): parameter used by the FLANN matching algorithm.
* ```flann_checks``` (optional, default: 50): parameter used by the FLANN matching algorithm.
* ```threshold``` (optional, default: 0.75): parameter used to select good matches. See [Feature Matching](https://docs.opencv.org/4.x/dc/dc3/tutorial_py_matcher.html) for more details. 

* ```alignment_config``` (optional, default; ```None```): a dictionary specifying the following parameters, with the corresponding default values:
```python
alignment_config = {
    'transform': constants.ALIGN_RIGID,
    'align_method': constants.RANSAC,
    'rans_threshold': 5.0,
    'refine_iters': 100,
    'refit': constants.REFIT_NONE,
    'refit_threshold': 1.5,
    'align_confidence': 99.9,
    'max_iters': 2000,
    'border_mode': constants.BORDER_REPLICATE_BLUR,
    'border_value': (0, 0, 0, 0),
    'border_blur': 50,
    'interpolation': constants.INTER_CUBIC,
    'subsample': 0,
    'fast_subsampling': False,
    'min_good_matches': 100,
    'phase_corr_fallback': False,
    'abort_abnormal': False
}
```
* ```transform``` (optional, default: ```ALIGN_RIGID```): the transformation applied to register images. Possible values are:
  * ```ALIGN_RIGID``` (default): allows scale, translation, and rotation correction. Use this for images acquired with a tripod or microscope.
  * ```ALIGN_HOMOGRAPHY```: allows full perspective correction. Use this for images taken with a handheld camera.
* ```align_method``` (optional, default: ```RANSAC```): the method used to find matches. Valid options are:
  * ```RANSAC``` (*Random Sample Consensus*, default)
  * ```LMEDS``` (*Least Medians of Squares*)
* ```rans_threshold``` (optional, default: 5.0): parameter used when ```ALIGN_HOMOGRAPHY``` is chosen as the transformation. See [Feature Matching + Homography to find Objects](https://docs.opencv.org/3.4/d1/de0/tutorial_py_feature_homography.html) for more details.
* ```refine_iters``` (optional, default: 100): refinement iterations. Used only if ```transform=ALIGN_RIGID```.
* ```refit``` (optional, default: ```REFIT_NONE```): re-estimation of the transformation after RANSAC or LMEDS. Used only if ```transform=ALIGN_RIGID```. Possible values are:
  * ```REFIT_NONE``` (default): the estimate of ```align_method``` is used as it is.
  * ```REFIT_IRLS```: iteratively reweighted least squares with Tukey's biweight. Every match closer than ```refit_threshold``` contributes, weighted down as its residual grows, so matches that are only just inliers count less than with RANSAC's refinement. Lowers the sub-pixel error of the transformation. The estimate of ```align_method``` is kept if fewer than 10 matches are within the threshold, if the refit moves any prediction in the area covered by the matches by more than ```rans_threshold```, or if the refined transformation fails the usual geometric check.
* ```refit_threshold``` (optional, default: 1.5): residual in pixels, at the feature-matching scale (as ```rans_threshold```), beyond which a match gets no weight in the refit. Used only if ```refit=REFIT_IRLS```.
* ```align_confidence``` (optional, default: 99.9): confidence level of the alignment algorithm, in percent. Used only if ```transform=ALIGN_RIGID```.
* ```max_iters``` (optional, default: 2000): maximum number of iterations. Used only if ```transform=ALIGN_HOMOGRAPHY```. 
* ```subsample``` (optional, default: 0=automatic): subsamples the image for faster alignment. This can save time, especially for large images, but may reduce accuracy if only a small portion of the image is in focus.
* ```resolution_target``` (optional, default: 2): with ```subsample=0```, the image is subsampled for feature matching to about this many megapixels. Larger values match finer detail and take longer.
* ```fast_subsampling``` (optional, default: ```False```): perform fast image subsampling without interpolation. Used if ```subsample``` is set to ```True```.
* ```min_good_matches``` (optional, default: 100): if ```subsample```>1 and the number of good matches is below ```min_good_matches```, alignment is retried without subsampling. This improves robustness when the subsampling factor is too large.
* ```phase_corr_fallback``` (optional, default: ```False```): use phase-correlation alignment when there are too few matches to estimate the transformation. This algorithm is not very precise and may help only with blurred images.
* ```abort_abnormal``` (optional, default: ```False```): abort if an abnormal transformation is detected. By default, frames with abnormal transformations are skipped, and processing continues with the next frame.
* ```border_mode``` (optional, default: ```BORDER_REPLICATE_BLUR```): border mode. See [Adding borders to your images](https://docs.opencv.org/3.4/dc/da3/tutorial_copyMakeBorder.html) for more details.  Possible values are:
  * ```BORDER_CONSTANT```: pad the image with a constant value. The border value is specified with the parameter ```border_value```.
  * ```BORDER_REPLICATE```: the rows and columns at the very edge of the original are replicated to the extra border.
  * ```BORDER_REPLICATE_BLUR``` (default): same as above, but the border is blurred. The amount of blurring is specified by the parameter ```border_blur```.
* ```border_value``` (optional, default: ```(0, 0, 0, 0)```): border value. See [Adding borders to your images](https://docs.opencv.org/3.4/dc/da3/tutorial_copyMakeBorder.html) for more details.
* ```border_blur``` (optional, default: ```50```): amount of border blurring, in pixels. Only applied if ```border_mode``` is set to ```BORDER_REPLICATE_BLUR```, which is the default option.
* ```interpolation``` (optional, default: ```INTER_CUBIC```): interpolation used to warp the frames onto the reference frame. Possible values are:
  * ```INTER_LINEAR```: bilinear. Fast, but a sub-pixel shift softens fine detail by up to a factor two at the highest frequencies.
  * ```INTER_CUBIC``` (default): bicubic. Keeps more fine detail; recommended for focus stacking.
  * ```INTER_LANCZOS4```: Lanczos over 8x8 pixels. Slightly sharper than bicubic and slower.
* ```plot_summary```  (optional, default: ```False```): if ```True```, plot a summary histogram with number of matches in each frame. May be useful for inspection and debugging.
* ```plot_matches```  (optional, default: ```False```): if ```True```, draws the matches between each image and the reference frame. This may be useful for inspection and debugging.
* ```enabled``` (optional, default: ```True```): enables or disables this module.

## Automatic fallback

Some detector/descriptor combinations — most notably ORB/ORB, which is the
default — can occasionally fail to find enough matches, or to estimate a
reliable transformation. When this happens, alignment is automatically retried
with a more robust configuration (SIFT/SIFT with KNN matching). The fallback is
built into the code: it is not configurable and it is not exposed in the GUI.

A fallback attempt is logged as a warning for the affected frame.

If `plot_matches` is enabled, the match plot of the fallback attempt is saved
with a `-fb-sift` suffix (e.g. `align-matches-0042-fb-sift.png`), alongside the
plot of the primary attempt.

If the fallback also fails, the frame is handled as usual: it is skipped, or
recovered by phase correlation if `phase_corr_fallback` is enabled. No
success/failure message is emitted for the fallback itself: the existing
warnings cover both cases.

## Parallel processing

A class ```AlignFramesParallel``` implements alignment using parallel processing.
This class has extra parameters, in addition to the above ones:

* ```max_threads``` (optional, default: ```2```): number of parallel processes allowed. The number of actual threads will not be greater than the number of available CPU cores.
* ```chunk_submit``` (optional, default: ```True```): if enabled, submits images in chunks of at most ```max_threads```. If disabled, submits all images at once, which may improve performance at the cost of significantly higher memory use.
* ```bw_matching``` (optional, default: ```False```): performs matching on grayscale images to save memory. Preliminary tests indicate that the memory savings are small, so this option may be removed in the future.
* ```delta_max``` (optional, default: 2): maximum number of consecutive frames to skip when too few matches are found.

## Automatic selection of processing strategy

A class ```AlignFramesAuto``` implements alignment with either sequential or parallel processing, and automatically tunes parallel processing parameters.
This class has extra parameters, in addition to the above ones:

* ```mode``` (optional, default: ```auto```): can be ```auto```, ```sequential``` or ```parallel```.
* ```memory_limit``` (optional, default: 8 GiB): memory limit used to determine optimal processing parameters


## Allowed configurations

⚠️ Not all combinations of detectors, descriptors, and matching methods are allowed. An invalid combination raises an exception. The GUI prevents invalid combinations, but they may occur when using Python. The table below lists the allowed combinations and compares their CPU performance.

## CPU performance

⏳ The table below shows alignment times for two sample images at 2000×1300 resolution, using the allowed configuration combinations, from fastest to slowest. Slower methods may be more precise.

| Time (s) | Detector | Descriptor | Match method |
|----------|----------|------------|--------------|
| 0.0250   |  SURF    | ORB        | NORM_HAMMING |
| 0.0347   |  SURF    | BRISK      | NORM_HAMMING |
| 0.0469   |  ORB     | ORB        | NORM_HAMMING |
| 0.0471   |  ORB     | BRISK      | NORM_HAMMING |
| 0.1001   |  BRISK   | BRISK      | NORM_HAMMING |
| 0.1199   |  BRISK   | ORB        | NORM_HAMMING |
| 0.1604   |  SURF    | SIFT       | KNN          |
| 0.1966   |  BRISK   | SIFT       | KNN          |
| 0.2121   |  ORB     | SIFT       | KNN          |
| 0.2738   |  AKAZE   | AKAZE      | NORM_HAMMING |
| 0.2863   |  AKAZE   | ORB        | NORM_HAMMING |
| 0.2887   |  AKAZE   | BRISK      | NORM_HAMMING |
| 0.4075   |  AKAZE   | SIFT       | KNN          |
| 0.4397   |  SIFT    | SIFT       | KNN          |

SIFT performance can be improved by using a GPU with the optional
[```silx```](https://github.com/silx-kit/silx) implementation.
For performance comparison, see the conversation in [PR #100](https://github.com/lucalista/shinestacker/pull/100).

## References

For a detailed review of the various image registration methods, see the publication below:
*  [A Review of Keypoints’ Detection and Feature Description in Image Registration](https://onlinelibrary.wiley.com/doi/10.1155/2021/8509164), Scientific Programming 2021, 8509164, doi:10.1155/2021/8509164


