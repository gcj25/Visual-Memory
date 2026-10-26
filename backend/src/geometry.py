"""Bounding-box helpers. Convention: (x1, y1, x2, y2), x right, y down."""
from __future__ import annotations

import math

BBox = tuple[float, float, float, float]
UNIT_DIAGONAL = math.sqrt(2.0)


def validate_bbox(bbox, width: float | None = None, height: float | None = None, tol: float = 1.0) -> BBox:
    if bbox is None or len(bbox) != 4:
        raise ValueError("bounding box must contain exactly 4 values (x1, y1, x2, y2)")
    try:
        x1, y1, x2, y2 = (float(v) for v in bbox)
    except (TypeError, ValueError) as e:
        raise ValueError("bounding box values must be numeric") from e
    if not all(math.isfinite(v) for v in (x1, y1, x2, y2)):
        raise ValueError("bounding box contains non-finite values")
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"degenerate bounding box {(x1, y1, x2, y2)}: need x2 > x1 and y2 > y1")
    if width is not None and height is not None:
        if x1 < -tol or y1 < -tol or x2 > width + tol or y2 > height + tol:
            raise ValueError(f"bounding box {(x1, y1, x2, y2)} lies outside image {width}x{height}")
    return (x1, y1, x2, y2)


def area(b: BBox) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def intersection_area(a: BBox, b: BBox) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, w) * max(0.0, h)


def iou(a: BBox, b: BBox) -> float:
    inter = intersection_area(a, b)
    union = area(a) + area(b) - inter
    return inter / union if union > 0 else 0.0


def centroid(b: BBox) -> tuple[float, float]:
    return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)


def centroid_distance(a: BBox, b: BBox) -> float:
    (ax, ay), (bx, by) = centroid(a), centroid(b)
    return math.hypot(ax - bx, ay - by)


def normalize_box(b: BBox, width: float, height: float) -> BBox:
    return (b[0] / width, b[1] / height, b[2] / width, b[3] / height)


def clip_box(b: BBox, width: float, height: float) -> BBox | None:
    c = (max(0.0, b[0]), max(0.0, b[1]), min(float(width), b[2]), min(float(height), b[3]))
    return c if c[2] > c[0] and c[3] > c[1] else None
