"""Class-gated Hungarian matching.

cost(r, l) = alpha * (1 - IoU) + beta * (centroid_distance / sqrt(2))
computed in normalised [0,1] image coordinates (so images of different resolution are
comparable, assuming a similar viewpoint or an applied alignment). Pairs of different class,
or with cost > max_match_cost, are gated out and can never be assigned.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment

from config import Settings
from .geometry import BBox, UNIT_DIAGONAL, area, centroid_distance, iou, normalize_box, validate_bbox
from .schemas import Detection

BIG = 1e6


@dataclass
class Match:
    ref_id: str
    later_id: str
    class_name: str
    cost: float
    iou: float
    norm_distance: float
    area_ratio: float  # later box area / reference box area (normalised frame)
    ambiguous: bool
    ambiguity_detail: str | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MatchResult:
    matches: list[Match]
    unmatched_reference: list[str]
    unmatched_later: list[str]


def pair_cost(a_n: BBox, b_n: BBox, alpha: float, beta: float) -> tuple[float, float, float]:
    i = iou(a_n, b_n)
    d = centroid_distance(a_n, b_n) / UNIT_DIAGONAL
    return alpha * (1.0 - i) + beta * d, i, d


def match_detections(reference: list[Detection], later: list[Detection], settings: Settings,
                     ref_boxes_in_later: dict[str, BBox | None] | None = None) -> MatchResult:
    """``ref_boxes_in_later`` optionally maps reference ids to boxes already in the later image's
    pixel frame (after alignment); ``None`` excludes that reference detection from matching."""
    for d in list(reference) + list(later):
        validate_bbox(d.bbox, d.image_width, d.image_height)

    ref_n: dict[str, BBox] = {}
    for r in reference:
        if ref_boxes_in_later is not None and r.id in ref_boxes_in_later:
            b = ref_boxes_in_later[r.id]
            if b is None:
                continue
            ref_n[r.id] = normalize_box(b, later[0].image_width, later[0].image_height) if later else None
        else:
            ref_n[r.id] = normalize_box(r.bbox, r.image_width, r.image_height)
    later_n = {l.id: normalize_box(l.bbox, l.image_width, l.image_height) for l in later}

    eligible = [r for r in reference if r.id in ref_n and ref_n[r.id] is not None]
    if not eligible or not later:
        return MatchResult([], [r.id for r in reference], [l.id for l in later])

    n, m = len(eligible), len(later)
    raw = np.full((n, m), BIG)
    iou_m = np.zeros((n, m))
    dist_m = np.zeros((n, m))
    for i, r in enumerate(eligible):
        for j, l in enumerate(later):
            if r.class_name != l.class_name:
                continue
            c, io_, d = pair_cost(ref_n[r.id], later_n[l.id], settings.match_alpha, settings.match_beta)
            raw[i, j], iou_m[i, j], dist_m[i, j] = c, io_, d
    gated = np.where(raw <= settings.max_match_cost, raw, BIG)
    rows, cols = linear_sum_assignment(gated)

    matches: list[Match] = []
    used_ref, used_later = set(), set()
    for i, j in zip(rows, cols):
        if gated[i, j] >= BIG:
            continue  # never force a match
        r, l = eligible[i], later[j]
        notes = []
        for j2 in range(m):
            if j2 != j and raw[i, j2] <= settings.max_match_cost and raw[i, j2] - raw[i, j] <= settings.ambiguity_margin:
                notes.append(f"later detection {later[j2].id} is a near-equal candidate for {r.id}")
        for i2 in range(n):
            if i2 != i and raw[i2, j] <= settings.max_match_cost and raw[i2, j] - raw[i, j] <= settings.ambiguity_margin:
                notes.append(f"reference detection {eligible[i2].id} is a near-equal candidate for {l.id}")
        a_ref, a_later = area(ref_n[r.id]), area(later_n[l.id])
        matches.append(Match(r.id, l.id, r.class_name, float(raw[i, j]), float(iou_m[i, j]), float(dist_m[i, j]),
                             float(a_later / a_ref) if a_ref > 0 else float("inf"), bool(notes),
                             "; ".join(notes) or None))
        used_ref.add(r.id)
        used_later.add(l.id)
    return MatchResult(matches,
                       [r.id for r in reference if r.id not in used_ref],
                       [l.id for l in later if l.id not in used_later])
