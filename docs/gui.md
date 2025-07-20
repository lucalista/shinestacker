# Graphical User Interface

## Introduction
FocusStack processes focus-bracketed images in two phases:
* **Project**: Batch processing (alignment/balancing/stacking)
* **Retouch**: Layer-based refinement
> [!NOTE]
> Advanced processing details in [main documentation](main.md).

The batch processing supports image alignment, color and luminosity balance, vignetting removal,
noisy picel masking.

## Starting

* If the python package is donwloaded and installed, the GUI can start either from a console command line :

```console
> focusstack
```

* If the app is dowloaded from the [releases page](https://github.com/lucalista/focusstack/releases), after the  ```zip``` archive is uncompressed, the user can just double-click the app icon:

<img src='../img/gui-finder.png' width="300">

**Platform Tip**: Windows apps are inside `/focusstack/`, macOS/Linux apps are directly in the uncompressed folder.

The GUI has two main working areas: 

* *Project* 
* *Retouch*

Switching from *Project* to *Retouch* can be done from the *FocusStack* main menu.

## Project area

When the app starts, it proposes to create a new project.

<img src='../img/gui-project-new.png' width="600">

### Creating Projects
1. Select source folder (JPEG/TIFF 8/16-bit)
2. Configure job actions (auto-saved in project file)
3. Run processing:
   - Real-time logs & progress bar
   - Thumbnail previews for each stage

<img src='../img/flow-diagram.png' width="600">

> **Large Set Tip**: For 100+ images:
> - Split into 10-15 image "bunches" 
> - Set frame overlap (default: 2 frames)
> - Combine intermediate results later

> 💡 **RAM Warning**: >15 images may need 16GB+ RAM. Use smaller batches if needed.

The newly created project consists in a single job that contains more actions.
Each action produces a folder as output that has, by default, the action's name.
Some actions can be combined in order to produce a single intermediate output.
This is the case for alignment, balancing, etc.

**Action Outputs**: 📁 `aligned-balanced/` | 📁 `bunches/` | 📁 `stacked/`

> **Pro Tip**: Duplicate jobs when processing similar image sets to save configuration time. 

It is possible to run a single job, or all jobs within a project.

<img src='../img/gui-project-run.png' width="600">

During processing:

* Real-time logs appear in new tab
* Progress bar shows current action
* Thumbnails generate for completed stages (images, histograms)

When the job finishes, a *Retouch* button is enabled, which opens the output image into the retouch area.

## Retouch area

<img src='../img/gui-retouch.png' width="600">

In the retouch area it is possible to apply the final correction to the stacked image.

### Retouch Workflow

Retouch stacking artifacts using layer-based editing:

1. **Navigate**: 
   - Mouse wheel or [Ctrl +]/[Ctrl -] to zoom | Space bar + mouse to pan
   - Up/Down arros switch source layers
2. **Correct**:
   - Adjust brush size, hardness, opacity and flow with cursors
   - Paint from source layers to master
3. **Export**:
   - ✅ Final image: Single TIFF/JPEG 
   - 🗂️ Editable: Multilayer TIFF (large)

## Final retouch

The final retouch, including color and luminosity balance, sharpness enhancement and
so on can be applied with your favurite image processing application, like [GIMP](https://www.gimp.org/)
or other.

