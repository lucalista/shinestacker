import time
import tempfile
import pytest
import numpy as np
import cv2
import os
from unittest.mock import MagicMock
from shinestacker.config.constants import constants
from shinestacker.config.defaults import DEFAULTS
from shinestacker.core.exceptions import InvalidOptionError
from shinestacker.algorithms.utils import read_and_validate_img, img_bw
from shinestacker.algorithms.depth_map import DepthMapStack

n_images = 6


@pytest.fixture
def example_images():
    image_dir = "examples/input/img-jpg/"
    filenames = [os.path.join(image_dir, f"000{i}.jpg") for i in range(6)]
    for f in filenames:
        if not os.path.exists(f):
            pytest.skip(f"Test image {f} not found")
    return filenames


def test_initialization():
    dms = DepthMapStack()
    assert dms.map_type == DEFAULTS['depth_map_params']['map_type']
    assert dms.energy == DEFAULTS['depth_map_params']['energy']


def test_sobel_map_single_image(example_images):
    dms = DepthMapStack()
    img = cv2.imread(example_images[0], cv2.IMREAD_GRAYSCALE)
    gray_img = img.astype(np.float32)
    sobel_map = dms.get_sobel_map(gray_img)
    assert sobel_map.shape == gray_img.shape
    assert sobel_map.dtype == np.float32
    assert np.all(sobel_map >= 0)


def test_laplacian_map_single_image(example_images):
    dms = DepthMapStack()
    img = cv2.imread(example_images[0], cv2.IMREAD_GRAYSCALE)
    gray_img = img.astype(np.float32)
    laplacian_map = dms.get_laplacian_map(gray_img)
    assert laplacian_map.shape == gray_img.shape
    assert laplacian_map.dtype == np.float32
    assert np.all(laplacian_map >= 0)


def test_modified_laplacian_single_image(example_images):
    dms = DepthMapStack()
    img = cv2.imread(example_images[0], cv2.IMREAD_GRAYSCALE)
    gray_img = img.astype(np.float32)
    modified_laplacian_map = dms.get_modified_laplacian(gray_img)
    assert modified_laplacian_map.shape == gray_img.shape
    assert modified_laplacian_map.dtype == np.float32
    assert np.all(modified_laplacian_map >= 0)


def test_focus_stack_with_examples(example_images):
    dms = DepthMapStack()
    dms.process = MagicMock()
    dms.process.callback.return_value = True
    dms.print_message = MagicMock()
    dms.init(example_images[:3])
    result = dms.focus_stack()
    assert len(result.shape) == 3
    assert result.dtype == np.uint8
    first_input = cv2.imread(example_images[0], cv2.IMREAD_GRAYSCALE)
    assert not np.array_equal(result, first_input)


def test_variance_map_single_image(example_images):
    dms = DepthMapStack()
    img = cv2.imread(example_images[0], cv2.IMREAD_GRAYSCALE)
    gray_img = img.astype(np.float32)
    variance_map = dms.get_variance_map(gray_img)
    assert variance_map.shape == gray_img.shape
    assert variance_map.dtype == np.float32
    assert np.all(variance_map >= 0)


def test_focus_map_with_examples(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    dms.process = MagicMock()
    energies = np.empty((3, *dms.shape), dtype=np.float32)
    for i, img_path in enumerate(example_images[:3]):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_img = img.astype(np.float32)
        energies[i] = dms.get_sobel_map(gray_img)
    focus_map = dms.get_focus_map(energies)
    assert focus_map.shape == energies.shape
    assert focus_map.dtype == np.float32
    assert np.all(np.isfinite(focus_map))
    valid_mask = np.isfinite(focus_map)
    assert np.all(focus_map[valid_mask] >= 0)
    assert np.all(focus_map[valid_mask] <= 1)


def test_weighted_pyramid_blend(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    dms.process = MagicMock()
    energies = np.empty((3, *dms.shape), dtype=np.float32)
    for i, img_path in enumerate(example_images[:3]):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_img = img.astype(np.float32)
        energies[i] = dms.get_sobel_map(gray_img)
    weights = dms.get_focus_map(energies)
    result = dms.weighted_pyramid_blend(weights, [3])
    assert result.shape == (dms.shape[0], dms.shape[1], 3)
    assert result.dtype == np.uint8


def test_performance_with_all_images(example_images):
    dms = DepthMapStack()
    dms.process = MagicMock()
    dms.process.callback.return_value = True
    start = time.time()
    dms.init(example_images)
    result = dms.focus_stack()
    elapsed = time.time() - start
    assert result.shape[0] > 0 and result.shape[1] > 0
    print(f"\nFocus stacking {n_images} images took {elapsed:.2f} seconds")
    output_dir = "examples/output/"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "focus_stacked.jpg")
    cv2.imwrite(output_path, result)
    os.remove(output_path)


def test_focus_stack_invalid_energy(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.process = MagicMock()
    dms.print_message = MagicMock()
    dms.energy = "invalid_energy"
    with pytest.raises(InvalidOptionError):
        dms.focus_stack()


def test_focus_map_max_type(example_images):
    dms = DepthMapStack(map_type='max')
    dms.init(example_images[:3])
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    energies = np.empty((3, *dms.shape), dtype=np.float32)
    for i, img_path in enumerate(example_images[:3]):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_img = img.astype(np.float32)
        energies[i] = dms.get_sobel_map(gray_img)
    focus_map = dms.get_focus_map(energies)
    assert focus_map.shape == energies.shape
    assert focus_map.dtype == np.float32
    assert np.all(np.isfinite(focus_map))
    sum_weights = np.sum(focus_map, axis=0)
    assert np.allclose(sum_weights, 1.0, atol=1e-6)


def test_focus_map_invalid_type(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.map_type = 'invalid_type'
    energies = np.empty((3, *dms.shape), dtype=np.float32)
    for i, img_path in enumerate(example_images[:3]):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_img = img.astype(np.float32)
        energies[i] = dms.get_sobel_map(gray_img)
    with pytest.raises(InvalidOptionError):
        dms.get_focus_map(energies)


def test_focus_map_max_with_temperature(example_images):
    dms_high_temp = DepthMapStack(map_type='max', temperature=1.0)
    dms_high_temp.init(example_images[:3])
    dms_high_temp.print_message = MagicMock()
    dms_high_temp.after_step = MagicMock()
    dms_high_temp.check_running = MagicMock()
    dms_low_temp = DepthMapStack(map_type='max', temperature=0.01)
    dms_low_temp.init(example_images[:3])
    dms_low_temp.print_message = MagicMock()
    dms_low_temp.after_step = MagicMock()
    dms_low_temp.check_running = MagicMock()
    energies = np.empty((3, *dms_high_temp.shape), dtype=np.float32)
    for i, img_path in enumerate(example_images[:3]):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_img = img.astype(np.float32)
        energies[i] = dms_high_temp.get_sobel_map(gray_img)
    focus_map_high_temp = dms_high_temp.get_focus_map(energies)
    focus_map_low_temp = dms_low_temp.get_focus_map(energies)

    def weight_entropy(weights):
        epsilon = 1e-10
        return -np.sum(weights * np.log(weights + epsilon), axis=0)

    avg_entropy_high = np.mean(weight_entropy(focus_map_high_temp))
    avg_entropy_low = np.mean(weight_entropy(focus_map_low_temp))
    assert avg_entropy_low < avg_entropy_high


def test_focus_stack_disk_mode_average(example_images):
    dms = DepthMapStack(mode='i/o', map_type='average')
    dms.process = MagicMock()
    dms.process.callback.return_value = True
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    dms.init(example_images[:3])
    result = dms.focus_stack()
    assert len(result.shape) == 3
    assert result.dtype == np.uint8


def test_focus_stack_disk_mode_max(example_images):
    dms = DepthMapStack(mode='i/o', map_type='max')
    dms.process = MagicMock()
    dms.process.callback.return_value = True
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    dms.init(example_images[:3])
    result = dms.focus_stack()
    assert len(result.shape) == 3
    assert result.dtype == np.uint8


def test_focus_stack_auto_mode_disk(example_images):
    dms = DepthMapStack(mode='auto', memory_limit=0.001)
    dms.process = MagicMock()
    dms.process.callback.return_value = True
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    dms.init(example_images[:3])
    result = dms.focus_stack()
    assert len(result.shape) == 3
    assert result.dtype == np.uint8


def test_focus_stack_disk_mode_weight_power(example_images):
    dms = DepthMapStack(mode='i/o', weight_power=2.0)
    dms.process = MagicMock()
    dms.process.callback.return_value = True
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    dms.init(example_images[:3])
    result = dms.focus_stack()
    assert len(result.shape) == 3
    assert result.dtype == np.uint8


def test_focus_stack_memory_vs_disk_identical(example_images):
    dms_memory = DepthMapStack(mode='memory')
    dms_disk = DepthMapStack(mode='i/o')
    for dms in [dms_memory, dms_disk]:
        dms.process = MagicMock()
        dms.process.callback.return_value = True
        dms.print_message = MagicMock()
        dms.after_step = MagicMock()
        dms.check_running = MagicMock()
        dms.init(example_images[:3])
    result_memory = dms_memory.focus_stack()
    result_disk = dms_disk.focus_stack()
    assert np.array_equal(result_memory, result_disk)


def test_focus_stack_disk_mode_energy_smoothing(example_images):
    dms = DepthMapStack(mode='i/o', energy_smooth_size=5)
    dms.process = MagicMock()
    dms.process.callback.return_value = True
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    dms.init(example_images[:3])
    result = dms.focus_stack()
    assert len(result.shape) == 3
    assert result.dtype == np.uint8


def test_focus_stack_disk_mode_pyramid_smoothing(example_images):
    dms = DepthMapStack(mode='i/o', pyramid_smooth_size=5)
    dms.process = MagicMock()
    dms.process.callback.return_value = True
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    dms.init(example_images[:3])
    result = dms.focus_stack()
    assert len(result.shape) == 3
    assert result.dtype == np.uint8


def test_focus_stack_disk_mode_all_energy_types(example_images):
    energy_types = [
        constants.DM_ENERGY_SOBEL,
        constants.DM_ENERGY_LAPLACIAN,
        constants.DM_ENERGY_MOD_LAPLACIAN,
        constants.DM_ENERGY_VARIANCE,
        constants.DM_ENERGY_TENENGRAD
    ]
    for energy_type in energy_types:
        dms = DepthMapStack(mode='i/o', energy=energy_type)
        dms.process = MagicMock()
        dms.process.callback.return_value = True
        dms.print_message = MagicMock()
        dms.after_step = MagicMock()
        dms.check_running = MagicMock()
        dms.init(example_images[:2])
        result = dms.focus_stack()
        assert len(result.shape) == 3
        assert result.dtype == np.uint8


def test_get_focus_map_from_disk_average(example_images):
    dms = DepthMapStack(mode='i/o', map_type='average')
    dms.process = MagicMock()
    dms.print_message = MagicMock()
    dms.check_running = MagicMock()
    dms.init(example_images[:2])
    temp_dir = tempfile.mkdtemp()
    energy_files = []
    sum_energies = np.zeros(dms.shape, dtype=dms.float_type)
    for i, img_path in enumerate(example_images[:2]):
        img = read_and_validate_img(img_path, dms.shape, dms.dtype)
        gray = img_bw(img).astype(dms.float_type)
        energy_map = dms.compute_energy_map(gray)
        temp_file = os.path.join(temp_dir, f"energy_{i:06d}.npy")
        np.save(temp_file, energy_map)
        energy_files.append(temp_file)
        sum_energies += energy_map
    weights = dms.get_focus_map_from_disk_average(energy_files, sum_energies, 2)
    assert weights.shape == (2, *dms.shape)
    assert weights.dtype == dms.float_type
    assert np.all(np.isfinite(weights))


def test_get_focus_map_from_disk_max(example_images):
    dms = DepthMapStack(mode='i/o', map_type='max')
    dms.process = MagicMock()
    dms.print_message = MagicMock()
    dms.check_running = MagicMock()
    dms.init(example_images[:2])
    temp_dir = tempfile.mkdtemp()
    energy_files = []
    max_energy = np.zeros(dms.shape, dtype=dms.float_type)
    for i, img_path in enumerate(example_images[:2]):
        img = read_and_validate_img(img_path, dms.shape, dms.dtype)
        gray = img_bw(img).astype(dms.float_type)
        energy_map = dms.compute_energy_map(gray)
        temp_file = os.path.join(temp_dir, f"energy_{i:06d}.npy")
        np.save(temp_file, energy_map)
        energy_files.append(temp_file)
        max_energy = np.maximum(max_energy, energy_map)
    weights = dms.get_focus_map_from_disk_max(energy_files, max_energy, 2)
    assert weights.shape == (2, *dms.shape)
    assert weights.dtype == dms.float_type
    assert np.all(np.isfinite(weights))


@pytest.mark.parametrize("params", [
    {'map_type': 'max'},
    {'map_type': 'average'},
    {'map_type': 'average', 'weight_power': 2.0},
])
def test_focus_stack_threads_identical(example_images, params):
    results = []
    for max_threads in (1, 4):
        dms = DepthMapStack(max_threads=max_threads, **params)
        dms.process = MagicMock()
        dms.process.callback.return_value = True
        dms.print_message = MagicMock()
        dms.after_step = MagicMock()
        dms.check_running = MagicMock()
        dms.init(example_images[:4])
        results.append(dms.focus_stack())
    assert np.array_equal(results[0], results[1])


def test_frames_in_flight_respects_memory_limit():
    dms = DepthMapStack(max_threads=8, memory_limit=1)
    assert dms.frames_in_flight(300 * 1024**2) == 3
    assert dms.frames_in_flight(4 * 1024**3) == 1
    assert dms.frames_in_flight(1) == 8
    assert dms.frames_in_flight(300 * 1024**2, resident_bytes=512 * 1024**2) == 1
    assert dms.frames_in_flight(300 * 1024**2, resident_bytes=2 * 1024**3) == 1


def test_ordered_parallel_map_order_and_early_stop():
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from shinestacker.algorithms.depth_map import ordered_parallel_map
    started = []
    lock = threading.Lock()

    def work(i):
        with lock:
            started.append(i)
        time.sleep(0.01 * (5 - i % 5))
        return i * i

    with ThreadPoolExecutor(4) as executor:
        results = list(ordered_parallel_map(executor, work, range(12), 3))
        assert results == [i * i for i in range(12)]
        started.clear()
        results = ordered_parallel_map(executor, work, range(100), 3)
        assert next(results) == 0
        results.close()
    assert len(started) <= 5
