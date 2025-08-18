import cv2
import sys
import numpy as np
import matplotlib
if "pytest" in sys.modules:
    matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shinestacker.config.constants import constants
from shinestacker.algorithms.align import align_images
np.random.seed(123456)


def create_test_image(size=(512, 512), color=False):
    if color:
        img = np.zeros((*size, 3), dtype=np.uint8)
        white = (255, 255, 255)
    else:
        img = np.zeros(size, dtype=np.uint8)
        white = 255
    cv2.rectangle(img, (50, 50), (150, 150), white, 2)
    cv2.circle(img, (400, 150), 60, white, 2)
    cv2.line(img, (200, 400), (300, 300), white, 2)
    cv2.line(img, (200, 300), (300, 400), white, 2)
    noise = np.random.normal(0, 10, img.shape).astype(np.uint8)
    return cv2.add(img, noise)


def apply_transform(img, angle=15, tx=30, ty=20):
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    M[0, 2] += tx
    M[1, 2] += ty
    return cv2.warpAffine(img, M, (w, h)), M


def ensure_3channel(img):
    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 1:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img


def compare_transformations(M_true, M_aligned):
    print("\nTrue transformation matrix:")
    print(M_true)
    print("\nRecovered transformation matrix:")
    print(M_aligned)
    angle_true = np.degrees(np.arctan2(M_true[1, 0], M_true[0, 0]))
    angle_aligned = np.degrees(np.arctan2(M_aligned[1, 0], M_aligned[0, 0]))
    angle_diff = abs(angle_true - angle_aligned)
    tx_diff = abs(M_true[0, 2] - M_aligned[0, 2])
    ty_diff = abs(M_true[1, 2] - M_aligned[1, 2])
    print(f"\nRotation difference: {angle_diff:.4f} degrees")
    print(f"Translation X difference: {tx_diff:.4f} pixels")
    print(f"Translation Y difference: {ty_diff:.4f} pixels")
    scale_true = np.sqrt(M_true[0, 0]**2 + M_true[1, 0]**2)
    scale_aligned = np.sqrt(M_aligned[0, 0]**2 + M_aligned[1, 0]**2)
    scale_diff = scale_true - scale_aligned
    print(f"Scale difference: {scale_diff:.6f}")
    assert abs(angle_diff) < 0.005
    assert abs(tx_diff) < 0.2
    assert abs(ty_diff) < 0.2
    assert abs(scale_diff) < 0.0001


def compare_alignment(color_test=False):
    original = create_test_image(color=color_test)
    transformed, M_true = apply_transform(original)
    original_bgr = ensure_3channel(original)
    transformed_bgr = ensure_3channel(transformed)
    try:
        n_matches, M_recovered, aligned = align_images(
            transformed_bgr, original_bgr,
            feature_config={
                'detector': constants.SIFT_DETECTOR,
                'descriptor': constants.SIFT_DESCRIPTOR
            },
            matching_config={
                'match_method': constants.MATCHING_KNN
            },
            alignment_config={
                'transform': constants.ALIGN_RIGID,
                'subsample': 1
            }
        )
    except Exception as e:
        print(f"Alignment failed: {e}")
        return
    compare_transformations(M_true, M_recovered)
    display_img = aligned.copy()
    if not color_test:
        display_img = cv2.cvtColor(display_img, cv2.COLOR_BGR2GRAY)
    titles = ['Original', 'Transformed', 'Aligned']
    images = [original, transformed, display_img]
    if "pytest" not in sys.modules:
        plt.figure(figsize=(15, 5))
        for i, (title, img) in enumerate(zip(titles, images)):
            plt.subplot(1, 3, i + 1)
            if len(img.shape) == 2:
                plt.imshow(img, cmap='gray')
            else:
                plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            plt.title(title)
        plt.show()


def test_alignment_bw():
    compare_alignment(False)


def test_alignment_color():
    compare_alignment(True)


if __name__ == "__main__":
    print("=== TEST GRAYSCALE ===")
    test_alignment_bw()
    print("\n=== TEST COLOR ===")
    test_alignment_color()
