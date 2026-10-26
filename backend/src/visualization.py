"""Annotated images (boxes coloured by change type) and baseline outputs."""
from __future__ import annotations

import cv2
import numpy as np

from .spatial_analysis import zone_polygon_px

COLORS = {"unchanged": (80, 175, 76), "possibly_relocated": (0, 165, 255), "newly_observed": (255, 144, 30),
          "not_observed": (60, 60, 230), None: (180, 180, 180)}


def _shrink(img: np.ndarray, max_side: int) -> np.ndarray:
    s = min(1.0, max_side / max(img.shape[:2]))
    return img if s >= 1.0 else cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)


def annotate(img: np.ndarray, detections, change_by_id: dict[str, tuple[str, str]], zones=None,
             max_side: int = 1280) -> np.ndarray:
    out = img.copy()
    scale = max(1.0, max(out.shape[:2]) / 900)
    th = max(2, int(round(2 * scale)))
    if zones:
        layer = out.copy()
        for z in zones:
            if not z["enabled"]:
                continue
            pts = np.array(zone_polygon_px(z, out.shape[1], out.shape[0]), np.int32)
            cv2.fillPoly(layer, [pts], (200, 160, 60))
            cv2.polylines(out, [pts], True, (200, 160, 60), th)
        out = cv2.addWeighted(layer, 0.18, out, 0.82, 0)
    for d in detections:
        ctype, status = change_by_id.get(d.id, (None, None))
        col = COLORS.get(ctype, COLORS[None])
        x1, y1, x2, y2 = (int(round(v)) for v in d.bbox)
        cv2.rectangle(out, (x1, y1), (x2, y2), col, th)
        label = f"{d.class_name} {d.confidence:.2f}" + ("?" if status == "uncertain" else "")
        fs = 0.5 * scale
        (tw, tht), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, fs, 1)
        cv2.rectangle(out, (x1, max(0, y1 - tht - 6)), (x1 + tw + 4, max(tht + 6, y1)), col, -1)
        cv2.putText(out, label, (x1 + 2, max(tht + 2, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, fs, (255, 255, 255), 1, cv2.LINE_AA)
    return _shrink(out, max_side)


def save_image(path, img: np.ndarray, quality: int = 88) -> None:
    ext = str(path).rsplit(".", 1)[-1].lower()
    params = [cv2.IMWRITE_JPEG_QUALITY, quality] if ext in ("jpg", "jpeg") else []
    if not cv2.imwrite(str(path), img, params):
        raise OSError(f"could not write {path}")
