"""RGBA / alpha-channel support for the Laplacian pyramid focus stacker.

A synthetic focus stack of a semi-transparent disc: the disc's sharp-focus
frame varies across the stack, and a soft alpha edge is constant. We check
that the stacked result:
  * keeps 4 channels,
  * has opaque centre / transparent background / a fractional edge band,
  * picks colour from the in-focus frame inside the disc.
"""
import numpy as np
import cv2
import pytest

from shinestacker.algorithms.stack_framework import StackJob
from shinestacker.algorithms.stack import FocusStack
from shinestacker.algorithms.pyramid import PyramidStack
from shinestacker.algorithms.utils import read_img, has_alpha

H = W = 256
MAXV = 65535


def _radial(cx, cy):
    yy, xx = np.mgrid[0:H, 0:W]
    return np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)


def _alpha_disc():
    r = _radial(W / 2, H / 2)
    a = np.clip((70.0 - r) / 12.0, 0.0, 1.0)          # soft edge around r=64
    return (a * MAXV).astype(np.uint16)


def _make_frame(sharp: bool, tint):
    """A textured disc; `sharp` controls whether the texture is crisp or blurred."""
    rng = np.random.default_rng(0)
    texture = rng.integers(0, MAXV, size=(H, W), dtype=np.uint16)
    bgr = np.stack([np.full((H, W), t, np.uint16) for t in tint], axis=2)
    bgr = (bgr.astype(np.float64) * 0.6 + texture[..., None].astype(np.float64) * 0.4)
    bgr = bgr.astype(np.uint16)
    if not sharp:
        bgr = cv2.GaussianBlur(bgr, (0, 0), 3)
    alpha = _alpha_disc()
    return np.concatenate([bgr, alpha[..., None]], axis=2)


@pytest.fixture
def rgba_stack(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    # frame 0 sharp (blue tint), frame 1 blurred, frame 2 sharp too but we make
    # frame 1 the only sharp one in a sub-region to force a real selection.
    frames = [
        _make_frame(sharp=True, tint=(60000, 8000, 8000)),
        _make_frame(sharp=False, tint=(8000, 60000, 8000)),
        _make_frame(sharp=False, tint=(8000, 8000, 60000)),
    ]
    for i, f in enumerate(frames):
        cv2.imwrite(str(src / f"f{i:02d}.tif"), f,
                    [int(cv2.IMWRITE_TIFF_COMPRESSION), 1])
    return tmp_path, src


def _run(tmp_path, src):
    job = StackJob("job", str(tmp_path), input_path="src")
    job.add_action(FocusStack("stk", PyramidStack(), output_path="out",
                              prefix="s_"))
    job.run()
    outs = list((tmp_path / "out").glob("*.tif"))
    assert len(outs) == 1
    return read_img(str(outs[0]))


def test_output_keeps_alpha(rgba_stack):
    tmp_path, src = rgba_stack
    out = _run(tmp_path, src)
    assert has_alpha(out), f"expected 4 channels, got shape {out.shape}"
    assert out.dtype == np.uint16


def test_alpha_regions(rgba_stack):
    tmp_path, src = rgba_stack
    out = _run(tmp_path, src)
    alpha = out[..., 3].astype(np.float64) / MAXV
    # centre opaque
    assert alpha[H // 2, W // 2] > 0.98
    # far corner transparent
    assert alpha[5, 5] < 0.02
    # a fractional band exists near the disc edge
    band = alpha[(alpha > 0.05) & (alpha < 0.95)]
    assert band.size > 200


def test_no_background_colour_bleed(rgba_stack):
    tmp_path, src = rgba_stack
    out = _run(tmp_path, src)
    alpha = out[..., 3].astype(np.float64) / MAXV
    bgr = out[..., :3].astype(np.float64)
    # where fully transparent, straight colour should be ~0 (un-premultiplied)
    transparent = alpha < 0.01
    assert bgr[transparent].mean() < 0.02 * MAXV


def test_align_then_stack_rgba(tmp_path):
    """AlignFrames must carry the 4th channel through the warp, and the
    subsequent pyramid stack must still emit RGBA."""
    from shinestacker.algorithms.stack_framework import CombinedActions
    from shinestacker.algorithms.align import AlignFrames

    src = tmp_path / "src"
    src.mkdir()
    base = _make_frame(sharp=True, tint=(40000, 20000, 20000))
    shifts = [(0, 0), (3, -2), (-2, 4)]
    for i, (dx, dy) in enumerate(shifts):
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        shifted = cv2.warpAffine(base, M, (W, H), borderMode=cv2.BORDER_REFLECT101)
        cv2.imwrite(str(src / f"f{i:02d}.tif"), shifted,
                    [int(cv2.IMWRITE_TIFF_COMPRESSION), 1])

    job = StackJob("job", str(tmp_path), input_path="src")
    job.add_action(CombinedActions("align", [AlignFrames()], output_path="aligned"))
    job.add_action(FocusStack("stk", PyramidStack(), input_path="aligned",
                              output_path="out"))
    job.run()

    aligned = read_img(str(next((tmp_path / "aligned").glob("*.tif"))))
    assert has_alpha(aligned), "align dropped the alpha channel"
    out = read_img(str(next((tmp_path / "out").glob("*.tif"))))
    assert has_alpha(out)


def test_reference_rgb_only_stack_still_3ch(tmp_path):
    """Regression: plain RGB stacks are untouched by the alpha path."""
    src = tmp_path / "src"
    src.mkdir()
    rng = np.random.default_rng(1)
    for i in range(3):
        img = rng.integers(0, 255, size=(128, 128, 3), dtype=np.uint8)
        cv2.imwrite(str(src / f"f{i}.tif"), img,
                    [int(cv2.IMWRITE_TIFF_COMPRESSION), 1])
    job = StackJob("job", str(tmp_path), input_path="src")
    job.add_action(FocusStack("stk", PyramidStack(), output_path="out"))
    job.run()
    out = read_img(str(next((tmp_path / "out").glob("*.tif"))))
    assert out.ndim == 3 and out.shape[2] == 3


def test_rgba_rejected_by_non_alpha_stackers(rgba_stack):
    """DepthMap / tiled pyramid must fail loudly on RGBA, not silently drop it."""
    from shinestacker.algorithms.depth_map import DepthMapStack
    from shinestacker.algorithms.pyramid_tiles import PyramidTilesStack
    from shinestacker.core.exceptions import InvalidOptionError

    tmp_path, src = rgba_stack
    for algo in (DepthMapStack, PyramidTilesStack):
        job = StackJob("job", str(tmp_path), input_path="src")
        job.add_action(FocusStack("stk", algo(), output_path=f"out_{algo.__name__}"))
        with pytest.raises((InvalidOptionError, RuntimeError)):
            job.run()


if __name__ == "__main__":
    import subprocess
    subprocess.run(["pytest", "-q", __file__], check=False)
