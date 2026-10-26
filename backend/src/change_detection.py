"""Turn matching output into findings. Never asserts removal, theft or intent."""
from __future__ import annotations

from config import Settings
from .object_matching import MatchResult
from .schemas import Detection, Finding
from .uncertainty import assess_finding

CAVEATS = {
    "possibly_relocated": "A detection match is not identity verification; a different similar object could be responsible.",
    "newly_observed": "May be a new object, a previously occluded or missed object, or a false-positive detection.",
    "not_observed": ("Absence from detector output is not evidence of removal: the object may be occluded, "
                     "outside the frame, poorly lit, or missed by the detector."),
    "unchanged": "",
}


def classify_changes(reference: list[Detection], later: list[Detection], mr: MatchResult, settings: Settings,
                     alignment: dict | None = None, projected_outside_ids: set[str] | None = None) -> list[Finding]:
    ref_by = {d.id: d for d in reference}
    later_by = {d.id: d for d in later}
    projected_outside_ids = projected_outside_ids or set()
    findings: list[Finding] = []

    def add(ctype, r, l, match=None, expl="", evidence=None, displacement=None, outside=False):
        reasons = assess_finding(ctype, r, l, match, reference, later, settings, alignment, outside, displacement)
        cls = (r or l).class_name
        caveat = CAVEATS[ctype]
        findings.append(Finding(
            finding_id=f"f{len(findings) + 1:03d}", change_type=ctype,
            status="uncertain" if reasons else "supported", class_name=cls, explanation=expl,
            reference_detection=r.to_dict() if r else None, later_detection=l.to_dict() if l else None,
            displacement_norm=None if displacement is None else round(displacement, 4),
            area_ratio=None if match is None else round(match.area_ratio, 3),
            association_quality=None if match is None else {
                "match_cost": round(match.cost, 4), "iou": round(match.iou, 4),
                "normalized_centroid_distance": round(match.norm_distance, 4), "ambiguous": match.ambiguous},
            detector_confidence={"reference": None if r is None else round(r.confidence, 4),
                                 "later": None if l is None else round(l.confidence, 4)},
            evidence=evidence or [], uncertainty_reasons=reasons, caveats=[caveat] if caveat else []))

    for m in mr.matches:
        r, l = ref_by[m.ref_id], later_by[m.later_id]
        d = m.norm_distance
        ev = [f"matched {r.id} -> {l.id} (cost {m.cost:.3f}, IoU {m.iou:.3f})",
              f"normalized centroid displacement {d:.4f} (tolerance {settings.unchanged_tolerance}, relocation threshold {settings.relocated_threshold})"]
        if d <= settings.unchanged_tolerance:
            add("unchanged", r, l, m, f"The {m.class_name} stayed within the displacement tolerance.", ev, d)
        else:
            add("possibly_relocated", r, l, m,
                f"The {m.class_name} appears displaced by {d:.1%} of the image diagonal; it may be the same object moved, "
                f"or a different similar object.", ev, d)
    for rid in mr.unmatched_reference:
        r = ref_by[rid]
        outside = rid in projected_outside_ids
        add("not_observed", r, None, None,
            f"A {r.class_name} detected in the reference image has no compatible detection in the later image.",
            [f"no later {r.class_name} detection satisfied the match cost limit {settings.max_match_cost}"], None, outside)
    for lid in mr.unmatched_later:
        l = later_by[lid]
        add("newly_observed", None, l, None,
            f"A {l.class_name} detected in the later image has no compatible detection in the reference image.",
            [f"no reference {l.class_name} detection satisfied the match cost limit {settings.max_match_cost}"], None)
    return findings


def summarize(findings: list[Finding]) -> dict:
    out = {"total": len(findings), "uncertain": sum(f.status == "uncertain" for f in findings), "by_change_type": {}}
    for f in findings:
        out["by_change_type"][f.change_type] = out["by_change_type"].get(f.change_type, 0) + 1
    return out
