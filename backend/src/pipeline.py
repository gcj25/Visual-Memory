"""Orchestrates the full comparison. Independent of HTTP so it can be tested directly."""
from __future__ import annotations

import time
import uuid

from config import Paths, Settings
from . import baseline as baseline_mod
from . import reporting, spatial_analysis, visualization
from .change_detection import classify_changes, summarize
from .image_alignment import estimate_alignment, transform_box
from .image_io import LoadedImage
from .object_matching import match_detections
from .scene_memory import SceneMemory, now_iso


class Pipeline:
    def __init__(self, settings: Settings, detector, memory: SceneMemory, paths: Paths):
        self.settings, self.detector, self.memory, self.paths = settings, detector, memory, paths

    def compare(self, ref: LoadedImage, later: LoadedImage, settings: Settings | None = None,
                persist: bool = True, against_observation_id: str | None = None) -> dict:
        s = settings or self.settings
        t_all = time.perf_counter()
        timings: dict[str, float] = {}
        warnings: list[str] = []
        if ref.sha256 == later.sha256:
            warnings.append("Reference and later images are byte-identical.")

        t = time.perf_counter()
        ref_dets = self.detector.detect(ref.bgr, ref.image_id, ref.sha256, s.detector_conf)
        later_dets = self.detector.detect(later.bgr, later.image_id, later.sha256, s.detector_conf)
        timings["detection_s"] = round(time.perf_counter() - t, 3)
        if not ref_dets:
            warnings.append("No supported objects were detected in the reference image.")
        if not later_dets:
            warnings.append("No supported objects were detected in the later image.")

        t = time.perf_counter()
        alignment = {"attempted": False, "applied": False, "reason": "alignment disabled in configuration"}
        ref_boxes_in_later, outside = None, set()
        if s.enable_alignment:
            ares = estimate_alignment(ref.bgr, later.bgr, s)
            alignment = ares.to_dict()
            if ares.applied:
                ref_boxes_in_later = {}
                for d in ref_dets:
                    b = transform_box(d.bbox, ares.H, later.width, later.height)
                    ref_boxes_in_later[d.id] = b
                    if b is None:
                        outside.add(d.id)
            else:
                warnings.append(f"Image alignment not applied ({ares.reason}); geometry-dependent findings are marked uncertain.")
        timings["alignment_s"] = round(time.perf_counter() - t, 3)

        t = time.perf_counter()
        mr = match_detections(ref_dets, later_dets, s, ref_boxes_in_later)
        findings = classify_changes(ref_dets, later_dets, mr, s, alignment, outside)
        timings["matching_and_classification_s"] = round(time.perf_counter() - t, 3)

        by_ref, by_later = {}, {}
        for f in findings:
            if f.reference_detection:
                by_ref[f.reference_detection["id"]] = (f.change_type, f.status)
            if f.later_detection:
                by_later[f.later_detection["id"]] = (f.change_type, f.status)

        zones, zwarn = spatial_analysis.load_zones(self.paths.zones / "zones.json")
        warnings += zwarn
        sp_findings = (spatial_analysis.analyze(zones, ref_dets, "reference", {k: v[0] for k, v in by_ref.items()})
                       + spatial_analysis.analyze(zones, later_dets, "later", {k: v[0] for k, v in by_later.items()}))

        t = time.perf_counter()
        bl = baseline_mod.compute_baseline(ref.bgr, later.bgr, s)
        timings["baseline_s"] = round(time.perf_counter() - t, 3)

        report_id = f"rep_{uuid.uuid4().hex[:12]}"
        outputs = {}
        ann_ref = visualization.annotate(ref.bgr, ref_dets, by_ref, None, s.output_max_side)
        ann_later = visualization.annotate(later.bgr, later_dets, by_later, zones, s.output_max_side)
        for key, img, folder, ext in (("annotated_reference", ann_ref, self.paths.annotated, "jpg"),
                                      ("annotated_later", ann_later, self.paths.annotated, "jpg")):
            name = f"{report_id}_{key.split('_')[1]}.{ext}"
            visualization.save_image(folder / name, img)
            outputs[key] = f"/api/outputs/annotated/{name}"
        if bl.get("available"):
            visualization.save_image(self.paths.baseline / f"{report_id}_mask.png", bl.pop("mask"))
            visualization.save_image(self.paths.baseline / f"{report_id}_overlay.jpg",
                                     visualization._shrink(bl.pop("overlay"), s.output_max_side))
            outputs["baseline_mask"] = f"/api/outputs/baseline/{report_id}_mask.png"
            outputs["baseline_overlay"] = f"/api/outputs/baseline/{report_id}_overlay.jpg"
        timings["total_s"] = round(time.perf_counter() - t_all, 3)

        report = {
            "report_id": report_id, "created_at": now_iso(),
            "reference_image": ref.meta(), "later_image": later.meta(),
            "model": self.detector.info(),
            "configuration": s.to_dict(),
            "detections": {"reference": [d.to_dict() for d in ref_dets], "later": [d.to_dict() for d in later_dets]},
            "alignment": alignment,
            "summary": {**summarize(findings), "reference_detections": len(ref_dets), "later_detections": len(later_dets)},
            "findings": [f.to_dict() for f in findings],
            "spatial": {"zones": [{**z, "polygon": [list(p) for p in z["polygon"]]} for z in zones],
                        "findings": sp_findings,
                        "note": "Zones come from data/zones/zones.json. A 'potential_concern' means a configured geometric rule was met."},
            "baseline": bl,
            "outputs": outputs, "timings": timings, "warnings": warnings, "limitations": reporting.LIMITATIONS,
        }
        if persist:
            self._persist(ref, later, ref_dets, later_dets, report, against_observation_id)
            reporting.save_report(self.paths.reports, report)
        return report

    def _persist(self, ref, later, ref_dets, later_dets, report, against_id) -> None:
        model = report["model"].get("name")
        for role, img, dets in (("reference", ref, ref_dets), ("later", later, later_dets)):
            if role == "reference" and self.memory.has_image(img.image_id):
                continue
            meta = img.meta()
            meta["stored_file"] = self.memory.store_image(img)
            self.memory.save({"role": role, "image": meta, "model": model,
                              "detections": [d.to_dict() for d in dets],
                              "comparison": ({"report_id": report["report_id"], "reference_image_id": ref.image_id,
                                              "against_observation_id": against_id, "summary": report["summary"]}
                                             if role == "later" else None)})
