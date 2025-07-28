import pytest
from shinestacker.core.exceptions import (
    FocusStackError,
    InvalidOptionError,
    ImageLoadError,
    ImageSaveError,
    AlignmentError,
    BitDepthError,
    ShapeError,
    RunStopException
)


def test_focus_stack_error_basic():
    with pytest.raises(FocusStackError) as excinfo:
        raise FocusStackError("Base error")
    assert str(excinfo.value) == "Base error"


def test_invalid_option_error():
    with pytest.raises(InvalidOptionError) as excinfo:
        raise InvalidOptionError("color_mode", "invalid_value")
    assert str(excinfo.value) == "Invalid option color_mode = invalid_value"
    assert excinfo.value.option == "color_mode"
    assert excinfo.value.value == "invalid_value"
    assert excinfo.value.details == ""
    with pytest.raises(InvalidOptionError) as excinfo:
        raise InvalidOptionError("algorithm", "bad_algo", "must be one of: A, B, C")
    assert str(excinfo.value) == "Invalid option algorithm = bad_algo: must be one of: A, B, C"
    assert excinfo.value.details == "must be one of: A, B, C"


def test_image_load_error():
    with pytest.raises(ImageLoadError) as excinfo:
        raise ImageLoadError("/path/to/image.jpg")
    assert str(excinfo.value) == "Failed to load /path/to/image.jpg"
    assert excinfo.value.path == "/path/to/image.jpg"
    assert excinfo.value.details == ""
    with pytest.raises(ImageLoadError) as excinfo:
        raise ImageLoadError("missing.png", "file not found")
    assert str(excinfo.value) == "Failed to load missing.png: file not found"
    assert excinfo.value.details == "file not found"


def test_image_save_error():
    with pytest.raises(ImageSaveError) as excinfo:
        raise ImageSaveError("/output/result.jpg")
    assert str(excinfo.value) == "Failed to save /output/result.jpg"
    assert excinfo.value.path == "/output/result.jpg"
    assert excinfo.value.details == ""
    with pytest.raises(ImageSaveError) as excinfo:
        raise ImageSaveError("output.tiff", "unsupported format")
    assert str(excinfo.value) == "Failed to save output.tiff: unsupported format"
    assert excinfo.value.details == "unsupported format"


def test_alignment_error():
    with pytest.raises(AlignmentError) as excinfo:
        raise AlignmentError(2, "feature detection failed")
    assert str(excinfo.value) == "Alignment failed for image 2: feature detection failed"
    assert excinfo.value.index == 2
    assert excinfo.value.details == "feature detection failed"


def test_bit_depth_error():
    with pytest.raises(BitDepthError) as excinfo:
        raise BitDepthError("uint8", "float32")
    assert str(excinfo.value) == "Image has type float32, expected uint8."


def test_shape_error():
    with pytest.raises(ShapeError) as excinfo:
        raise ShapeError((1080, 1920), (720, 1280))
    expected_msg = """
Image has shape (1280x720), while it was expected (1920x1080).
""".strip()
    assert str(excinfo.value).strip() == expected_msg


def test_run_stop_exception():
    with pytest.raises(RunStopException) as excinfo:
        raise RunStopException("focus stacking")
    assert str(excinfo.value) == "Job focus stacking stopped"
    with pytest.raises(RunStopException) as excinfo:
        raise RunStopException("")
    assert str(excinfo.value) == "Job stopped"
    with pytest.raises(RunStopException) as excinfo:
        raise RunStopException(None)
    assert str(excinfo.value) == "Job None stopped"


def test_exception_hierarchy():
    assert issubclass(InvalidOptionError, FocusStackError)
    assert issubclass(ImageLoadError, FocusStackError)
    assert issubclass(ImageSaveError, FocusStackError)
    assert issubclass(AlignmentError, FocusStackError)
    assert issubclass(BitDepthError, FocusStackError)
    assert issubclass(ShapeError, FocusStackError)
    assert issubclass(RunStopException, FocusStackError)
