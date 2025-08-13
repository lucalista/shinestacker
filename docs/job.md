# Job creation and action scheduling

Create a job, then schedule the desired actions in a job, then run the job.

Quick start example:

```python
from focus_stack import *

job = StackJob("job", "E:/Focus stacking/My image directory/", input_path="src")
job.add_action(NoiseDetection())
job.run()

job = StackJob("job", "E:/Focus stacking/My image directory/", input_path="src")
job.add_action(Actions("align", actions=[MaskNoise(),
                                         AlignFrames(),
                                         BalanceFrames(mask_size=0.9, i_min=150, i_max=65385)]))
job.add_action(FocusStackBunch("batches", PyramidStack(), frames=10, overlap=2, denoise=0.8))
job.add_action(FocusStack("stack", PyramidStack(), postfix='_py', denoise=0.8))
job.add_action(FocusStack("stack", DepthMapStack(), input_path='batches', postfix='_dm', denoise=0.8))
job.add_action(MultiLayer("multilayer", input_path=['batches', 'stack']))
job.run()
```

```python
job = StackJob(name, working_path [, input_path])
```

Arguments are:
* ```working_path```: the directory that contains input and output images, organized in subdirectories as specified by each action
* ```name```: the name of the job, used for printout
* ```input_path``` (optional): the subdirectory within ```working_path``` that contains input images for subsequent action. If not specified, at least the first action must specify an ```input_path```.
* ```callbacks``` (optional, default: ```None```): dictionary of callback functions for internal use. If equal to ```'tqdm'```, a progress bar is shown in either text mode or jupyter notebook.
* ```enabled``` (optional, default: ```True```): allows to switch on and off all actions within a job.

## Schedule multiple actions based on a reference image: align and/or balance images

The class ```CombinedActions``` runs multiple actions on each of the frames appearing in a path.

```python
job.add_action(CombinedActions(name, [...], *options))
```
Arguments for the constructor of ```CombinedActions``` are for the :
* ```name```: the name of the action, used for printout, and possibly for output path.
* ```actions```: array of action object to be applied in cascade.
* ```input_path``` (optional): the subdirectory within ```working_path``` that contains input images to be processed. If not specified, the last output path is used, or, if this is the first action, the ```input_path``` specified with the ```StackJob``` construction is used. If the ```StackJob``` specifies no ```input_path```, at least the first action must specify an  ```input_path```.
* ```output_path``` (optional): the subdirectory within ```working_path``` where aligned images are written. If not specified,  it is equal to  ```name```.
* ```working_path``` (optional): the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.
* ```plot_path``` (optional, default: ```plots```): the directory within ```working_path``` that contains plots produced by the different actions.
* ```resample``` (optional, default: 1): take every *n*<sup>th</sup> frame in the selected directory. Default: take all frames.
* ```ref_idx``` (optional): the index of the image used as reference. Images are numbered starting from zero. If not specified, it is the index of the middle image.
* ```step_process``` (optional): if equal to ```True``` (default), each image is processed with respect to the previous or next image, depending if its file is placed in alphabetic order after or befor the reference image.
* ```enabled``` (optional, default: ```True```): allows to switch on and off this module. 
