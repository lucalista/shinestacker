class FocusStackError(Exception):
    """Base exception for all focusstack errors"""
    pass


class InvalidOptionError(FocusStackError):
    """"Raised when invalid option is requested"""
    def __init__(self, option, value, details=""):
        self.option = option
        self.value = value
        self.details = details
        super().__init__(f"Invalid option {option} = {value}" + ("" if details == "" else f": {details}"))


class ImageLoadError(FocusStackError):
    """Raised when image loading fails"""
    def __init__(self, path, details=""):
        self.path = path
        self.details = details
        super().__init__(f"Failed to load {path}" + ("" if details == "" else f": {details}"))


class AlignmentError(FocusStackError):
    """Raised when image alignment fails"""
    def __init__(self, index, details):
        self.index = index
        self.details = details
        super().__init__(f"Alignment failed for image {index}: {details}")


class BitDepthError(FocusStackError):
    """Raised when images don't have the same bit depth"""
    def __init__(self, dtype_ref, dtype):
        super().__init__("Images has type {}, expected {}.".format(dtype, dtype_ref))


class ShapeError(FocusStackError):
    """Raised when images don't have the same shape"""
    def __init__(self, shape_ref, shape):
        super().__init__("Images has shape ({}x{}), expected ({}x{}).".format(*shape[:2], *shape_ref[:2]))
