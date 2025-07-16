class FocusStackError(Exception):
    pass


class InvalidOptionError(FocusStackError):
    def __init__(self, option, value, details=""):
        self.option = option
        self.value = value
        self.details = details
        super().__init__(f"Invalid option {option} = {value}" + ("" if details == "" else f": {details}"))


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
        super().__init__(f"Alignment failed for image {index}: {details}")


class BitDepthError(FocusStackError):
    def __init__(self, dtype_ref, dtype):
        super().__init__("Image has type {}, expected {}.".format(dtype, dtype_ref))


class ShapeError(FocusStackError):
    def __init__(self, shape_ref, shape):
        super().__init__("Image has shape ({}x{}), expected ({}x{}).".format(*shape[:2], *shape_ref[:2]))


class RunStopException(FocusStackError):
    def __init__(self, name):
        if name != "":
            name = f"{name} "
        super().__init__(f"Job {name}stopped")
