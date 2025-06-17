# Combine frames into a single multilayer tiff

```python
job.add_action(MultiLayer(name, *options))
```
It is convenient to combine the output of focus stacking and intermediate frames, or bunches, in order to perform fine retouch using an image manipulation application. This may be done with PhotoShop or GIMP, opening the multilayer oputput file and editing with masks and layers.

Arguments for the constructor of ```MultiLayer``` are:
* ```input_path``` (optional): one or more subdirectory within ```working_path``` that contains input images to be combined. If not specified, the last output path is used, or, if this is the first action, the ```input_path``` specified with the ```StackJob``` construction is used. If the ```StackJob``` specifies no ```input_path```, at least the first action must specify an  ```input_path```.
* ```output_path``` (optional): the subdirectory within ```working_path``` where aligned images are written. If not specified,  it is equal to  ```name```.
* ```working_path```: the directory that contains input and output image subdirectories. If not specified, it is the same as ```job.working_path```.
* ```exif_path``` (optional): if specified, EXIF data are copied to the output file from file in the specified directory. If not specified, it is the source directory used as input for the first action. If set equal to ```''``` no EXIF data is saved.
* ```enabled``` (optional, default: ```True```): allows to switch on and off this module.
