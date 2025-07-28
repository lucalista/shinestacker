import pytest
import numpy as np
import cv2
import os
from unittest.mock import MagicMock
from shinestacker.config.constants import constants
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
    assert dms.map_type == constants.DEFAULT_DM_MAP
    assert dms.energy == constants.DEFAULT_DM_ENERGY


def test_sobel_map_with_examples(example_images):
    dms = DepthMapStack()
    gray_images = []
    for img_path in example_images[:3]:
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_images.append(img.astype(np.float32))
    gray_images = np.array(gray_images)
    sobel_map = dms.get_sobel_map(gray_images)
    assert sobel_map.shape == gray_images.shape
    assert sobel_map.dtype == np.float32
    assert np.all(sobel_map >= 0)  # Energy should always be positive

def test_focus_stack_with_examples(example_images):
    dms = DepthMapStack()
    dms.process = MagicMock()
    dms.process.callback.return_value = True  # Keep running
    dms.print_message = MagicMock()
    result = dms.focus_stack(example_images[:3])
    assert len(result.shape) == 3
    assert result.dtype == np.uint8
    first_input = cv2.imread(example_images[0], cv2.IMREAD_GRAYSCALE)
    assert not np.array_equal(result, first_input)


def test_pyramid_blend_with_examples(example_images):
    dms = DepthMapStack(levels=4)
    images = []
    for img_path in example_images[:3]:
        img = cv2.imread(img_path).astype(np.float32)
        images.append(img)
    images = np.array(images)
    weights = np.zeros((len(images), images[0].shape[0], images[0].shape[1]), dtype=np.float32)
    weights[1] = 0.7
    weights[0] = 0.2
    weights[2] = 0.1
    blended = dms.pyramid_blend(images, weights)
    assert blended.shape == images[0].shape
    assert blended.dtype == np.float32
    middle_img = images[1]
    correlation = np.corrcoef(blended.flatten(), middle_img.flatten())[0,1]
    assert correlation > 0.5


def test_performance_with_all_images(example_images):
    dms = DepthMapStack()
    dms.process = MagicMock()
    dms.process.callback.return_value = True
    
    # Time the operation (pytest will show this in output)
    import time
    start = time.time()
    result = dms.focus_stack(example_images)  # All 7 images
    elapsed = time.time() - start
    
    # Verify output
    assert result.shape[0] > 0 and result.shape[1] > 0
    print(f"\nFocus stacking {n_images} images took {elapsed:.2f} seconds")
    
    # Optionally save the result for visual inspection
    output_dir = "examples/output/"
    os.makedirs(output_dir, exist_ok=True)
    cv2.imwrite(os.path.join(output_dir, "focus_stacked.jpg"), result)

