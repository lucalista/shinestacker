# pylint: disable=C0114, C0116, E1101
import cv2
import numpy as np
import pytest
from shinestacker.algorithms.pyramid import PyramidStack


def reference_fuse(algo, laplacians):
    images = np.stack(laplacians, axis=0)
    images_32 = images if images.dtype == np.float32 else images.astype(np.float32)
    energies = np.empty(images.shape[:3], dtype=np.float32)
    for i, image in enumerate(images_32):
        gray = cv2.cvtColor(image[..., :3], cv2.COLOR_BGR2GRAY)
        energies[i] = algo.convolve(gray * gray)
    best = np.argmax(energies, axis=0)
    rows = np.arange(best.shape[0])[:, None]
    cols = np.arange(best.shape[1])
    return images[best, rows, cols, :]


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
@pytest.mark.parametrize("channels", [3, 4])
@pytest.mark.parametrize("shape", [(31, 47), (131, 47)])
def test_fuse_laplacian_matches_stacked_reference(dtype, channels, shape):
    algo = PyramidStack()
    rng = np.random.default_rng(42)
    height, width = shape
    laplacians = [
        rng.normal(0, 20, (height, width * 2, channels)).astype(dtype)[:, ::2, :]
        for _ in range(4)
    ]

    expected = reference_fuse(algo, laplacians)
    actual = algo.fuse_laplacian(laplacians)

    assert actual.dtype == expected.dtype
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_fuse_laplacian_first_frame_wins_ties(dtype):
    algo = PyramidStack()
    rgb = np.arange(31 * 47 * 3, dtype=np.float64).reshape(31, 47, 3) % 17
    rgb = rgb.astype(dtype)
    laplacians = []
    for i in range(4):
        alpha = np.full((31, 47, 1), i, dtype=dtype)
        laplacians.append(np.concatenate((rgb, alpha), axis=2))

    actual = algo.fuse_laplacian(laplacians)

    np.testing.assert_array_equal(actual[..., :3], rgb)
    assert np.all(actual[..., 3] == 0)


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_fuse_laplacian_matches_reference_for_near_ties(dtype):
    algo = PyramidStack()
    rng = np.random.default_rng(7)
    rgb = rng.normal(0, 20, (31, 47, 3)).astype(dtype)
    first = np.concatenate((rgb, np.zeros((31, 47, 1), dtype=dtype)), axis=2)
    second_rgb = rgb + 1e-5 * rgb
    second = np.concatenate((second_rgb, np.ones((31, 47, 1), dtype=dtype)), axis=2)
    laplacians = [first, second]

    expected = reference_fuse(algo, laplacians)
    actual = algo.fuse_laplacian(laplacians)

    np.testing.assert_array_equal(actual, expected)
