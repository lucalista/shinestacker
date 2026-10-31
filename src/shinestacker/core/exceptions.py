# pylint: disable=C0301
class FocusStackError(Exception):
    pass


class InvalidProjectError(FocusStackError):
    def __init__(self, file_path):
        self.file_path = file_path
        super().__init__(f"File {file_path} contains an invalid project.")


class InvalidOptionError(FocusStackError):
    def __init__(self, option, value, details=""):
        self.option = option
        self.value = value
        self.details = details
        super().__init__(f"Invalid option {option} = {value}" +
                         ("" if details == "" else f": {details}"))


class ImageLoadError(FocusStackError):
    def __init__(self, path, details=""):
        self.path = path
        self.details = details
        super().__init__(f"Failed to load {path}" + ("" if details == "" else f": {details}"))


class ImageSaveError(FocusStackError):
    def __init__(self, path, details=""):
        self.path = path
        self.details = details
        super().__init__(f"Failed to save {path}" + ("" if details == "" else f": {details}"))


class AlignmentError(FocusStackError):
    def __init__(self, index, details):
        self.index = index
        self.details = details
        super().__init__(f"Alignment failed for frame {index}: {details}")


class BitDepthError(FocusStackError):
    def __init__(self, dtype_ref, dtype):
        super().__init__(f"Image has type {dtype}, expected {dtype_ref}.")


class ShapeError(FocusStackError):
    def __init__(self, shape_ref, shape):
        super().__init__(f'''
Image has shape ({shape[1]}x{shape[0]}), while it was expected ({shape_ref[1]}x{shape_ref[0]}).
''')


class RunStopException(FocusStackError):
    def __init__(self, name):
        if name != "":
            name = f"{name} "
        super().__init__(f"Job {name}stopped")


class PathTooLong(FocusStackError):
    def __init__(self, path):
        super().__init__(f'Path exceeds Windows 260 characters limits: {path}. '
                         'You can enable long path following the instructions give in this page: '
                         'https://learn.microsoft.com/en-us/windows/'
                         'win32/fileio/maximum-file-path-limitation')


class InvalidWinPath(FocusStackError):
    def __init__(self, path):
        super().__init__('Only ASCII characters are supported on Windows. '
                         f'Please rename the path: {path}')
