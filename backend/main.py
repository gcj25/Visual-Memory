"""FastAPI application. Thin HTTP layer over the pipeline."""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from config import DEV_ORIGINS, Paths, Settings, load_settings
from src import reporting, spatial_analysis
from src.detector import Detector, DetectorUnavailable
from src.image_io import ImageValidationError, decode_upload
from src.pipeline import Pipeline
from src.scene_memory import SceneMemory

_FILE = re.compile(r"^[A-Za-z0-9_.-]+$")


def create_app(detector=None, settings: Settings | None = None, paths: Paths | None = None) -> FastAPI:
    settings = settings or load_settings()
    paths = (paths or Paths.default()).ensure()
    detector = detector or Detector(settings)
    memory = SceneMemory(paths.observations, paths.images)
    pipeline = Pipeline(settings, detector, memory, paths)

    app = FastAPI(title="Visual Memory API", version="1.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=DEV_ORIGINS, allow_methods=["GET", "POST"], allow_headers=["*"])
    app.state.detector, app.state.memory, app.state.pipeline, app.state.paths = detector, memory, pipeline, paths

    def need_detector() -> None:
        try:
            detector.load()
        except DetectorUnavailable as e:
            raise HTTPException(503, f"Detector unavailable: {e}") from e

    def read_upload(f: UploadFile | None, label: str):
        if f is None:
            raise HTTPException(422, f"Missing required file field '{label}'")
        data = f.file.read(settings.max_upload_bytes + 1)
        try:
            return decode_upload(data, f.filename or label, settings)
        except ImageValidationError as e:
            raise HTTPException(e.status_code, str(e)) from e

    def request_settings(detector_conf: float | None, enable_alignment: bool | None) -> Settings:
        kw = {}
        if detector_conf is not None:
            kw["detector_conf"] = detector_conf
        if enable_alignment is not None:
            kw["enable_alignment"] = enable_alignment
        try:
            return settings.with_overrides(**kw) if kw else settings
        except ValueError as e:
            raise HTTPException(422, str(e)) from e

    @app.get("/health")
    def health():
        return {"status": "ok", "detector": detector.status(), "observations_dir": "data/observations"}

    @app.get("/api/config")
    def get_config():
        return {"settings": settings.to_dict()}

    @app.post("/api/compare")
    def compare(reference: UploadFile | None = File(None), later: UploadFile | None = File(None),
                detector_conf: float | None = Form(None), enable_alignment: bool | None = Form(None)):
        ref, lat = read_upload(reference, "reference"), read_upload(later, "later")
        s = request_settings(detector_conf, enable_alignment)
        need_detector()
        try:
            return pipeline.compare(ref, lat, s)
        except ValueError as e:  # e.g. invalid bounding boxes
            raise HTTPException(422, f"Processing error: {e}") from e
        except Exception as e:  # noqa: BLE001
            raise HTTPException(500, f"Internal processing error: {type(e).__name__}: {e}") from e

    @app.post("/api/observe")
    def observe(image: UploadFile | None = File(None), detector_conf: float | None = Form(None),
                enable_alignment: bool | None = Form(None)):
        """Store a new observation and compare it with the latest stored observation, if any."""
        img = read_upload(image, "image")
        s = request_settings(detector_conf, enable_alignment)
        need_detector()
        prev = memory.latest()
        prev_img = None
        if prev:
            p = memory.image_path(prev["image"].get("stored_file", ""))
            if p is not None:
                from src.image_io import decode_upload as _dec
                prev_img = _dec(p.read_bytes(), prev["image"]["filename"], settings)
        try:
            if prev_img is None:
                dets = detector.detect(img.bgr, img.image_id, img.sha256, s.detector_conf)
                meta = img.meta()
                meta["stored_file"] = memory.store_image(img)
                rec = memory.save({"role": "single", "image": meta, "model": settings.model_name,
                                   "detections": [d.to_dict() for d in dets], "comparison": None})
                return {"status": "stored_first_observation", "observation": SceneMemory.summary(rec),
                        "message": "No earlier stored observation to compare against."}
            report = pipeline.compare(prev_img, img, s, against_observation_id=prev["observation_id"])
            return {"status": "compared_with_latest", "against_observation_id": prev["observation_id"], "report": report}
        except Exception as e:  # noqa: BLE001
            raise HTTPException(500, f"Internal processing error: {type(e).__name__}: {e}") from e

    @app.get("/api/observations")
    def observations():
        recs = memory.all()
        w, memory.warnings = list(memory.warnings), []
        return {"count": len(recs), "observations": [SceneMemory.summary(r) for r in reversed(recs)], "warnings": w}

    @app.get("/api/observations/{observation_id}")
    def observation(observation_id: str):
        r = memory.get(observation_id)
        if r is None:
            raise HTTPException(404, "Observation not found")
        return r

    @app.get("/api/images/{filename}")
    def stored_image(filename: str):
        p = memory.image_path(filename) if _FILE.match(filename) else None
        if p is None:
            raise HTTPException(404, "Image not found")
        return FileResponse(p)

    @app.get("/api/reports")
    def reports():
        return {"reports": reporting.list_reports(paths.reports)}

    @app.get("/api/reports/{report_id}")
    def report(report_id: str, download: bool = False):
        r = reporting.load_report(paths.reports, report_id)
        if r is None:
            raise HTTPException(404, "Report not found")
        headers = {"Content-Disposition": f'attachment; filename="{report_id}.json"'} if download else None
        return JSONResponse(r, headers=headers)

    @app.get("/api/reports/{report_id}/csv")
    def report_csv(report_id: str):
        r = reporting.load_report(paths.reports, report_id)
        if r is None:
            raise HTTPException(404, "Report not found")
        return PlainTextResponse(reporting.findings_csv(r), media_type="text/csv",
                                 headers={"Content-Disposition": f'attachment; filename="{report_id}_findings.csv"'})

    @app.get("/api/outputs/{kind}/{filename}")
    def output_file(kind: str, filename: str):
        folder = {"annotated": paths.annotated, "baseline": paths.baseline}.get(kind)
        if folder is None or not _FILE.match(filename):
            raise HTTPException(404, "Not found")
        p = (folder / filename).resolve()
        if p.parent != folder.resolve() or not p.exists():
            raise HTTPException(404, "Not found")
        return FileResponse(p)

    @app.get("/api/zones")
    def zones():
        z, w = spatial_analysis.load_zones(paths.zones / "zones.json")
        return {"zones": [{**x, "polygon": [list(p) for p in x["polygon"]]} for x in z], "warnings": w}

    return app


app = create_app()
