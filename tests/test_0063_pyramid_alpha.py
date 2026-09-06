"""RGBA / alpha-channel support for the pyramid + depth-map focus stackers.

A synthetic focus stack of a semi-transparent disc: which frame is in sharp
focus varies across the stack, the soft alpha edge is constant. We check that
every alpha-capable stacker produces a result that:
  * keeps 4 channels,
  * has opaque centre / transparent background / a fractional edge band,
  * carries no straight-colour bleed into fully transparent regions,
  * picks colour from the in-focus frame inside the disc.
"""
import numpy as np
import cv2
import pytest

from shinestacker.algorithms.stack_framework import StackJob, CombinedActions
from shinestacker.algorithms.stack import FocusStack
from shinestacker.algorithms.align import AlignFrames
from shinestacker.algorithms.pyramid import PyramidStack
from shinestacker.algorithms.pyramid_tiles import PyramidTilesStack
from shinestacker.algorithms.pyramid_auto import PyramidAutoStack
from shinestacker.algorithms.depth_map import DepthMapStack
from shinestacker.algorithms.utils import read_img, has_alpha

H = W = 256
MAXV = 65535

ALPHA_STACKERS = [
    pytest.param(lambda: PyramidStack(), id="pyramid"),
    pytest.param(lambda: PyramidTilesStack(tile_size=96, max_threads=1), id="tiles"),
    pytest.param(lambda: DepthMapStack(), id="depthmap"),
    pytest.param(lambda: PyramidAutoStack(), id="auto"),
]


def _alpha_disc():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt((xx - W / 2) ** 2 + (yy - H / 2) ** 2)
    return (np.clip((70.0 - r) / 12.0, 0.0, 1.0) * MAXV).astype(np.uint16)


def _make_frame(sharp, tint, seed=0):
    rng = np.random.default_rng(seed)
    texture = rng.integers(0, MAXV, size=(H, W), dtype=np.uint16)
    bgr = np.stack([np.full((H, W), t, np.uint16) for t in tint], axis=2)
    bgr = (bgr.astype(np.float64) * 0.5 + texture[..., None].astype(np.float64) * 0.5)
    bgr = bgr.astype(np.uint16)
    if not sharp:
        bgr = cv2.GaussianBlur(bgr, (0, 0), 3)
    return np.concatenate([bgr, _alpha_disc()[..., None]], axis=2)


@pytest.fixture
def rgba_src(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    # only frame 1 is sharp -> its (green) colour should win inside the disc
    frames = [
        _make_frame(sharp=False, tint=(60000, 8000, 8000), seed=1),
        _make_frame(sharp=True, tint=(8000, 60000, 8000), seed=2),
        _make_frame(sharp=False, tint=(8000, 8000, 60000), seed=3),
    ]
    for i, f in enumerate(frames):
        cv2.imwrite(str(src / f"f{i:02d}.tif"), f, [int(cv2.IMWRITE_TIFF_COMPRESSION), 1])
    return tmp_path


def _run(tmp_path, make_algo, input_path="src"):
    job = StackJob("job", str(tmp_path), input_path=input_path)
    job.add_action(FocusStack("stk", make_algo(), output_path="out", prefix="s_"))
    job.run()
    outs = list((tmp_path / "out").glob("*.tif"))
    assert len(outs) == 1
    return read_img(str(outs[0]))


@pytest.mark.parametrize("make_algo", ALPHA_STACKERS)
def test_output_keeps_alpha(rgba_src, make_algo):
    out = _run(rgba_src, make_algo)
    assert has_alpha(out), f"expected 4 channels, got {out.shape}"
    assert out.dtype == np.uint16


@pytest.mark.parametrize("make_algo", ALPHA_STACKERS)
def test_alpha_regions(rgba_src, make_algo):
    out = _run(rgba_src, make_algo)
    a = out[..., 3].astype(np.float64) / MAXV
    assert a[H // 2, W // 2] > 0.98            # centre opaque
    assert a[5, 5] < 0.02                      # corner transparent
    assert a[(a > 0.05) & (a < 0.95)].size > 200   # fractional edge band


@pytest.mark.parametrize("make_algo", ALPHA_STACKERS)
def test_no_transparent_colour_bleed(rgba_src, make_algo):
    out = _run(rgba_src, make_algo)
    a = out[..., 3].astype(np.float64) / MAXV
    bgr = out[..., :3].astype(np.float64)
    assert bgr[a < 0.01].mean() < 0.02 * MAXV


@pytest.mark.parametrize("make_algo", ALPHA_STACKERS)
def test_alpha_follows_focus_selection(rgba_src, make_algo):
    """Inside the disc the sharp (green) frame should dominate the result."""
    out = _run(rgba_src, make_algo)
    c = out[H // 2, W // 2, :3].astype(float)   # BGR
    assert c[1] > c[0] and c[1] > c[2]


@pytest.mark.parametrize("make_algo", ALPHA_STACKERS)
def test_align_then_stack_rgba(tmp_path, make_algo):
    src = tmp_path / "src"
    src.mkdir()
    base = _make_frame(sharp=True, tint=(40000, 20000, 20000), seed=7)
    for i, (dx, dy) in enumerate([(0, 0), (3, -2), (-2, 4)]):
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        cv2.imwrite(str(src / f"f{i:02d}.tif"),
                    cv2.warpAffine(base, M, (W, H), borderMode=cv2.BORDER_REFLECT101),
                    [int(cv2.IMWRITE_TIFF_COMPRESSION), 1])
    job = StackJob("job", str(tmp_path), input_path="src")
    job.add_action(CombinedActions("align", [AlignFrames()], output_path="aligned"))
    job.add_action(FocusStack("stk", make_algo(), input_path="aligned", output_path="out"))
    job.run()
    aligned = read_img(str(next((tmp_path / "aligned").glob("*.tif"))))
    assert has_alpha(aligned), "align dropped the alpha channel"
    assert has_alpha(read_img(str(next((tmp_path / "out").glob("*.tif")))))


def test_align_balance_rgba(tmp_path):
    """BalanceFrames must colour-correct RGB only and pass alpha through."""
    from shinestacker.algorithms.balance import BalanceFrames
    from shinestacker.config.constants import constants
    src = tmp_path / "src"
    src.mkdir()
    for i in range(3):
        f = _make_frame(sharp=True, tint=(30000 + i * 6000, 30000, 30000 - i * 4000), seed=i)
        cv2.imwrite(str(src / f"f{i:02d}.tif"), f, [int(cv2.IMWRITE_TIFF_COMPRESSION), 1])
    job = StackJob("job", str(tmp_path), input_path="src")
    job.add_action(CombinedActions(
        "align", [AlignFrames(), BalanceFrames(channel=constants.BALANCE_RGB)],
        output_path="aligned"))
    job.run()
    for p in (tmp_path / "aligned").glob("*.tif"):
        assert has_alpha(read_img(str(p)))


def test_reference_rgb_only_untouched(tmp_path):
    """Plain RGB stacks still emit 3 channels."""
    src = tmp_path / "src"
    src.mkdir()
    rng = np.random.default_rng(1)
    for i in range(3):
        cv2.imwrite(str(src / f"f{i}.tif"),
                    rng.integers(0, 255, (128, 128, 3), np.uint8),
                    [int(cv2.IMWRITE_TIFF_COMPRESSION), 1])
    out = _run(tmp_path, lambda: PyramidStack())
    assert out.ndim == 3 and out.shape[2] == 3


def test_non_alpha_algo_rejects_rgba(rgba_src):
    """A stacker with supports_alpha = False must fail loudly, not drop alpha."""
    from shinestacker.core.exceptions import InvalidOptionError

    class NoAlphaPyramid(PyramidStack):
        supports_alpha = False

    job = StackJob("job", str(rgba_src), input_path="src")
    job.add_action(FocusStack("stk", NoAlphaPyramid(), output_path="out"))
    with pytest.raises((InvalidOptionError, RuntimeError)):
        job.run()


if __name__ == "__main__":
    import subprocess
    subprocess.run(["pytest", "-q", __file__], check=False)
