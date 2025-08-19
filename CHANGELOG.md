# Changelog

This page reports the main releases only and the main changes therein.

---

## [v0.4.0] - 2025-08-19
**Support touchpad navigation**

### Changes

* implemented touchpad image navigation (pan, zoom with pinch)
* alignment robustness: retry without subsampling if number of bood matches is below a threshold parameter
* added more robust path management in retouch area
* added frame count display in "New Project" dialog
* more unifrom color code in GUI run log
* code clanup, removed remnants of obsolete code
* various fixes

---

## [v0.3.6] - 2025-08-18
**Bug fixes**

### Changes

* fixed a bug that prevented a complete clean up when "New Project" action is called
* fixed the management of project file path while loading and saving
* removed duplicated code
* some code clean up

---

## [v0.3.5] - 2025-08-17
**Bug fixes**

### Changes

* fixed a bug that prevented to add sub-actions
* vignetting constrains model parameter in order to prevent searching for dark areas at the center of the image instead of at periphery
* updated sample images and documentation

---

## [v0.3.4] - 2025-08-16
**Code consolidation and fixes**

### Changes

* code consolidation with support of pylint code checking
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
* several code refactoring reduces interclass dependencies
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

* added filters for sharpening, denoise and white balance
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

* icon location fixed, compatibly with PyPI and bundle release build

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
* improvement rigid alignment with more precise matrix
* some minor bug fixes
* removed dependence on termcolor external module
* some internal code cleanup

---

## [v0.1.1] - 2025-07-20
**Optimized image alignment**

### Changes

* Faster alignment with image subsample enables
* Alignment refinement via ECC transform enabled
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