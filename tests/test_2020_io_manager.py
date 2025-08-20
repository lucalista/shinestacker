import numpy as np
import cv2
import pytest
from pathlib import Path
from shinestacker.retouch.io_manager import IOManager
from shinestacker.retouch.layer_collection import LayerCollection
from shinestacker.algorithms.utils import read_img


def get_sample_paths(directory, extension):
    base_path = Path(__file__).parent.parent / directory
    if not base_path.exists():
        raise FileNotFoundError(f"Sample directory not found: {base_path}")
    return sorted([str(p) for p in base_path.glob(f"*.{extension}")])


@pytest.fixture(scope="module")
def sample_jpg_paths():
    return get_sample_paths("examples/input/img-jpg", "jpg")


@pytest.fixture(scope="module")
def sample_tif_paths():
    return get_sample_paths("examples/input/img-tif", "tif")


def test_import_frames(sample_jpg_paths):
    lc = LayerCollection()
    io = IOManager(lc)
    paths = sample_jpg_paths[:2]
    stack, labels, master = io.import_frames(paths)
    assert len(stack) == 2
    expected_labels = [Path(p).stem for p in paths]
    assert labels == expected_labels
    assert master.shape == stack[0].shape
    np.testing.assert_array_equal(master, stack[0])
    for i, path in enumerate(paths):
        img_bgr = cv2.imread(path)
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        np.testing.assert_array_equal(stack[i], img_rgb)


def test_set_exif_data(sample_jpg_paths):
    lc = LayerCollection()
    io = IOManager(lc)
    exif_path = sample_jpg_paths[0]
    io.set_exif_data(exif_path)
    assert io.exif_path == exif_path
    assert io.exif_data is not None


def test_save_master(sample_jpg_paths, tmp_path):
    lc = LayerCollection()
    io = IOManager(lc)
    stack, _, master = io.import_frames([sample_jpg_paths[0]])
    lc.set_master_layer(master)
    io.set_exif_data(sample_jpg_paths[0])
    output_path = tmp_path / "master.tif"
    io.save_master(str(output_path))
    assert output_path.exists()
    saved_img_rgb = read_img(str(output_path))
    np.testing.assert_array_equal(saved_img_rgb, master)
