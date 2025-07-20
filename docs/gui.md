# Graphical User Interface

## Introduction
FocusStack processes focus-bracketed images in two phases:
* **Project**: Batch processing (alignment/balancing/stacking)
* **Retouch**: Layer-based refinement
> [!NOTE]
> Advanced processing details in [main documentation](main.md).

The batch processing supports image alignment, color and luminosity balance, vignetting removal,
noisy pixel masking.

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

<img src='../img/flow-diagram.png' width="900" alt="FocusStack workflow: Source images → Alignment → Balancing → Stacking">

> **Large Set Tip**: For 100+ images:
> - Split into 10-15 image "bunches" 
> - Set frame overlap (default: 2 frames)
> - Combine intermediate results later

> 💡 **RAM Warning**: >15 images may need 16GB+ RAM. Use smaller batches if needed.

The newly created project consists of a single job that contains more actions.
Each action produces a folder as output that has, by default, the action's name.
Some actions can be combined in order to produce a single intermediate output (alignment, balancing, etc.).

**Action Outputs**: 📁 `aligned-balanced/` | 📁 `bunches/` | 📁 `stacked/`

> **Pro Tip**: Duplicate jobs when processing similar image sets to save configuration time. You can run multiple jobs in sequence.

It is possible to run a single job, or all jobs within a project.

<img src='../img/gui-project-run.png' width="600">

### Project Run Tabs

1. Job progress bar
2. Real-time log viewer
3. Retouch button (enabled after processing)

When the job finishes, a *Retouch* button is enabled, which opens the output image into the retouch area.

## Retouch area

<img src='../img/gui-retouch.png' width="600">

### Brush Properties
Adjust in the top toolbar:
- **Size**: Brush diameter (px)
- **Hardness**: Edge softness (0-100%)
- **Opacity**: Paint transparency
- **Flow**: Paint accumulation rate

> 💡 Pro Tip: Use low opacity/flow (20-40%) for subtle corrections

### Retouch Workflow

1. **Navigate**: 
   - Zoom/pan to defect area
   - Toggle between master/source (`X`)
2. **Correct defects/artifacts**:**:
   - Select source layer with clean area
   - Adjust brush properties (size/hardness/opacity)
   - Paint over defects
   - Use `Ctrl+Z` to undo strokes
3. **Verify**:
   - Toggle master view (`M`) to check results
   - Compare before/after with `L`/`M` toggle
3. **Export**:
   - ✅ Final image: Single TIFF/JPEG 
   - 🗂️ Editable: Multilayer TIFF (large)

| Action              | Shortcut                  |
|---------------------|---------------------------|
| Zoom in/out         | `Ctrl` + `+`/`- or mouse wheel          |
| Reset view          | `Ctrl` + `0`              |
| Pan                 | `Space` + mouse drag      |
| Prev./next layer    | `Up`/`Down` arrows        |
| View master layer   | `M`                       |
| View source layer   | `L`                       |
| Toggle master ↔ source | `X`                    |

See help menu for complete list of shortcuts.

**Export Formats**:
- Single TIFF: Final image (highest quality)
- Single JPEG: For web and quick preview (lower quality)
- Multilayer TIFF: Preserves all layers (large file)

**EXIF metadata**:
* EXIF data can be imported from source images and saved with final file.

## Final retouch

The final retouch, including color and luminosity balance, sharpness enhancement and
so on can be applied with your favorite image processing application, like [GIMP](https://www.gimp.org/)
or other.

