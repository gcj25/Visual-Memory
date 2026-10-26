import io
import json

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from config import Paths, Settings
from main import create_app
from src.scene_memory import SceneMemory
from src.schemas import Detection


class FakeDetector:
    """Test double standing in for YOLO. Used ONLY by automated API tests."""
    def __init__(self, per_image=None):
        self.calls = 0
        self.per_image = per_image

    def load(self): pass
    def status(self): return {"initialized": True, "model": "fake", "error": None}
    def info(self): return {"name": "fake-test-double", "device": "cpu"}

    def detect(self, bgr, image_id, sha, conf):
        self.calls += 1
        h, w = bgr.shape[:2]
        if int(bgr[0, 0, 0]) > 128:  # white-ish image => one chair
            return [Detection(f"{image_id}_d00", image_id, "chair", (w * .3, h * .3, w * .5, h * .6), 0.9, w, h)]
        return []


def png(color=0, size=(120, 160)):
    img = np.full((size[1], size[0], 3), color, np.uint8)
    return cv2.imencode(".png", img)[1].tobytes()


@pytest.fixture()
def api(tmp_path):
    import dataclasses
    base = Paths.default()
    fields = {f.name: getattr(base, f.name) for f in dataclasses.fields(base)}
    redirected = {k: (tmp_path / v.name if hasattr(v, "name") else v) for k, v in fields.items()}
    paths = Paths(**redirected)
    app = create_app(detector=FakeDetector(), settings=Settings(enable_alignment=False), paths=paths)
    return TestClient(app), paths


def post(c, ref, lat, **kw):
    return c.post("/api/compare", files={"reference": ("r.png", ref, "image/png"), "later": ("l.png", lat, "image/png")}, **kw)


def test_health(api):
    c, _ = api
    r = c.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_compare_ok_and_new_object(api):
    c, _ = api
    r = post(c, png(0), png(255))
    assert r.status_code == 200
    body = r.json()
    assert [f["change_type"] for f in body["findings"]] == ["newly_observed"]
    assert body["baseline"]["available"] is True


def test_empty_detections_both(api):
    c, _ = api
    r = post(c, png(0), png(10))
    assert r.status_code == 200 and r.json()["findings"] == []


def test_missing_file_422(api):
    c, _ = api
    r = c.post("/api/compare", files={"reference": ("r.png", png(0), "image/png")})
    assert r.status_code == 422


@pytest.mark.parametrize("data", [b"", b"not an image at all", b"\x89PNG\r\n\x1a\ngarbage", b"%PDF-1.4 fake"])
def test_malformed_image_rejected(api, data):
    c, _ = api
    r = post(c, data, png(0))
    assert 400 <= r.status_code < 500 and "detail" in r.json()


def test_oversized_upload_rejected(api):
    c, _ = api
    big = png(0) + b"\0" * (11 * 1024 * 1024)
    r = post(c, big, png(0))
    assert 400 <= r.status_code < 500


def test_invalid_conf_override_422(api):
    c, _ = api
    r = post(c, png(0), png(0), data={"detector_conf": "7"})
    assert r.status_code == 422


def test_unknown_report_and_path_traversal(api):
    c, _ = api
    assert c.get("/api/reports/rep_nope").status_code in (400, 404)
    assert c.get("/api/images/..%2F..%2Fetc%2Fpasswd").status_code in (400, 404)
    assert c.get("/api/outputs/annotated/..%2F..%2Fconfig.py").status_code in (400, 404)


def test_report_download_and_csv(api):
    c, _ = api
    rid = post(c, png(0), png(255)).json()["report_id"]
    assert c.get(f"/api/reports/{rid}").json()["report_id"] == rid
    assert "change_type" in c.get(f"/api/reports/{rid}/csv").text


def test_observe_history_persists(api):
    c, paths = api
    r1 = c.post("/api/observe", files={"image": ("a.png", png(0), "image/png")})
    r2 = c.post("/api/observe", files={"image": ("b.png", png(255), "image/png")})
    assert r1.status_code == 200 and r2.status_code == 200
    assert len(c.get("/api/observations").json()["observations"]) == 2
    # a fresh app over the same directories still sees them (restart persistence)
    app2 = create_app(detector=FakeDetector(), settings=Settings(), paths=paths)
    assert len(TestClient(app2).get("/api/observations").json()["observations"]) == 2


def test_memory_corrupt_json_recovery(tmp_path):
    m = SceneMemory(tmp_path / "o", tmp_path / "i")
    good = m.save({"image": {}, "detections": []})
    (tmp_path / "o" / "obs_bad.json").write_text("{ not json")
    (tmp_path / "o" / "obs_wrong.json").write_text(json.dumps([1, 2]))
    ids = [r["observation_id"] for r in m.all()]
    assert ids == [good["observation_id"]]
    assert m.warnings and (tmp_path / "o" / "obs_bad.json.corrupt").exists()


def test_memory_save_never_overwrites(tmp_path):
    m = SceneMemory(tmp_path / "o", tmp_path / "i")
    a, b = m.save({"x": 1}), m.save({"x": 2})
    assert a["observation_id"] != b["observation_id"] and len(m.all()) == 2
