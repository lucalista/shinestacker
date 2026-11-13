# Changelog

## [v1.18.x] - Unreleased

### Added
- package the amber flies sample images as a downloadable release asset (#110)

### Changed
- vectorised the local entropy and deviation used to fuse the coarsest pyramid level (`get_fused_base`): same output, ~200x faster for this step, no meaningful memory change
- project and settings files are written with the standard `json` module (atomic write) instead of `jsonpickle`; project file version 2. Version 1 files are still readable, legacy `py/tuple` and `py/set` tags are converted to lists, files requiring object instantiation are rejected; `jsonpickle` dependency removed

## [v1.18.0] - 2026-11-13
**Performance improvement: OpenCL SIFT, and output metadata enhancement**

### Added
- optional OpenCL SIFT implementation (silx) for alignment: `sift_backend` option, `pip install shinestacker[opencl]`; included in the executables (#100)
- write a readable ImageDescription for TIFF, JPEG and PNG output EXIF data (#109)

## [v1.17.6] - 2026-11-04
**Fixes and performance improvements**

## Fixed
- launch external viewer/file manager with a clean environment (#95)
- GPS exif data in TIFF format (#96)
- dialog crash when adding FocusStack manually (#97)
- crash when using ```-x``` option (#100)
- reset of border value in align module dialog (#100)
- action dialogs: reset restores combo-box defaults (#102)
- depth map:
    - ```mod_laplacian``` uses second derivatives (#103)
    - average weights where no frame has energy (#104)
    - the weights replace the energy cube band by band (#106)

### Added
- optional robust refit of the rigid transform after RANSAC (#101)

### Changed
- code speedup:
    - compute the features of each frame once in parallel alignment (#107)
    - alignment: use a single-channel coverage mask (#105)
- minor code cleanup

---

## [v1.17.5] - 2026-10-29
**Fixes, including RAW format input, and new CLI options**

### Fixed
- crash while reading raw file input (#91)
- suppress console warnings
- unknown filename undefined in CLI project start (```-p <path> --start```) (#94)

### Added
- new CLI options (default behaviour unchanged) (#94):
    - ```-b/--bunches```: insert a "focus stack bunch" step between align/balance and the final pyramid stack, using the new-project dialog defaults (10 frames, overlap 2)
    - ```--bunch-frames N``` (1–20) and ```--bunch-overlap N``` (0–10): override the defaults; either one enables bunches implicitly; overlap must be smaller than frames

---

## [v1.17.4] - 2026-10-26
**Fixed external package metadata**

### Fixed
- fixed ```tifftools``` metadata for the Linux and Windows builds. The previous release fixed it only for macOS (#89, #90)

---

## [v1.17.3] - 2026-10-25
**Fixed external package metadata**

### ⚠️ DEPRECATED on Windows and Linux
— **use 1.17.4**

### Fixed
- fixed ```tifftools``` metadata for build. The previous release crashed at startup due to this build problem (#87, #89)

---

## [v1.17.2] - 2026-10-24 
**User pull requests and more fixes**

### ⚠️ DEPRECATED
— **use 1.17.4**

### Fixed
- pylint CI script fixed for pull requests, and updated to python 3.14
- fixed some default parameter values in documentation (#78)
- alignment retries using SIFT detector and descriptor methods if ORB fails (#77)
- TIFF output: write Exif tags into the Exif IFD (#84)
- spawn child processes in the background (#85)

### Changed
- FocusStack: keep the source colour profile without EXIF copying (#79)
- Round instead of truncating when converting to integer pixels (#80)
- DepthMapStack: optional Gaussian smoothing of the energy maps (#81)
- Alignment: make the warp interpolation selectable (#82)
- Default alignment interpolation method changed to cubic (#82)
- Alignment: SIFT/AKAZE threads in auto mode, and a working resolution_target option (#83)
- Enhanced RAW formats configurable settings (#86)

---

## [v1.17.1] - 2026-10-20
**Security vulnerability fixed**

### Fixed
- fixed a potential vulnerability caused by misuse of project metadata by disabling the external retouch app. This feature was only used for internal purposes and does not affect normal usage.

---

## [v1.17.0] - 2026-09-06
**RGBA / alpha-channel support for the focus stackers (#69)**

### Added
- `PyramidStack`, `PyramidTilesStack`, `DepthMapStack` and `PyramidAutoStack`
  now carry a 4th (alpha) channel through alignment and fusion. RGBA input
  frames (16-bit TIFF / PNG) produce an RGBA stacked result. Colour is
  premultiplied by alpha before pyramids are built (so transparent regions
  contribute no focus energy) and un-premultiplied on output.
- Focus metrics (entropy / deviation / Laplacian energy / depth-map weights) are
  computed from the RGB channels only; the alpha channel is fused with the same
  per-pixel frame selection / weights as the colour, so colour and matte never
  diverge.
- `AlignFrames` carries alpha through the warp and forces revealed border area
  to fully transparent; `BalanceFrames` colour-corrects RGB only; `denoise` and
  `unsharp_mask` pass alpha through untouched.
- A stacker that cannot carry alpha (`BaseStackAlgo.supports_alpha = False`)
  raises a clear error on RGBA input instead of silently dropping the channel.
- `algorithms.utils`: `has_alpha`, `split_alpha`, `merge_alpha`, `drop_alpha`.

---

## [v1.16.3] - 2026-08-22

### Fixed
- updated PyPI publishing script to prevent warning message

---

## [v1.16.2] - 2026-08-22
**New output file template format plus bug fixes**

### Fixed
- incorrect GUI widget creation when adding an action to a job in the modern project view (#68)

### Added
- users can specify the stack output filename format using a template, for example: `{input_prefix}{input_min}-{input_max}_{input_count}-frames` (#66)

---

## [v1.16.1] - 2026-08-10
**Bug fixes**

### Fixed
- default zoom was mistakenly off (#60)
- fixed scrollbar appearance (#61)
- updated installation documentation using ```pip```

---

## [v1.16.0] - 2026-08-07
**Added user-requested improvements and bug fixes**

### Fixed
- cursor no longer disappears on scrollbars in retouch mode (#57)
- when the zoom is reset to actual size (Ctrl+R), the image is centered correctly, preventing jumps when changing layers (#58)
- image centering issue when zooming with Ctrl++ (#58)
- image panning (Space + drag or the new key P) works when the mouse is in either view in the side-by-side view mode
- fixed a warning in a unit test

### Changed
- removed uv.lock file since uv is not supported and uv.lock is not updated in the development workflow

### Added
- new configurable setting: alignment transform; valid options are rigid and homography (#55)
- full screen view menu option added to project window
- full screen shortcut is Ctrl + Cmd + F or F11 on Windows (#57)
- more shortcuts added for zoom in/out: +, =, Ctrl-+ and Ctrl-= could all zoom in, -, Ctrl-- could all zoom out (#57)
- added an option to automatically open retouch mode after a job runs. The setting is saved and can be enabled at startup, regardless of the default settings, with the --enable-auto-retouch (-e) command-line argument (#56)
- added the --start (-s) command-line option to automatically start a specified project. It works only with the -f or -p options (#54)
- in retouch mode, P toggles pan mode as an alternative to Space + drag (#57)
- in retouch mode, the "Fit to Window" action (Ctrl+0) automatically fits the image to the window when the window is resized. This also happens the first time an image is opened for retouch (#58).

----

## [v1.15.5] - 2026-07-05
**Forced OpenCV compatibility**

### Fixed
- cv2 version forced to be < 5.0.0 for compatibility

---

## [v1.15.4] - 2026-05-21
**Bug fixes**

### Fixed
- input paths no longer become empty when they contain a trailing "/" or "\" on Windows (#45, #46). Additional fix following release 1.15.3.
- fixed job's input path selector in case of trailing "/" or "\" on Windows (#45, #46). 

---

## [v1.15.3] - 2026-05-14
**Fixes and minor GUI improvements**

### Fixed
- input path no longer becomes empty when it contains a trailing "/" or "\" on Windows (#45, #46)
- added fallback protection to prevent an empty module base name when the input path is empty (#45, #46)
- project templates with folder parameters pointing to non-existent paths now prompt the user for input instead of failing when the job runs (#47)

### Changed
- improved user messages when opening a project template that contains missing folder paths (#47)

---

## [v1.15.2] - 2026-05-03
**Fixes, updates, and cleanup**

### Fixed
- updated release and pylint scripts with more recent external script versions to prevent warning messages
- robustness fix to command line option -p/--path (#38)
- fixed default dialog path when opening image files in retouch mode (#36, #43)
- fixed configurable parameter dialog for integer tuples

### Changed
- added new setting: "Raw Formats" > "Auto-brightness threshold" parameter (default: 1%) (#33)
- improved command line options: -p/--path selects the input path for a new project; -i/--image-folder selects one or more image folders to be opened in retouch mode
- improved help text for command line arguments (#35)
- minor code cleanup

---

## [v1.15.1] - 2026-04-22
**Bug fixes and user-requested improvements**

### Fixed
- fixed bugs and improved implementation of the "Open Template" action (#31)

### Changed
- added new setting: "Raw Formats" > "Automatic Brightness" to enable or disable automatic brightness correction (default: true) (#33)
- required package versions pillow>=12.2.0 (for release build) and pytest>=9.0.3 (for CI tests) to fix security warnings 

---

## [v1.15.0] - 2026-04-09
**Project template support, minor fixes and updates**

### Added
- menu entry "Open Project As Template": allows users to rename jobs and customize input selection (#31)

### Fixed
- required package version Pygments>=2.20.0 to fix a security warning
- updated release and test scripts with more recent action versions

---

## [v1.14.4] - 2026-03-22
**Minor GUI fixes and code cleanup**

### Fixed
- upper bound to RAM settings increased from 64 to 1024 GBytes (#30)
- upper bound to CPU number increased from 8 to 256 (#30)

### Changes
- minor code cleanup
- updated CI pylint script

---

## [v1.14.3] - 2026-03-07
**GUI improvements and fixes from pull requests**

### Fixed
- added support for uppercase file extensions (e.g., .JPG and .TIFF) in file dialogs on case-sensitive Linux systems (PR #26)
- EXIF Metadata Handling and Resolve Qt Conflict (PR #27)
- .gitignore ignores auto-generated files (PR #27)
- resolution of Qt/xcb Conflict (PR #27)

### Changes
- robust EXIF Metadata Handling (PR #27)

---

## [v1.14.2] - 2026-02-18
**Fixes and GUI improvements**

### Added
- renamed elements in menu actions
- a "Run Job" icon in job GUI widgets

### Fixed
- retained the last opened path when opening or saving files
- no more keyboard shortcut conflicts
- safe DepthMap implementation when temperature is exactly zero
- fixed a failure in the bunches algorithm when a single frame is selected
- several GUI issues and minor usability glitches

### Changes
- rationalized keyboard shortcuts and menu actions
- copied elements now have the suffix " (copy)" after their names
- final stack images have a suffix indicating the algorithm type: "_pyram" or "_depmp" (#24)
- cleaned up signal handling
- DepthMap: minor algorithm optimization and improved default parameter values for sharper images
- visually improved GUI icons

---

## [v1.14.1] - 2026-02-11
**Improved DepthMap and requested features**

### Added
- input folder path in the default settings (#15)
- menu action to delete intermediate image folders; this action is also triggered when closing a project and prompts the user to free disk space (#17)
- icon in the top bar to more easily start a retouch session

### Fixed
- fixes and improvements to RAW format support (#12)
- improved default depth map settings for sharper fused images (#8)
- support for opening multiple input files via the `-f` option (filenames separated by `;`)
- several GUI issues and minor usability glitches

### Changes
- trap `UnidentifiedImageError` from `PIL.Image.open` when loading images to retrieve EXIF data
- file open/save dialogs now remember the last visited path during the current session
- improved the performance of the pyramid-stacking algorithm
- dropped support for macOS on Intel x64 because free build machines are unavailable (#18)

---

## [v1.14.0] - 2026-02-04
**Native RAW format support, GUI improvements, and internal refactoring**

### Added
- native RAW image formats support via rawpy (#12)
- redo operation support in project GUI
- added keyboard shortcuts for redo (Ctrl + Shift + Z or Ctrl + Y) and for moving elements (Shift + Ctrl + arrow keys)

### Fixed
- various GUI issues and usability glitches

### Changes
- better image arrangement in modern project view
- internal code refactoring with significant architectural improvements in the GUI area, enabling future developments

---

This page reports the main releases only and the main changes therein.

## [v1.13.4] - 2026-01-28
**GUI fixes and improvements**

### Added
- visual icon representing stacking algorithm, ▲ for pyramid or ■ for depth map (#11)
- expert options toggle added in new project dialog
- retouch job action has an entry in top menu
- project run information is saved persistently with the project file
- menu entry to clear project run information
- support ICC profile in EXIF data

### Fixed
- fixed an automatic subsampling factor that could reduce alignment quality in some cases (#7)
- added fault protection for depth map plot
- input filepaths explicitly sorted alphabetically
- minor GUI fixes and improvements

### Changed
- minor optimization: skip stacking if input has a single frame
- in the project area, the delete shortcut is now the backspace key instead of the delete key

---

## [v1.13.3] - 2026-01-21

**Fixes and minor GUI improvements, cleanup and refactoring**

### Added
- optional plot of the estimated depth map for focus stacking with the DepthMap algorithm
- improved navigation in the classic project GUI: use the arrow keys to move from jobs to actions, and press Enter/Return to edit.
- keyboard shortcuts for main project and retouch menu main entries
- RAW file extensions are now recognized, but a warning is issued because support depends on future updates to the rawpy package

### Fixed
- fixed various bugs in the project-editing GUI
- required NumPy >=2.4.1 to prevent potential bugs in OpenCV caused by inconsistent versions

### Changed
- removed duplicate code from the classic and modern project GUI views
- minor optimization of pyramid algorithm
- allowed latest OpenCV version, 4.13.0.90

---

## [v1.13.2] - 2026-01-13

**Implemented some GUI missing features**

### Fixed
- undoing a cut or delete in the modern view restores the full run progress, including image thumbnails and the progress bar
- cut element in classic view now works as expected

### Changed
- removed redundant stop button from classic run job window
- refactored and cleaned up the project GUI components

---

## [v1.13.1] - 2026-01-06

**Main stability reengineering of the project GUI: improvements and fixes**

### Fixed
- correct and consistent GUI response with update of both views when the project is modified
- refreshed the GUI with minimal updates to prevent accidental deletion of job run information

### Changed
- extensively refactored and cleaned up the project GUI components

---

## [v1.13.0] - 2025-12-29

**This release introduces a redesigned project GUI with an integrated editing and run workflow.
Project modules now display their outputs directly inside their corresponding boxes, making complex pipelines easier to understand and manage.
The classic project view is still available and can be enabled at any time from the View menu.**

### Added
- new integrated project editing view with a redesigned interactive GUI; the classic view is still available via *View > View Mode > Classic*
- extended status bar messaging
- stop button added to the top toolbar, alongside run controls

### Fixed
- various GUI issues in the project editing view
- missing features restored in the classic project editing view
- prevented output conflicts by checking for multiple modules sharing the same output path

### Changed
- system monitor widgets moved from the run window to the main window toolbar
- improved clarity and consistency of status messages
- significant refactoring of GUI-related code
- the new project dialog enables focus bunches by default if the estimated memory requirements exceeds a predefined threshold

---

## [v1.12.0] - 2025-12-21

**New tonemapping filter**

### Added
- new tonemapping filter
- startup dialog prompts an update if a new version is available
- stop button available in the top bar

### Fixed
- fixed LAB and HLS color-space conversions for 16-bit images
- fixed software version retrieval when SSL fails in the About dialog
- pinned OpenCV to version 4.11 to prevent a bug in 16-bit HLS color-space conversion

---

## [v1.11.3] - 2025-12-10
**Bug fix release**

### Fixed
- multithread conflict in plot generation
- prevented saving a noisy-pixel map that contains too many pixels
- missing match plot in parallel alignment module
- plot images are saved as PNG by default to avoid issues generating many PDF files with Matplotlib. PDF output can be enabled in the settings.
- added more exception handling to the focus-stacking algorithm
- minor logging printout fix

---

## [v1.11.2] - 2025-12-04
**Bug fix release**

### Fixed
- fixed threshold parameter for unsharp mask filter
- fixed frames import in retouch mode
- reverted to sequential pyramid focus stacking when temporary disk space is insufficient
- prevented failure when a single file is selected for parallel alignment
- added protection against invalid file content
- added protection against invalid paths on Windows

### Changed
- optimized temporary disk cache for parallel pyramid focus stacking

---

## [v1.11.1] - 2025-11-28
**fixes to new DepthMap algorithm**

### Added
- optional sharpen filter after focus stacking stage

### Fixed
- fault-tolerant argument lists in modules prevent potential issues when reading project files from older releases

### Changed
- improved DepthMap layer blending using the pyramid method
- optimized the depth-map algorithm and added I/O buffering to reduce memory requirements

---

## [v1.11.0] - 2025-11-22
**improved DepthMap algorithm**

### Added
- optimized the depth-map algorithm with additional energy calculations and blending modes
- new customizable parameters for depth map algorithm
- customizable temporary scratch disk area in settings

### Fixed
- added protection to persistent settings against potentially dangerous data types

### Changed
- some minor fixes and code cleanup
- minor GUI refinements

---

## [v1.10.1] - 2025-11-19
**Enhanced noise detection and interface improvements**

### Added
- brush luminosity correction in retouch mode  
- new noise-detection methods `norm_lab` and `norm_rgb` as alternatives to the default `rgb`  
- automatic threshold estimation in the noise detection module  
- double-click on processing-status boxes opens the corresponding processed frame  
- extended set of parameters stored in persistent configuration

### Fixed
- incorrect configuration parameters in the noise-masking module  
- noisy-pixel detection now works correctly for 16-bit images  
- a warning is now shown when attempting to load more than 20 image frames
- protected the pyramid-stacking algorithm against temporary-disk exhaustion
- various user-interface issues  
- alignment warning messages restored

### Changed
- optimized vignetting algorithm  
- improved settings persistence by saving only parameters that differ from defaults  
- project-window colors now update correctly when the desktop theme changes  
- image previews now open on double-click instead of single-click  
- refactored default-parameter configuration code

---

## [v1.10.0] - 2025-11-19 (⚠️ DEPRECATED — use 1.10.1)
**One source file missing; replaced by 1.10.1.**

---

## [v1.9.7] - 2025-11-13
**Fixed serious alignment bug from previous release**

### Fixed
- fixed a serious bug in the alignment module introduced during code refactoring in release 1.9.6
- Space + drag now also works when the master layer is not selected
- updated tooltips in the processing-status boxes and fixed their contents

---

## [v1.9.6] - 2025-11-13
**GUI improvements and bug fixes**

### Added
- visual progress indicators for frame processing

### Fixed
- alignment miscalculation when running in single-core mode
- incorrect EXIF tag conversion from TIFF to JPEG
- clickable links in the "About" dialog
- protection against invalid or spurious content in the source folder when importing frames
- fault tolerance for missing or invalid files

### Changed
- major refactoring and cleanup of the alignment code

---

## [v1.9.5] - 2025-11-07
**Fixed possible crash in focus bunches**

### Fixed
- fixed a crash in focus bunches when only a subset of files in a folder is selected

---

## [v1.9.4] - 2025-11-07
**Improved GUI and more fixes to EXIF data**

### Fixed
- more consistent naming in EXIF data display
- EXIF copying is now fault-tolerant
- safer EXIF conversion prevents failure when invalid values are found

### Changed
- improved the save-image dialog with clearer options and explanatory information
- improved EXIF data display
- simplified name of noise detection job and module
- when saving a 16-bit image, a dialog shows the possible options and warns about EXIF data loss for 16-bit PNG format.

---

## [v1.9.3] - 2025-11-02
**Fixes to EXIF data and GUI**

### Fixed
- fault-tolerant EXIF copying prevents corrupted files from being written
- added the missing 16-to-8-bit conversion when saving TIFF as JPEG in retouch mode
- removed problematic EXIF tag MakerNote that may cause failure for some cameras
- added missing EXIF and exposure data in legacy compatibility mode
- menu actions correctly enabled with a new project is created
- minor fix to balance module log output

### Changed
- code cleanup
- improved EXIF data display to make it clearer than the raw data

---

## [v1.9.2] - 2025-10-29
**Fixes to EXIF data and alignment, and GUI refinements**

### Added
- new keyboard and mouse wheel shortcuts to control brush opacity and flow
- added more action shortcuts to the context menu in the project area

### Fixed
- increased the previously too-tight validity tolerance thresholds for composite transformations
- skipping frames with missing alignment transformation
- focus bunch processing order is now sequential
- added missing exposure data to JPEG EXIF data
- converted EXIF data between JPEG, TIFF, and PNG formats

---

## [v1.9.1] - 2025-10-23
**Improved EXIF data handling GUI refinements**

### Added
- added the missing "Show EXIF Data" and "Delete EXIF Data" actions

### Fixed
- if saving EXIF data fails, a warning is issued instead of stopping the run
- fixed EXIF data loading when opening image files in retouch mode
- removed a duplicate parameter from the configuration dialog (FocusStackBunch)
- fixed thread warning when the application quits
- made EXIF handling for JPG files more robust to prevent errors

### Changed
- improved EXIF GUI: more data displayed and improved selection logic

-----

## [v1.9.0] - 2025-10-19
**Added PNG format support and fixed EXIF failure**

### Added
- added support for 8-bit and 16-bit PNG images. Note: EXIF data are not supported for 16-bit PNGs because of limitations in the PIL and OpenCV libraries.

### Fixed
- if saving EXIF data fails, a warning is issued instead of stopping the run

-----

## [v1.8.1] - 2025-10-16
**Alignment stability and performance improvements**

### Added
- optional alignment algorithm based on phase correlation as fallback when no feature match is found
- retry limits in parallel alignment, determined by new configurable parameter delta_max
- new configurable parameters in persistent default settings

### Fixed
- fixed reference-frame indexing when sequential processing is used as a fallback from a multithreaded run
- fixed a failure in the job configuration dialog when input is already selected
- preview thumbnail failure for very large images
- minor inaccuracies in logger messages
- minor GUI issues
- computations for vignetting summary plot

### Changed
- improved robustness of alignment strategy for poorly focused images
- better tuning of parallel frame alignment
- consistent handling of noise map output folders
- improved naming scheme for wizard-generated projects
- improved persistence of default settings
- code refactoring and cleanup

-----

## [v1.8.0] - 2025-10-08
**Minor improvements and accessibility fix**

### Added
- temporary disk space can be cleaned up with a new option to scratch output files at the end of a job 

### Fixed
- fixed the new-project dialog so it displays correctly with a dark background

### Changed
- icons now adapt automatically to light or dark desktop theme
- additional alignment parameters added to default settings
- minor GUI stability fix
- removed the redundant macOS ```.tar.gz``` installer and replaced it with a ```.dmg``` image

-----

## [v1.7.0] - 2025-10-04
**New image-adjustment actions and macOS DMG installer**

### Added
- luminosity and contrast adjustment action
- saturation and vibrance adjustment action
- added a macOS DMG installer

### Changed
- improved windows installer
- white balance moved from filters to edit > adjust menu
- minor GUI cosmetic improvements
- code refactoring

-----

## [v1.6.1] - 2025-10-01
**Performance improvements**

### Added
- windows installer

### Changed
- improved display update performance by refreshing only the painted area
- multiple frame import now runs in a separate thread, avoiding UI freezes
- reduced dependencies and code refactored for more robust architecture
- dropped examples and test images to reduce distribution file size

-----

## [v1.6.0] -  2025-09-27
**Few more features and several fixes**

### Added
- persistent settings dialog to configure app startup options
- command-line option ```-n``` to prevent opening the "new project" dialog
- zoom factor display in the status bar

### Fixed
- ghost brush gradient no longer appears at cursor transitions
- action and job names are now correctly set in the input dialog
- image centering fixed in viewport for double-view modes
- frame highlight works correctly when clicking on a thumbnail
- exif data is now correctly inserted into stacked output files
- bug in the retouch undo has been fixed

### Changed
- cursor updates are now throttled (~60 fps) to improve responsiveness
- new projects created via dialog save exif data by default

----

## [v1.5.4] - 2025-09-23
**Bug fixes**

### Fixed
- fixed alphabetical sorting of layers
- fixed image centering in zoom operations
- fixed color picker reuse in white-balance filter
- minor fixes and code cleanup

### Changed
- menu actions that require a file are disabled when no file is open

----

## [v1.5.3] - 2025-09-21
**Bug fixes**

### Fixed
- fixed a critical startup crash in the distribution package caused by a relative import in the main application scripts
- fixed relative import in main app scripts

### Changed
- implemented dynamic cursor coloring based on background image luminosity

---

## [v1.5.2] - 2025-09-21 (⚠️ DEPRECATED — use 1.5.3)
**Bug fixes**

### Fixed
- fixed white balance filter functionality
- fixed brush preview visibility during view-mode transitions

### Changed
- code refactoring and cleanup

---

## [v1.5.1] - 2025-09-20 (⚠️ DEPRECATED — use 1.5.3)
**Several bug fixes**

### Added
- added the -v1, -v2, and -v3 command-line arguments to select the view mode at startup

### Fixed
- consistent and restyled cursor for current layer view
- fixed ghost cursors in side-by-side views
- fixed cursor shift at startup
- fixed brush preview at image borders
- fixed capitalization of GUI labels
- improved help and description text

---

## [v1.5.0] - 2025-09-16
**GUI improvements and fixes**

### Added
- implemented image rotation

### Fixed
- fixed zoom in wheel events for side-by-side views
- restored standard cursor in empty retouch views
- capitalization of GUI labels

### Changed
- code refactoring and cleanup
- dotted cursor in secondary two-image view

---

## [v1.4.0] - 2025-09-14
**GUI improvements**

### Added
- added retouch view modes with the master and frame side by side or top and bottom
- implemented "Open Recent" menu entry for both projects and retouch images
- expert options can be shown with a checkbox in each dialog
- optional summary plots for alignment transformation parameters

### Fixed
- fixed bug in plot generation
- fixed a warning caused by a missing glyph when generating PDFs on macOS
- made parallel plot generation safer by using a thread lock

### Changed
- code refactoring in various areas


## [v1.3.1] - 2025-09-08
**Fixes and optimizations**

### Fixed
- fixed the input-folder widget in job configuration
- improved handling of pathological alignments
- restored alignment match plots

### Changed
- improved automatic parameters for parallel alignment
- improved pyramid performance by combining two input steps
- improved ORB and SURF feature-extraction performance by caching keypoints
- improved configuration GUI using tabs and other minor GUI improvements
- code cleanup and fixes

---

## [v1.3.0] - 2025-09-06
**Parallel processing and input flexibility**

### Added
- Parallel processing in alignment feature extraction
- Parallel processing of combined actions
- Job input can now specify a list of files (not only a folder)
- CPU and memory usage monitor widget for running jobs

### Fixed
- Path in example project
- Bug fix in config dialog

### Changed
- changed some default parameters for better performance
- Some GUI restyling
- Code cleanup

---

## [v1.2.1] - 2025-09-02
**Bug fixes and minor improvements**

### Changes

* alignment is more tolerant in case of failures: frames are skipped and the running job is not stopped
* fixed the -x (--expert) option
* more safety checks prevent crashes for abnormal conditions
* reference frame index improved with a more consistent treatment, a better numbering scheme and GUI widget 
* improved project undo action description text
* some bug fixes and code cleanup

---

## [v1.2.0] - 2025-08-31
**Parallel processing and more improvements**

### Changes

* Implemented parallel processing for pyramid stacking algorithm
* optimized the pyramid algorithm to automatically select the best strategy within the memory budget, avoiding memory issues when processing many images. Explicit configuration is also available.
* added an automatic subsampling option for alignment, balancing, and vignetting; it is now enabled by default
* added HLS and HSV corrections for 16-bit images
* added luminosity correction in the LAB color space
* the alignment module skips frames if transformation parameters are outside a reasonable range
* the multilayer module warns if the estimated output file size exceeds 1 GB
* enabled the "Run all jobs" action only when more than one job is present
* updated the default module names in projects generated by the "New Project" dialog
* refactored code
* fixed GUI issues

---

## [v1.1.0] - 2025-08-28
**New pyramid algorithm, improvements, and fixes**

### Changes

* added pyramid tiling, which requires less RAM by fusing images in tiles
* the alignment module now supports images with different dimensions
* noisy pixel mask verifies that the mask has the same shape as input images
* minor changes to default alignment parameters
* improved the GUI
* fixed bugs
---

## [v1.0.4.pre2] - 2025-08-26
**Bug fixes**

### Changes

* fixed the release build script to create ```.tar.gz``` archives instead of ZIP files for macOS and Linux

---

## [v1.0.4] - 2025-08-26
**Bug fixes**

### Changes

* extensions are treated in lower case (e.g.: both jpg and JPG)
* added missing retouch menu action: import frames from current project

---
## [v1.0.3] - 2025-08-26
**Bug fixes**

### Changes

* fixed menu text
* fixed crash multilayer module
* fixed multilayer module
* code cleanup

---

## [v1.0.2] - 2025-08-25
**Bug fixes**

### Changes

* fixed context menu
* fixed retouch callback for shiestacker-project app
* fixed double image loading

---

## [v1.0.1] - 2025-08-25
**First stable release**

### Changes

* added source file missing by mistake in v1.0.0

---

## [v1.0.0] - 2025-08-25
**First stable release**

### Changes

* implemented vignetting correction filter
* improved vignetting performance using subsampling
* implemented fast subsample option in balance algorithms
* added hexadecimal color input to the white-balance filter
* new application logo
* interface improvements: implemented master/layer toggle
* more informative GUI messages and colors
* refactored code and performed other cleanup
* bug fixes

Note

A source file was missing in this tag, and was added in v1.0.1

---

## [v0.5.0] - 2025-08-20
**GUI and robustness improvements**

### Changes

* layer selection highlighted with a blue border
* improved font rendering in brush preview
* fixed thumbnail spacing
* fixed and improved save strategy for retouched images
* added checks for updated version in about dialog
* disable "Save" and "Save As..." menus if do not apply to current status

---

## [v0.4.0] - 2025-08-19
**Support touchpad navigation**

### Changes

* implemented touchpad image navigation (pan, zoom with pinch)
* improved alignment robustness: retry without subsampling if the number of good matches is below a threshold
* added more robust path management in retouch area
* added frame count display in "New Project" dialog
* more uniform colors in the GUI run log
* cleaned up code and removed remnants of obsolete code
* various fixes

---

## [v0.3.6] - 2025-08-18
**Bug fixes**

### Changes

* fixed a bug that prevented complete cleanup when the "New Project" action was called
* fixed the management of project file path while loading and saving
* removed duplicate code
* code cleanup

---

## [v0.3.5] - 2025-08-17
**Bug fixes**

### Changes

* fixed a bug that prevented users from adding sub-actions
* constrained the vignetting model to avoid searching for dark areas at the center of the image instead of near the periphery
* updated sample images and documentation

---

## [v0.3.4] - 2025-08-16
**Code consolidation and fixes**

### Changes

* consolidated code and added support for pylint checks
* some bug fixes
* new project dialog shows the number of bunches, if selected
* updated sample images, examples and documentation

---

## [v0.3.3] - 2025-08-13
**Fixed PyPI distribution**

This release is equivalent to v0.3.2, but resolves a problem for PyPI distribution.

### Changes

* examples and tests removed from PyPI distribution in order to fix file size limit

---

## [v0.3.2] - 2025-08-13
**Fixes and code refactoring**

### Changes

* fixed ```from shinestacker import *```
* restored jupyter support and updated examples
* several bug fixes
* refactored code to reduce interclass dependencies
* updated documentation
* added new sample images and project files
* examples removed from PyPI distribution

---

## [v0.3.1] - 2025-08-12
**Fixes and code refactoring**

### Changes

* some GUI fixes
* some code refactoring and cleanup

---

## [v0.3.0] - 2025-08-11
**Filters added to retouch GUI**

### Changes

* added sharpening, denoising, and white-balance filters
* updated documentation
* some bug fixes

---

## [v0.2.2] - 2025-07-28
**More stability and improved tests**

### Changes

* improved test suite and enhanced test coverage
* updated documentation
* some stability improvements

---

## [v0.2.1] - 2025-07-27
**Icon location fix**

### Changes

* fixed the icon location for compatibility with PyPI and bundled releases

---

## [v0.2.0] - 2025-07-27
**Stability improvements and new package name**

### Changes

* first release with new name ShineStacker
* added BRISK detector/descriptor alignment method
* improved stability by adding more validation controls to alignment configuration
* some bug fixes
* minor restyling

---

## [v0.1.4] - 2025-07-23
**Bug fixes and alignment improvements**

### Changes

* fixed recently introduced bugs in the alignment module
* disabled ECC refinement, too unstable
* improved rigid alignment with a more precise matrix
* fixed minor bugs
* removed dependence on termcolor external module
* some internal code cleanup

---

## [v0.1.1] - 2025-07-20
**Optimized image alignment**

### Changes

* sped up alignment with image subsampling
* enabled alignment refinement using the ECC transform
* GUI opens new project dialog at startup
* fixed color logging for windowed app
*  bug fixes

---

## [v0.1.0] - 2025-07-19
**First relatively stable and usable GUI release**

### Changes
- several stability improvements
- several bug fixes

---