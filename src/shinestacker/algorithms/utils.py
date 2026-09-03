# pylint: disable=C0114, C0116, E1101, R0914, W0718, C0103
import os
import sys
import numpy as np
import cv2
import tifffile
import rawpy
from .. core.exceptions import ShapeError, BitDepthError, PathTooLong, InvalidWinPath
from .. config.app_config import AppConfig


def get_path_extension(path):
    return os.path.splitext(path)[1].lstrip('.')


def check_windows_path(path):
    if not sys.platform.startswith('win'):
        return
    try:
        path.encode('ascii')
    except UnicodeEncodeError as e:
        raise InvalidWinPath(path) from e
    abs_path = os.path.abspath(path)
    if len(abs_path) > 260:
        try:
            # pylint: disable=C0415, E0401
            import winreg  # Windows only
            # pylint: enable=C0415, E0401
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"SYSTEM\CurrentControlSet\Control\FileSystem") as key:
                if winreg.QueryValueEx(key, "LongPathsEnabled")[0] == 0:
                    raise PathTooLong(abs_path)
        except Exception as e:
            raise PathTooLong(abs_path) from e


EXTENSIONS_TIF = ['tif', 'tiff']
EXTENSIONS_JPG = ['jpg', 'jpeg']
EXTENSIONS_PNG = ['png']
EXTENSIONS_PDF = ['pdf']
EXTENSIONS_RAW = ["arw", "cr2", "cr3", "dng", "nef", "orf", "pef", "raf", "raw", "rw2", "srw"]
EXTENSIONS_SUPPORTED_OUT = EXTENSIONS_TIF + EXTENSIONS_JPG + EXTENSIONS_PNG
EXTENSIONS_SUPPORTED_IN = EXTENSIONS_SUPPORTED_OUT + EXTENSIONS_RAW


def _make_gui_filter(exts):
    return " ".join([f"*.{ext} *.{ext.upper()}" for ext in exts])


EXTENSIONS_GUI_STR_IN = _make_gui_filter(EXTENSIONS_SUPPORTED_IN)
EXTENSIONS_GUI_STR_OUT = _make_gui_filter(EXTENSIONS_SUPPORTED_OUT)
EXTENSION_GUI_TIF = _make_gui_filter(EXTENSIONS_TIF)
EXTENSION_GUI_JPG = _make_gui_filter(EXTENSIONS_JPG)
EXTENSION_GUI_PNG = _make_gui_filter(EXTENSIONS_PNG)


def extension_in(path, exts):
    return get_path_extension(path).lower() in exts


def extension_tif(path):
    return extension_in(path, EXTENSIONS_TIF)


def extension_jpg(path):
    return extension_in(path, EXTENSIONS_JPG)


def extension_png(path):
    return extension_in(path, EXTENSIONS_PNG)


def extension_raw(path):
    return extension_in(path, EXTENSIONS_RAW)


def extension_pdf(path):
    return extension_in(path, EXTENSIONS_PDF)


def extension_tif_jpg(path):
    return extension_in(path, EXTENSIONS_TIF + EXTENSIONS_JPG)


def extension_tif_png(path):
    return extension_in(path, EXTENSIONS_TIF + EXTENSIONS_PNG)


def extension_jpg_png(path):
    return extension_in(path, EXTENSIONS_JPG + EXTENSIONS_PNG)


def extension_jpg_tif_png(path):
    return extension_in(path, EXTENSIONS_JPG + EXTENSIONS_TIF + EXTENSIONS_PNG)


def extension_supported_input(path):
    return extension_in(path, EXTENSIONS_SUPPORTED_IN)


def extension_supported_output(path):
    return extension_in(path, EXTENSIONS_SUPPORTED_OUT)


def get_output_extension(ext):
    return "tif" if ext.lower() in EXTENSIONS_RAW else ext.lower()


def get_output_filename(input_filename):
    pre, ext = os.path.splitext(input_filename)
    return pre + "." + get_output_extension(ext[1:])


def read_img(file_path):
    check_windows_path(file_path)
    if not os.path.isfile(file_path):
        raise RuntimeError("File does not exist: " + file_path)
    img = None
    if extension_raw(file_path):
        with rawpy.imread(file_path) as raw:
            rgb = raw.postprocess(
                output_bps=16, output_color=rawpy.ColorSpace.sRGB, use_camera_wb=True,
                no_auto_bright=not AppConfig.get('raw_formats')['auto_bright'],
                auto_bright_thr=AppConfig.get('raw_formats')['auto_bright_thr'] / 100.0)
            img = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    elif extension_jpg(file_path):
        img = cv2.imread(file_path)
    elif extension_tif(file_path):
        try:
            img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise RuntimeError("OpenCV imgread returned empty file")
        except Exception:
            img = tifffile.imread(file_path)
            if img.ndim == 4:  # Multi-page color image
                img = img[0]
            elif img.ndim == 3 and img.shape[0] > 1 and img.shape[2] not in [3, 4]:
                img = img[0]
            if img.ndim == 3 and img.shape[2] in [3, 4]:
                if img.shape[2] == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                elif img.shape[2] == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA)
    elif extension_png(file_path):
        img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
    return img


def write_img(file_path, img):
    if img is None:
        raise RuntimeError("Trying to write null image.")
    check_windows_path(file_path)
    if extension_jpg(file_path):
        cv2.imwrite(file_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
    elif extension_tif(file_path):
        if img.ndim == 3 and img.shape[2] == 4:
            # Write with ExtraSamples tag so Affinity/Photoshop recognise the alpha channel.
            # Pyramid stacking un-premultiplies before calling write_img, so alpha is straight.
            tifffile.imwrite(file_path, img, photometric='rgb', compression='lzw',
                             extrasamples=['UNASSALPHA'])
        else:
            cv2.imwrite(file_path, img, [int(cv2.IMWRITE_TIFF_COMPRESSION), 1])
    elif extension_png(file_path):
        cv2.imwrite(file_path, img, [
            int(cv2.IMWRITE_PNG_COMPRESSION), 9,
            int(cv2.IMWRITE_PNG_STRATEGY), cv2.IMWRITE_PNG_STRATEGY_HUFFMAN_ONLY
        ])
    else:
        raise RuntimeError(f"Invalid extension for file: {file_path}")


def img_8bit(img):
    return (img >> 8).astype(np.uint8) if img.dtype == np.uint16 else img


def has_alpha(img):
    return img is not None and img.ndim == 3 and img.shape[2] == 4


def split_alpha(img):
    """Return (color, alpha) for a 4-channel image, or (img, None) otherwise."""
    if has_alpha(img):
        return img[..., :3], img[..., 3]
    return img, None


def merge_alpha(color, alpha):
    """Re-attach an alpha channel; alpha may be (h, w) or (h, w, 1)."""
    if alpha is None:
        return color
    if alpha.ndim == 2:
        alpha = alpha[..., np.newaxis]
    return np.concatenate([color[..., :3], alpha.astype(color.dtype)], axis=2)


def drop_alpha(img):
    return img[..., :3] if has_alpha(img) else img


def img_bw_8bit(img):
    img = img_8bit(img)
    if len(img.shape) == 3:
        return cv2.cvtColor(drop_alpha(img), cv2.COLOR_BGR2GRAY)
    if len(img.shape) == 2:
        return img
    raise ValueError(f"Unsupported image format: {img.shape}")


def img_bw(img):
    return cv2.cvtColor(drop_alpha(img), cv2.COLOR_BGR2GRAY)


def get_first_image_file(filenames):
    if len(filenames) == 0:
        raise ValueError("No valid image files found in the selected path")
    first_img_file = None
    for filename in filenames:
        if os.path.isfile(filename) and extension_supported_input(filename):
            first_img_file = filename
            break
    if first_img_file is None:
        paths = ", ".join(filenames)
        raise ValueError(f"No image files found in paths: {paths}")
    return first_img_file


def get_img_metadata(img):
    if img is None:
        return None, None
    return img.shape[:2], img.dtype


def validate_image(img, expected_shape=None, expected_dtype=None):
    if img is None:
        raise RuntimeError("Image is None")
    shape, dtype = get_img_metadata(img)
    if expected_shape and shape[:2] != expected_shape[:2]:
        raise ShapeError(expected_shape, shape)
    if expected_dtype and dtype != expected_dtype:
        raise BitDepthError(expected_dtype, dtype)
    return img


def read_and_validate_img(filename, expected_shape=None, expected_dtype=None):
    return validate_image(read_img(filename), expected_shape, expected_dtype)


def img_subsample(img, subsample, fast=True):
    if fast:
        img_sub = img[::subsample, ::subsample]
    else:
        img_sub = cv2.resize(img, (0, 0),
                             fx=1 / subsample, fy=1 / subsample,
                             interpolation=cv2.INTER_AREA)
    return img_sub


def bgr_to_hsv(bgr_img):
    if bgr_img.dtype == np.uint8:
        return cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
    if len(bgr_img.shape) == 2:
        bgr_img = cv2.merge([bgr_img, bgr_img, bgr_img])
    bgr_normalized = bgr_img.astype(np.float32) / 65535.0
    b, g, r = cv2.split(bgr_normalized)
    v = np.max(bgr_normalized, axis=2)
    m = np.min(bgr_normalized, axis=2)
    delta = v - m
    s = np.zeros_like(v)
    nonzero_delta = delta != 0
    s[nonzero_delta] = delta[nonzero_delta] / v[nonzero_delta]
    h = np.zeros_like(v)
    r_is_max = (v == r) & nonzero_delta
    h[r_is_max] = (60 * (g[r_is_max] - b[r_is_max]) / delta[r_is_max]) % 360
    g_is_max = (v == g) & nonzero_delta
    h[g_is_max] = (60 * (b[g_is_max] - r[g_is_max]) / delta[g_is_max] + 120) % 360
    b_is_max = (v == b) & nonzero_delta
    h[b_is_max] = (60 * (r[b_is_max] - g[b_is_max]) / delta[b_is_max] + 240) % 360
    h[h < 0] += 360
    h_16bit = (h / 360 * 65535).astype(np.uint16)
    s_16bit = (s * 65535).astype(np.uint16)
    v_16bit = (v * 65535).astype(np.uint16)
    return cv2.merge([h_16bit, s_16bit, v_16bit])


def hsv_to_bgr(hsv_img):
    if hsv_img.dtype == np.uint8:
        return cv2.cvtColor(hsv_img, cv2.COLOR_HSV2BGR)
    hsv_float = hsv_img.astype(np.float32) / 65535.0
    h, s, v = hsv_float[..., 0] * 360, hsv_float[..., 1], hsv_float[..., 2]
    c = v * s
    x = c * (1 - np.abs((h / 60) % 2 - 1))
    m = v - c
    r = np.zeros_like(h, dtype=np.float32)
    g = np.zeros_like(h, dtype=np.float32)
    b = np.zeros_like(h, dtype=np.float32)
    mask = (h >= 0) & (h < 60)
    r[mask], g[mask], b[mask] = c[mask], x[mask], 0
    mask = (h >= 60) & (h < 120)
    r[mask], g[mask], b[mask] = x[mask], c[mask], 0
    mask = (h >= 120) & (h < 180)
    r[mask], g[mask], b[mask] = 0, c[mask], x[mask]
    mask = (h >= 180) & (h < 240)
    r[mask], g[mask], b[mask] = 0, x[mask], c[mask]
    mask = (h >= 240) & (h < 300)
    r[mask], g[mask], b[mask] = x[mask], 0, c[mask]
    mask = (h >= 300) & (h < 360)
    r[mask], g[mask], b[mask] = c[mask], 0, x[mask]
    r = np.clip((r + m) * 65535, 0, 65535).astype(np.uint16)
    g = np.clip((g + m) * 65535, 0, 65535).astype(np.uint16)
    b = np.clip((b + m) * 65535, 0, 65535).astype(np.uint16)
    return cv2.merge([b, g, r])


def bgr_to_hls(bgr_img):
    if bgr_img.dtype == np.uint8:
        return cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HLS)
    bgr_float = bgr_img.astype(np.float32) / 65535.0
    b, g, r = bgr_float[..., 0], bgr_float[..., 1], bgr_float[..., 2]
    v_max = np.maximum(np.maximum(r, g), b)
    v_min = np.minimum(np.minimum(r, g), b)
    delta = v_max - v_min
    l = (v_max + v_min) / 2.0  # noqa
    s = np.zeros_like(l)
    mask = delta > 0
    l_lt_half = l < 0.5
    denom = np.where(l_lt_half, v_max + v_min, 2.0 - v_max - v_min)
    s[mask] = delta[mask] / denom[mask]
    s = np.clip(s, 0, 1)
    h = np.zeros_like(l)
    r_is_max = (v_max == r) & mask
    g_is_max = (v_max == g) & mask
    b_is_max = (v_max == b) & mask
    h[r_is_max] = (60 * (g[r_is_max] - b[r_is_max]) / delta[r_is_max]) % 360
    h[g_is_max] = (60 * (b[g_is_max] - r[g_is_max]) / delta[g_is_max] + 120) % 360
    h[b_is_max] = (60 * (r[b_is_max] - g[b_is_max]) / delta[b_is_max] + 240) % 360
    h_16bit = (h * 65535 / 360).astype(np.uint16)
    l_16bit = (l * 65535).astype(np.uint16)
    s_16bit = (s * 65535).astype(np.uint16)
    return cv2.merge([h_16bit, l_16bit, s_16bit])


def hls_to_bgr(hls_img):
    if hls_img.dtype == np.uint8:
        return cv2.cvtColor(hls_img, cv2.COLOR_HLS2BGR)
    hls_float = hls_img.astype(np.float32) / 65535.0
    h = hls_float[..., 0] * 360.0
    l = hls_float[..., 1]  # noqa
    s = hls_float[..., 2]
    c = (1 - np.abs(2 * l - 1)) * s
    x = c * (1 - np.abs(np.mod(h / 60.0, 2) - 1))
    m = l - c / 2.0
    r = np.zeros_like(h)
    g = np.zeros_like(h)
    b = np.zeros_like(h)
    mask = (h >= 0) & (h < 60)
    r[mask], g[mask], b[mask] = c[mask], x[mask], 0
    mask = (h >= 60) & (h < 120)
    r[mask], g[mask], b[mask] = x[mask], c[mask], 0
    mask = (h >= 120) & (h < 180)
    r[mask], g[mask], b[mask] = 0, c[mask], x[mask]
    mask = (h >= 180) & (h < 240)
    r[mask], g[mask], b[mask] = 0, x[mask], c[mask]
    mask = (h >= 240) & (h < 300)
    r[mask], g[mask], b[mask] = x[mask], 0, c[mask]
    mask = (h >= 300) & (h < 360)
    r[mask], g[mask], b[mask] = c[mask], 0, x[mask]
    r += m
    g += m
    b += m
    r = np.clip(r * 65535, 0, 65535).astype(np.uint16)
    g = np.clip(g * 65535, 0, 65535).astype(np.uint16)
    b = np.clip(b * 65535, 0, 65535).astype(np.uint16)
    return cv2.merge([b, g, r])


def bgr_to_lab(bgr_img):
    if bgr_img.dtype == np.uint8:
        return cv2.cvtColor(bgr_img, cv2.COLOR_BGR2LAB)
    if len(bgr_img.shape) == 2:
        bgr_img = cv2.merge([bgr_img, bgr_img, bgr_img])
    bgr_float = bgr_img.astype(np.float32) / 65535.0
    B, G, R = bgr_float[..., 0], bgr_float[..., 1], bgr_float[..., 2]

    def inv_compand(c):
        result = np.empty_like(c)
        mask = c <= 0.04045
        result[mask] = c[mask] / 12.92
        not_mask = ~mask
        if np.any(not_mask):
            result[not_mask] = ((c[not_mask] + 0.055) / 1.055) ** 2.4
        return result

    R_lin, G_lin, B_lin = inv_compand(R), inv_compand(G), inv_compand(B)
    X = 0.412453 * R_lin + 0.357580 * G_lin + 0.180423 * B_lin
    Y = 0.212671 * R_lin + 0.715160 * G_lin + 0.072169 * B_lin
    Z = 0.019334 * R_lin + 0.119193 * G_lin + 0.950227 * B_lin
    X /= 0.950456
    Z /= 1.088754

    def f_xyz_to_lab(t):
        delta = 6.0 / 29.0
        delta_cubed = delta ** 3
        result = np.empty_like(t)
        mask = t > delta_cubed
        result[mask] = t[mask] ** (1.0 / 3.0)
        not_mask = ~mask
        if np.any(not_mask):
            result[not_mask] = t[not_mask] / (3 * delta * delta) + 4.0 / 29.0
        return result

    fY = f_xyz_to_lab(Y)
    L = 116.0 * fY - 16.0
    fX = f_xyz_to_lab(X)
    fZ = f_xyz_to_lab(Z)
    a = 500.0 * (fX - fY)
    b = 200.0 * (fY - fZ)
    L_scaled = np.clip(L * 652.80, 0, 65280).astype(np.uint16)
    a_scaled = np.clip((a + 128.0) * 256.0, 0, 65535).astype(np.uint16)
    b_scaled = np.clip((b + 128.0) * 256.0, 0, 65535).astype(np.uint16)
    return np.stack([L_scaled, a_scaled, b_scaled], axis=-1)


def lab_to_bgr(lab_img):
    if lab_img.dtype == np.uint8:
        return cv2.cvtColor(lab_img, cv2.COLOR_LAB2BGR)
    if len(lab_img.shape) == 2:
        lab_img = cv2.merge([lab_img, lab_img, lab_img])
    L = lab_img[..., 0].astype(np.float32) / 652.80
    a = lab_img[..., 1].astype(np.float32) / 256.0 - 128.0
    b = lab_img[..., 2].astype(np.float32) / 256.0 - 128.0
    fY = (L + 16.0) / 116.0
    Y = np.empty_like(fY)
    delta = 6.0 / 29.0
    mask = fY > delta
    Y[mask] = fY[mask] ** 3
    not_mask = ~mask
    if np.any(not_mask):
        Y[not_mask] = 3 * delta * delta * (fY[not_mask] - 4.0 / 29.0)
    fX = a / 500.0 + fY
    fZ = fY - b / 200.0
    X = np.empty_like(fX)
    Z = np.empty_like(fZ)
    mask_x = fX > delta
    X[mask_x] = fX[mask_x] ** 3
    not_mask_x = ~mask_x
    if np.any(not_mask_x):
        X[not_mask_x] = 3 * delta * delta * (fX[not_mask_x] - 4.0 / 29.0)
    mask_z = fZ > delta
    Z[mask_z] = fZ[mask_z] ** 3
    not_mask_z = ~mask_z
    if np.any(not_mask_z):
        Z[not_mask_z] = 3 * delta * delta * (fZ[not_mask_z] - 4.0 / 29.0)
    X *= 0.950456
    Z *= 1.088754
    R_lin = 3.240479 * X - 1.537150 * Y - 0.498535 * Z
    G_lin = -0.969256 * X + 1.875992 * Y + 0.041556 * Z
    B_lin = 0.055648 * X - 0.204043 * Y + 1.057311 * Z
    R_lin = np.clip(R_lin, 0, 1)
    G_lin = np.clip(G_lin, 0, 1)
    B_lin = np.clip(B_lin, 0, 1)

    def compand(c):
        result = np.empty_like(c)
        mask = c <= 0.0031308
        result[mask] = 12.92 * c[mask]
        not_mask = ~mask
        if np.any(not_mask):
            result[not_mask] = 1.055 * (c[not_mask] ** (1 / 2.4)) - 0.055
        return result

    R = compand(R_lin)
    G = compand(G_lin)
    B = compand(B_lin)
    bgr_float = np.stack([B, G, R], axis=-1)
    bgr_16bit = np.clip(bgr_float * 65535.0, 0, 65535).astype(np.uint16)
    return bgr_16bit
