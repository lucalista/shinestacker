# Job creation

Create a job, then schedule the desired actions in a job, then run the job.

```python
job = StackJob(name, working_path [, input_path])
```

Arguments are:
* ```working_path```: the directory that contains input and output images, organized in subdirectories as specified by each action
* ```name```: the name of the job, used for printout
* ```input_path``` (optional): the subdirectory within ```working_path``` that contains input images for subsequent action. If not specified, at least the first action must specify an ```input_path```.
