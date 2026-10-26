"""Configurable polygon zones + rule-based overlap evidence (Shapely). No hazard classifier."""
from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import Polygon, box as sbox

from .schemas import Detection


def load_zones(path: Path) -> tuple[list[dict], list[str]]:
    """Returns (valid zones, warnings). Missing/corrupt files yield an empty list plus a warning."""
    warnings: list[str] = []
    if not path.exists():
        return [], warnings
    try:
        raw = json.loads(path.read_text())
        items = raw["zones"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return [], [f"zones file unreadable ({type(e).__name__}); spatial analysis skipped"]
    zones = []
    for z in items:
        try:
            pts = [(float(x), float(y)) for x, y in z["polygon"]]
            if len(pts) < 3 or not Polygon(pts).is_valid:
                raise ValueError("polygon needs >= 3 points and must be simple")
            space = z.get("coordinate_space", "normalized")
            if space not in ("normalized", "pixel"):
                raise ValueError("coordinate_space must be 'normalized' or 'pixel'")
            rule = z.get("rule", {})
            zones.append({"id": str(z["id"]), "name": z.get("name", z["id"]), "description": z.get("description", ""),
                          "polygon": pts, "coordinate_space": space, "enabled": bool(z.get("enabled", True)),
                          "rule": {"type": "overlap_fraction", "min_overlap_fraction": float(rule.get("min_overlap_fraction", 0.2)),
                                   "classes": list(rule.get("classes", []))}})
        except (KeyError, ValueError, TypeError) as e:
            warnings.append(f"zone skipped ({e})")
    return zones, warnings


def zone_polygon_px(zone: dict, width: int, height: int) -> list[tuple[float, float]]:
    if zone["coordinate_space"] == "pixel":
        return zone["polygon"]
    return [(x * width, y * height) for x, y in zone["polygon"]]


def analyze(zones: list[dict], detections: list[Detection], image_role: str,
            change_by_detection: dict[str, str] | None = None) -> list[dict]:
    """Report a potential concern only when the zone's configured rule is met by geometry."""
    findings = []
    for z in zones:
        if not z["enabled"]:
            continue
        rule = z["rule"]
        for d in detections:
            if rule["classes"] and d.class_name not in rule["classes"]:
                continue
            poly = Polygon(zone_polygon_px(z, d.image_width, d.image_height))
            b = sbox(*d.bbox)
            inter = poly.intersection(b).area
            frac = inter / b.area if b.area > 0 else 0.0
            if frac >= rule["min_overlap_fraction"]:
                findings.append({
                    "zone_id": z["id"], "zone_name": z["name"], "image_role": image_role, "detection_id": d.id,
                    "class_name": d.class_name, "bbox": [round(v, 2) for v in d.bbox],
                    "overlap_area_px": round(inter, 1), "overlap_fraction_of_object": round(frac, 4),
                    "rule": f"{d.class_name} overlaps zone by >= {rule['min_overlap_fraction']:.0%} of its box"
                            + (f" (classes: {', '.join(rule['classes'])})" if rule["classes"] else ""),
                    "status": "potential_concern",
                    "change_type": (change_by_detection or {}).get(d.id),
                    "note": "A configured geometric rule was met; this does not establish that anything is hazardous."})
    return findings
