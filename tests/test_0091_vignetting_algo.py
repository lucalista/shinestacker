import pytest
import numpy as np
import cv2
import os
from unittest.mock import MagicMock
from shinestacker.algorithms.vignetting import (
    Vignetting, radial_mean_intensity, fit_sigmoid, correct_vignetting,
    sigmoid_model)

n_images = 4


@pytest.fixture
def vignetted_images():
    image_dir = "examples/input/img-vignetted/"
    filenames = [os.path.join(image_dir, f"vig-000{i}.jpg") for i in range(n_images)]
    for f in filenames:
        if not os.path.exists(f):
            pytest.skip(f"Test image {f} not found")
    images = [cv2.imread(f) for f in filenames]
    return filenames, images


@pytest.fixture
def vignetting_instance():
    process_mock = MagicMock()
    process_mock.counts = n_images
    process_mock.plot_path = "plots"
    process_mock.working_path = "."
    process_mock.name = "test_vignetting"
    process_mock.id = 123
    vignetting = Vignetting(
        enabled=True,
        apply_correction=True,
        plot_correction=False,
        plot_summary=False,
        r_steps=20,
        black_threshold=10,
        max_correction=0.9
    )
    vignetting.process = process_mock
    vignetting.corrections = [np.full(n_images, None, dtype=float) for _ in vignetting.percentiles]
    vignetting.r_max = np.sqrt((2000 / 2)**2 + (1333 / 2)**2)
    vignetting.w_2 = 2000 / 2
    vignetting.h_2 = 1333 / 2
    return vignetting


def test_radial_mean_intensity(vignetting_instance, vignetted_images):
    _, images = vignetted_images
    img_gray = cv2.cvtColor(images[0], cv2.COLOR_BGR2GRAY)
    radii, intensities = radial_mean_intensity(img_gray, vignetting_instance.r_steps)
    assert len(radii) == vignetting_instance.r_steps
    assert len(intensities) == vignetting_instance.r_steps
    assert radii[0] > 0
    assert radii[-1] > radii[0]
    if vignetting_instance.r_steps > 10:
        assert np.mean(intensities[:5]) > np.mean(intensities[-5:])


def test_sigmoid_fit(vignetting_instance, vignetted_images):
    _, images = vignetted_images
    img_gray = cv2.cvtColor(images[0], cv2.COLOR_BGR2GRAY)
    radii, intensities = radial_mean_intensity(img_gray, vignetting_instance.r_steps)
    params = fit_sigmoid(radii, intensities)
    assert params is not None
    i0, k, r0 = params
    assert i0 > 0
    assert 0 < r0 < radii[-1]


def test_correct_vignetting(vignetting_instance, vignetted_images):
    _, images = vignetted_images
    img = images[0]
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    radii, intensities = radial_mean_intensity(img_gray, vignetting_instance.r_steps)
    params = fit_sigmoid(radii, intensities)
    v0 = sigmoid_model(0, *params)
    corrected = correct_vignetting(img, params=params, v0=v0)
    assert corrected.shape == img.shape
    assert corrected.dtype == img.dtype
    h, w = img.shape[:2]
    center_patch = img[h // 4:3 * h // 4, w // 4:3 * w // 4]
    top_edge = img[:h // 8, :]
    bottom_edge = img[-h // 8:, :]
    left_edge = img[:, :w // 8]
    right_edge = img[:, -w // 8:]
    orig_center_mean = np.mean(center_patch)
    orig_edge_means = [
        np.mean(top_edge),
        np.mean(bottom_edge),
        np.mean(left_edge),
        np.mean(right_edge)
    ]
    orig_ratio = orig_center_mean / np.mean(orig_edge_means)
    corrected_center = corrected[h // 4:3 * h // 4, w // 4:3 * w // 4]
    corrected_edge_means = [
        np.mean(corrected[:h // 8, :]),
        np.mean(corrected[-h // 8:, :]),
        np.mean(corrected[:, :w // 8]),
        np.mean(corrected[:, -w // 8:])
    ]
    corrected_ratio = np.mean(corrected_center) / np.mean(corrected_edge_means)
    assert abs(corrected_ratio - 1) < abs(orig_ratio - 1)


def test_run_frame(vignetting_instance, vignetted_images):
    filenames, images = vignetted_images
    vignetting_instance.corrections = [
        np.full(len(images), None, dtype=float) for _ in vignetting_instance.percentiles]
    result = vignetting_instance.run_frame(0, 0, images[0])
    assert result.shape == images[0].shape
    assert result.dtype == images[0].dtype
    if vignetting_instance.apply_correction:
        assert not np.array_equal(result, images[0])
    assert vignetting_instance.process.sub_message_r.call_count > 0
    assert vignetting_instance.process.sub_message.call_count > 0
    assert vignetting_instance.corrections[0][0] is not None


def test_end_to_end_processing(vignetting_instance, vignetted_images):
    filenames, images = vignetted_images
    vignetting_instance.begin(vignetting_instance.process)
    for idx, img in enumerate(images):
        result = vignetting_instance.run_frame(idx, 0, img)
        assert result is not None
    vignetting_instance.end()
    for corrections in vignetting_instance.corrections:
        assert len(corrections) == len(images)
        assert not all(v is None for v in corrections)
