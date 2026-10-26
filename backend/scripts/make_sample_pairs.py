"""Create *edited* image pairs with known ground truth from one real photograph.

These are NOT independent real captures: the 'later' images are produced by copy/paste and
inpainting of the detected chair, so they test the pipeline against known edits only.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROJECT_DIR, load_settings  # noqa: E402
from src.detector import Detector  # noqa: E402

OUT = PROJECT_DIR / "data" / "sample_images"
img = cv2.imread(str(OUT / "chairs_original.jpg"))
h, w = img.shape[:2]
dets = Detector(load_settings()).detect(img, "orig", None, 0.25)
chairs = sorted([d for d in dets if d.class_name == "chair"], key=lambda d: -d.confidence)
assert chairs, "no chair detected in source image"
x1, y1, x2, y2 = (int(v) for v in chairs[0].bbox)
patch = img[y1:y2, x1:x2].copy()
mask = np.zeros((h, w), np.uint8)
pad = 6
mask[max(0, y1 - pad):y2 + pad, max(0, x1 - pad):x2 + pad] = 255
cleared = cv2.inpaint(img, mask, 7, cv2.INPAINT_TELEA)


def paste(base, dx, dy):
    out = base.copy()
    nx1, ny1 = min(max(0, x1 + dx), w - patch.shape[1]), min(max(0, y1 + dy), h - patch.shape[0])
    out[ny1:ny1 + patch.shape[0], nx1:nx1 + patch.shape[1]] = patch
    return out, (nx1, ny1)


PADC = 25  # context margin so the pasted chair is still recognisable to the detector
X1, Y1, X2, Y2 = max(0, x1 - PADC), max(0, y1 - PADC), min(w, x2 + PADC), min(h, y2 + PADC)
ctx = img[Y1:Y2, X1:X2]
dx = -int(0.18 * w)
center = ((X1 + X2) // 2 + dx, (Y1 + Y2) // 2)
moved = cv2.seamlessClone(ctx, cleared, 255 * np.ones(ctx.shape[:2], np.uint8), center, cv2.NORMAL_CLONE)
pos = center
cv2.imwrite(str(OUT / "edit_moved_chair.jpg"), moved)
cv2.imwrite(str(OUT / "edit_removed_chair.jpg"), cleared)
added = cv2.seamlessClone(ctx, img, 255 * np.ones(ctx.shape[:2], np.uint8), center, cv2.NORMAL_CLONE)
cv2.imwrite(str(OUT / "edit_added_chair.jpg"), added)
cv2.imwrite(str(OUT / "edit_identical_copy.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
print("source chair bbox", (x1, y1, x2, y2), "moved to", pos)
