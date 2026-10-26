"""Rule-based, evidence-based abstention. NOT Bayesian, NOT calibrated: each rule is a
transparent threshold test, and any triggered rule marks the finding 'uncertain'."""
from __future__ import annotations

from config import Settings
from .geometry import area, intersection_area
from .object_matching import Match
from .schemas import Detection


def _reason(code: str, detail: str) -> dict:
    return {"code": code, "detail": detail}


def _near_boundary(d: Detection, frac: float) -> bool:
    mx, my = frac * d.image_width, frac * d.image_height
    x1, y1, x2, y2 = d.bbox
    return x1 <= mx or y1 <= my or x2 >= d.image_width - mx or y2 >= d.image_height - my


def _overlapped_by(d: Detection, others: list[Detection], thr: float) -> Detection | None:
    a = area(d.bbox)
    if a <= 0:
        return None
    for o in others:
        if o.id != d.id and intersection_area(d.bbox, o.bbox) / a >= thr:
            return o
    return None


def assess_finding(change_type: str, reference: Detection | None, later: Detection | None, match: Match | None,
                   reference_all: list[Detection], later_all: list[Detection], settings: Settings,
                   alignment: dict | None = None, projected_outside: bool = False,
                   displacement: float | None = None) -> list[dict]:
    reasons: list[dict] = []
    involved = [("reference", reference, reference_all), ("later", later, later_all)]
    for role, det, pool in involved:
        if det is None:
            continue
        if det.confidence < settings.low_confidence_threshold:
            reasons.append(_reason("low_detector_confidence",
                                   f"{role} detector score {det.confidence:.2f} < {settings.low_confidence_threshold:.2f}"))
        if _near_boundary(det, settings.boundary_margin_frac):
            reasons.append(_reason("near_image_boundary", f"{role} box touches/near the image edge (possibly truncated)"))
        other = _overlapped_by(det, pool, settings.occlusion_overlap_fraction)
        if other is not None:
            reasons.append(_reason("possible_overlap_or_occlusion",
                                   f"{role} box is ≥{settings.occlusion_overlap_fraction:.0%} covered by a detected {other.class_name}"))
    if match is not None:
        if match.cost > settings.weak_match_cost:
            reasons.append(_reason("weak_association", f"match cost {match.cost:.2f} > {settings.weak_match_cost:.2f} (little box overlap)"))
        if match.ambiguous:
            reasons.append(_reason("ambiguous_match", match.ambiguity_detail or "near-equal alternative candidate"))
        r = settings.area_ratio_limit
        if match.area_ratio > r or match.area_ratio < 1.0 / r:
            reasons.append(_reason("bbox_area_inconsistency", f"box area ratio later/reference = {match.area_ratio:.2f}"))
        if displacement is not None and displacement > settings.large_displacement_threshold:
            reasons.append(_reason("large_displacement", f"displacement {displacement:.2f} exceeds {settings.large_displacement_threshold:.2f}"))
        if (change_type == "possibly_relocated" and displacement is not None
                and displacement <= settings.relocated_threshold + 1e-12 and displacement > settings.unchanged_tolerance):
            reasons.append(_reason("borderline_displacement", "displacement lies between the unchanged and relocation thresholds"))
    if projected_outside:
        reasons.append(_reason("projected_outside_later_frame", "aligned reference box falls outside the later image"))
    if alignment and alignment.get("attempted") and change_type != "unchanged":
        if not alignment.get("applied"):
            reasons.append(_reason("alignment_unavailable", f"alignment attempted but not applied: {alignment.get('reason')}"))
        elif alignment.get("inlier_ratio") is not None and alignment["inlier_ratio"] < settings.alignment_good_inlier_ratio:
            reasons.append(_reason("weak_alignment", f"RANSAC inlier ratio {alignment['inlier_ratio']:.2f} < {settings.alignment_good_inlier_ratio:.2f}"))
    return reasons
