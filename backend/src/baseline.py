"""Classic pixel-difference baseline (grayscale absdiff + threshold + contours)."""
from __future__ import annotations

import cv2
import numpy as np

from config import Settings

EXPLANATION = ("Pixel differencing responds to any intensity change: lighting variation, shadows, camera movement, "
               "background changes and genuine object movement alike. It has no notion of objects.")


def compute_baseline(ref_bgr: np.ndarray, later_bgr: np.ndarray, settings: Settings) -> dict:
    """Returns {'available', 'warnings', ..., 'mask', 'overlay'} (arrays are not JSON; the caller saves them)."""
    out: dict = {"available": False, "warnings": [], "explanation": EXPLANATION}
    rh, rw = ref_bgr.shape[:2]
    lh, lw = later_bgr.shape[:2]
    later = later_bgr
    if (rw, rh) != (lw, lh):
        if abs(rw / rh - lw / lh) > settings.baseline_aspect_tolerance:
            out["warnings"].append(
                f"Image sizes {rw}x{rh} and {lw}x{lh} have different aspect ratios; resizing would distort geometry, "
                f"so the pixel-difference baseline was not computed.")
            return out
        later = cv2.resize(later_bgr, (rw, rh), interpolation=cv2.INTER_AREA)
        out["warnings"].append(f"Later image uniformly resized from {lw}x{lh} to {rw}x{rh} (same aspect ratio) to match the reference.")
    out["warnings"].append("Viewpoint, exposure or camera differences can make this comparison unreliable.")
    k = settings.baseline_blur_kernel
    a = cv2.GaussianBlur(cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2GRAY), (k, k), 0)
    b = cv2.GaussianBlur(cv2.cvtColor(later, cv2.COLOR_BGR2GRAY), (k, k), 0)
    diff = cv2.absdiff(a, b)
    _, mask = cv2.threshold(diff, settings.baseline_threshold, 255, cv2.THRESH_BINARY)
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (settings.baseline_morph_kernel,) * 2)
    mask = cv2.morphologyEx(cv2.morphologyEx(mask, cv2.MORPH_OPEN, ker), cv2.MORPH_CLOSE, ker)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = settings.baseline_min_region_frac * rw * rh
    regions = []
    overlay = later.copy()
    for c in contours:
        if cv2.contourArea(c) < min_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        regions.append({"bbox": [x, y, x + w, y + h], "area_px": int(cv2.contourArea(c))})
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 0, 255), 2)
    out.update(available=True, mask=mask, overlay=overlay, region_count=len(regions), regions=regions[:200],
               changed_pixel_fraction=round(float((mask > 0).mean()), 5), image_size=[rw, rh],
               parameters={"threshold": settings.baseline_threshold, "blur_kernel": k,
                           "morph_kernel": settings.baseline_morph_kernel, "min_region_frac": settings.baseline_min_region_frac})
    return out
