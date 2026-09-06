#!/usr/bin/env python3
"""End-to-end RGBA focus-stack test harness for the alpha-channel fork.

Takes a folder of focus-stack frames, attaches an alpha matte to each, runs
AlignFrames + a stacker, and writes the RGBA result plus a checkerboard-
composite preview so you can eyeball the matte edge.

Matte source (--matte):
  folder:<dir>   per-frame masks in <dir> (matched by sorted order); white=opaque
  const:<dir>    a single mask image in <dir>, reused for every frame
  luma:<lo>,<hi> threshold the frame luminance, soft-ramp between lo..hi (0-255)
  rembg          use rembg (birefnet-general) if installed

Examples:
  python tools/rgba_stack.py ~/pics/bug_angle01 --matte luma:35,60 --stacker pyramid
  python tools/rgba_stack.py in/ --matte const:mattes/ --stacker depthmap -o out/
"""
import argparse
import glob
import os
import sys
import shutil

import numpy as np
import cv2

from shinestacker.algorithms.stack_framework import StackJob, CombinedActions
from shinestacker.algorithms.align import AlignFrames
from shinestacker.algorithms.stack import FocusStack
from shinestacker.algorithms.pyramid import PyramidStack
from shinestacker.algorithms.pyramid_tiles import PyramidTilesStack
from shinestacker.algorithms.pyramid_auto import PyramidAutoStack
from shinestacker.algorithms.depth_map import DepthMapStack
from shinestacker.algorithms.utils import read_img, has_alpha

STACKERS = {
    "pyramid": lambda: PyramidStack(),
    "tiles": lambda: PyramidTilesStack(),
    "depthmap": lambda: DepthMapStack(),
    "auto": lambda: PyramidAutoStack(),
}
EXTS = ("*.tif", "*.tiff", "*.png", "*.jpg", "*.jpeg",
        "*.dng", "*.cr2", "*.cr3", "*.nef", "*.arw", "*.rw2", "*.orf")


def list_images(folder):
    files = []
    for e in EXTS:
        files += glob.glob(os.path.join(folder, e))
        files += glob.glob(os.path.join(folder, e.upper()))
    return sorted(set(files))


def to_u16(img):
    if img.dtype == np.uint16:
        return img
    if img.dtype == np.uint8:
        return (img.astype(np.uint16) * 257)
    return np.clip(img, 0, 1).astype(np.float32).__mul__(65535).astype(np.uint16)


def luma_matte(bgr_u16, lo, hi):
    g = cv2.cvtColor(bgr_u16, cv2.COLOR_BGR2GRAY).astype(np.float32) / 65535.0
    a = np.clip((g - lo / 255.0) / max(1e-6, (hi - lo) / 255.0), 0, 1)
    return (a * 65535).astype(np.uint16)


def load_mask(path, shape_hw):
    m = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if m is None:
        sys.exit(f"cannot read mask {path}")
    if m.ndim == 3:
        m = m[..., 3] if m.shape[2] == 4 else cv2.cvtColor(m, cv2.COLOR_BGR2GRAY)
    if m.shape[:2] != shape_hw:
        m = cv2.resize(m, (shape_hw[1], shape_hw[0]), interpolation=cv2.INTER_LINEAR)
    return to_u16(m)


def rembg_matte(bgr_u16):
    try:
        from rembg import remove, new_session
    except ImportError:
        sys.exit("rembg not installed:  pip install rembg onnxruntime")
    sess = new_session("birefnet-general")
    rgb8 = cv2.cvtColor((bgr_u16 >> 8).astype(np.uint8), cv2.COLOR_BGR2RGB)
    out = remove(rgb8, session=sess)  # RGBA
    return to_u16(out[..., 3])


def build_rgba(src_files, matte_spec, work_src):
    os.makedirs(work_src, exist_ok=True)
    mask_files = None
    const_mask = None
    if matte_spec.startswith("folder:"):
        mask_files = list_images(matte_spec.split(":", 1)[1])
        if len(mask_files) != len(src_files):
            sys.exit(f"{len(mask_files)} masks for {len(src_files)} frames")
    elif matte_spec.startswith("const:"):
        cm = list_images(matte_spec.split(":", 1)[1])
        if not cm:
            sys.exit("no mask found for const: matte")
        const_mask = cm[0]

    for i, f in enumerate(src_files):
        bgr = to_u16(read_img(f))[..., :3]
        if mask_files:
            a = load_mask(mask_files[i], bgr.shape[:2])
        elif const_mask:
            a = load_mask(const_mask, bgr.shape[:2])
        elif matte_spec.startswith("luma:"):
            lo, hi = (float(x) for x in matte_spec.split(":", 1)[1].split(","))
            a = luma_matte(bgr, lo, hi)
        elif matte_spec == "rembg":
            a = rembg_matte(bgr)
        else:
            sys.exit(f"unknown --matte {matte_spec}")
        rgba = np.concatenate([bgr, a[..., None]], axis=2)
        cv2.imwrite(os.path.join(work_src, f"f{i:04d}.tif"), rgba,
                    [int(cv2.IMWRITE_TIFF_COMPRESSION), 1])
    print(f"wrote {len(src_files)} RGBA frames -> {work_src}")


def checkerboard_preview(rgba, path, sq=24):
    prev = (rgba[..., :3] >> 8).astype(np.uint8)
    a = rgba[..., 3:4].astype(np.float32) / 65535.0
    ch = (np.indices(rgba.shape[:2]).sum(0) // sq) % 2
    bg = np.where(ch[..., None] == 0, 190, 130).astype(np.uint8)
    cv2.imwrite(path, (prev * a + bg * (1 - a)).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="folder of focus-stack frames")
    ap.add_argument("--matte", required=True,
                    help="folder:<dir> | const:<dir> | luma:<lo>,<hi> | rembg")
    ap.add_argument("--stacker", default="pyramid", choices=list(STACKERS))
    ap.add_argument("--no-align", action="store_true", help="skip AlignFrames")
    ap.add_argument("-o", "--out", default=None, help="output folder (default: <src>/rgba_out)")
    args = ap.parse_args()

    src_files = list_images(args.src)
    if len(src_files) < 2:
        sys.exit(f"need >=2 frames in {args.src}, found {len(src_files)}")
    print(f"{len(src_files)} source frames")

    out_dir = args.out or os.path.join(args.src, "rgba_out")
    work = os.path.join(out_dir, "_work")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(out_dir, exist_ok=True)

    build_rgba(src_files, args.matte, os.path.join(work, "src"))

    job = StackJob("rgba", work, input_path="src")
    stack_input = "src"
    if not args.no_align:
        job.add_action(CombinedActions("align", [AlignFrames()], output_path="aligned"))
        stack_input = "aligned"
    job.add_action(FocusStack("stack", STACKERS[args.stacker](),
                              input_path=stack_input, output_path="stacked"))
    job.run()

    result_path = next(iter(glob.glob(os.path.join(work, "stacked", "*.tif"))), None)
    if result_path is None:
        sys.exit("no stacked output produced")
    rgba = read_img(result_path)
    final = os.path.join(out_dir, f"stacked_{args.stacker}.tif")
    shutil.copy(result_path, final)
    checkerboard_preview(rgba, os.path.join(out_dir, f"preview_{args.stacker}.png"))

    a = rgba[..., 3].astype(np.float32) / 65535.0
    print(f"\nresult: {rgba.shape} {rgba.dtype}  has_alpha={has_alpha(rgba)}")
    print(f"  alpha: opaque {(a > 0.98).mean():.1%}  transparent {(a < 0.02).mean():.1%}"
          f"  edge-band {((a > 0.05) & (a < 0.95)).mean():.1%}")
    if (a < 0.01).any():
        print(f"  straight RGB mean where transparent: "
              f"{rgba[..., :3].astype(float)[a < 0.01].mean():.1f} / 65535")
    print(f"\n  {final}\n  {os.path.join(out_dir, f'preview_{args.stacker}.png')}")


if __name__ == "__main__":
    main()
