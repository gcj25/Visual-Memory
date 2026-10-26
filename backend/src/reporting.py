"""Structured JSON report + CSV export."""
from __future__ import annotations

import csv
import io
import json
import os
import re
from pathlib import Path

REPORT_ID = re.compile(r"^rep_[0-9a-f]{12}$")

LIMITATIONS = [
    "Detector confidence is a model score, not the probability that an object is correctly identified.",
    "COCO models may label a monitor as 'tv'; desks and specialised laboratory equipment may not be detected.",
    "A detection match between images is not proof that the same physical object appears in both.",
    "'not_observed' means the detector produced no match; it is not evidence of removal, theft or disappearance.",
    "Uncertainty handling is transparent rule-based abstention; it is not Bayesian and not statistically calibrated.",
    "Matching assumes a similar viewpoint, or a successfully applied ORB/RANSAC alignment.",
]

CSV_FIELDS = ["finding_id", "class_name", "change_type", "status", "reference_confidence", "later_confidence",
              "displacement_norm", "match_cost", "iou", "uncertainty_reasons", "explanation", "reference_bbox", "later_bbox"]


def save_report(reports_dir: Path, report: dict) -> Path:
    path = reports_dir / f"{report['report_id']}.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report, indent=2))
    os.replace(tmp, path)
    return path


def load_report(reports_dir: Path, report_id: str) -> dict | None:
    if not REPORT_ID.match(report_id):
        return None
    p = reports_dir / f"{report_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def list_reports(reports_dir: Path) -> list[dict]:
    out = []
    for p in sorted(reports_dir.glob("rep_*.json")):
        try:
            r = json.loads(p.read_text())
            out.append({"report_id": r["report_id"], "created_at": r.get("created_at"),
                        "reference_image": r.get("reference_image", {}).get("filename"),
                        "later_image": r.get("later_image", {}).get("filename"), "summary": r.get("summary")})
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    return sorted(out, key=lambda r: r.get("created_at") or "", reverse=True)


def findings_csv(report: dict) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
    w.writeheader()
    for f in report.get("findings", []):
        aq = f.get("association_quality") or {}
        w.writerow({
            "finding_id": f["finding_id"], "class_name": f["class_name"], "change_type": f["change_type"],
            "status": f["status"], "reference_confidence": f["detector_confidence"].get("reference"),
            "later_confidence": f["detector_confidence"].get("later"), "displacement_norm": f.get("displacement_norm"),
            "match_cost": aq.get("match_cost"), "iou": aq.get("iou"),
            "uncertainty_reasons": "; ".join(r["code"] for r in f.get("uncertainty_reasons", [])),
            "explanation": f["explanation"],
            "reference_bbox": (f.get("reference_detection") or {}).get("bbox"),
            "later_bbox": (f.get("later_detection") or {}).get("bbox")})
    return buf.getvalue()
