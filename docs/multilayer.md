# Combine frames into a single multilayer TIFF

```python
job.add_action(MultiLayer(name, *options))
```
Combining the focus-stacking output with intermediate frames or bunches is useful for detailed retouching in an image-editing application such as Photoshop or GIMP. Open the multilayer output file and edit it using masks and layers.

Arguments for the constructor of ```MultiLayer``` are:
* ```input_path``` (optional): one or more subdirectories within ```working_path``` that contain the images to combine. If not specified, the last output path is used, or, for the first action, the ```input_path``` specified when creating the ```StackJob```. If the ```StackJob``` specifies no ```input_path```, the first action must specify one. If multiple input paths are specified, frames from the first path are placed on top of the stack.
* ```output_path``` (optional): the subdirectory within ```working_path``` where the output image is written. If not specified, it is set to ```name```.
* ```working_path```: the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.
* ```exif_path``` (optional): if specified, EXIF data are copied to the output file from a file in this directory. If not specified, the source directory used as input for the first action is used. If set to ```''```, no EXIF data is saved.
* ```enabled``` (optional, default: ```True```): enables or disables this module.
