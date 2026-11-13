# Job creation and action scheduling

Create a job, add the desired actions, then run it.

Quick start example:

```python
from shinestacker import *

job = StackJob("job", "E:/focus_stacking/project_directory/", input_path="tiff_images")
job.add_action(CombinedActions("align", actions=[AlignFrames(), BalanceFrames()]))
job.add_action(FocusStackBunch("batches", PyramidStack(), frames=12, overlap=2))
job.add_action(FocusStack("stack", PyramidStack(), prefix='pyram_'))
job.add_action(FocusStack("stack", DepthMapStack(), prefix='dmap_'))
job.run()
```

```python
job = StackJob(name, working_path [, input_path])
```

Arguments are:
* ```working_path```: the directory that contains input and output images, organized in subdirectories as specified by each action
* ```name```: the name of the job, used for printout
* ```input_path``` (optional): the subdirectory within ```working_path``` that contains input images for subsequent action. If not specified, at least the first action must specify an ```input_path```.
* ```callbacks``` (optional, default: ```None```): dictionary of callback functions for internal use. If equal to ```'tqdm'```, a progress bar is shown in either text mode or a Jupyter notebook.
* ```enabled``` (optional, default: ```True```): enables or disables all actions within a job.

## Schedule multiple actions based on a reference image: align and/or balance images

The class ```CombinedActions``` runs multiple actions on each of the frames appearing in a path.

```python
job.add_action(CombinedActions(name, [...], *options))
```
Arguments for the ```CombinedActions``` constructor are:
* ```name```: the name of the action, used for printout, and possibly for output path.
* ```actions```: array of action object to be applied in cascade.
* ```input_path``` (optional): the subdirectory within ```working_path``` that contains input images to be processed. If not specified, the last output path is used, or, if this is the first action, the ```input_path``` specified with the ```StackJob``` construction is used. If the ```StackJob``` specifies no ```input_path```, at least the first action must specify an  ```input_path```.
* ```output_path``` (optional): the subdirectory within ```working_path``` where output images are written. If not specified, it is set to ```name```.
* ```working_path``` (optional): the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.
* ```plot_path``` (optional, default: ```plots```): the directory within ```working_path``` that contains plots produced by the different actions.
* ```resample``` (optional, default: 1): take every *n*<sup>th</sup> frame in the selected directory. Default: take all frames.
* ```reference_index``` (optional, default: 0): the index of the reference image. Images are numbered from 1 to N. -1 selects the last image, and 0 selects the median index.
* ```step_process``` (optional): if ```True``` (default), each image is processed relative to the previous or next image, depending on whether its filename is alphabetically before or after the reference image.
* ```enabled``` (optional, default: ```True```): enables or disables this module.
* ```scratch_output_dir``` (optional, default: ```True```): scratch output directory before processing. This avoids that existing files pollute the output.
* ```delete_output_at_end``` (optional, default: ```False```): deletes the output after processing, freeing disk space when the step is intermediate and not part of the final output.
* ```max_threads``` (optional, default: ```2```): number of parallel processes allowed. The number of actual threads will not be greater than the number of available CPU cores.
* ```chunk_submit``` (optional, default: ```True```): if enabled, submits tasks in chunks of at most ```max_threads```. If disabled, submits all tasks at once, which may improve performance at the cost of significantly higher memory use.
