import pytest
from fastapi.testclient import TestClient
from conftest import StubDetector, encode, textured
from config import Settings
from main import create_app

REF, LAT = textured(1), textured(1).copy()
LAT[50:90, 50:90] = 255


@pytest.fixture
def client_factory(paths):
    def make(script=None, fail=False, settings=None):
        s = settings or Settings().validate()
        return TestClient(create_app(StubDetector(s, script, fail), s, paths))
    return make


def files(**kw):
    return {k: (f"{k}.png", v, "image/png") for k, v in kw.items()}


def sha(img):
    import hashlib
    return hashlib.sha256(encode(img)).hexdigest()


def test_health_reports_detector(client_factory):
    r = client_factory().get("/health")
    assert r.status_code == 200 and r.json()["detector"]["initialized"] is True


def test_health_when_detector_failed(client_factory):
    assert client_factory(fail=True).get("/health").json()["detector"]["initialized"] is False


def test_missing_files_422(client_factory):
    c = client_factory()
    assert c.post("/api/compare").status_code == 422
    assert c.post("/api/compare", files=files(reference=encode(REF))).status_code == 422


def test_non_image_415_empty_400_corrupt_400(client_factory):
    c = client_factory()
    assert c.post("/api/compare", files=files(reference=b"hello", later=encode(LAT))).status_code == 415
    assert c.post("/api/compare", files=files(reference=b"", later=encode(LAT))).status_code == 400
    assert c.post("/api/compare", files=files(reference=b"\x89PNG\r\n\x1a\nxx", later=encode(LAT))).status_code == 400


def test_oversize_413(client_factory):
    c = client_factory(settings=Settings().with_overrides(max_upload_bytes=500))
    assert c.post("/api/compare", files=files(reference=encode(REF), later=encode(LAT))).status_code == 413


def test_invalid_config_override_422(client_factory):
    r = client_factory().post("/api/compare", files=files(reference=encode(REF), later=encode(LAT)), data={"detector_conf": "7"})
    assert r.status_code == 422 and "detector_conf" in r.json()["detail"]


def test_detector_unavailable_503(client_factory):
    r = client_factory(fail=True).post("/api/compare", files=files(reference=encode(REF), later=encode(LAT)))
    assert r.status_code == 503 and "weights" in r.json()["detail"]


def test_compare_end_to_end_with_stub_detector(client_factory):
    script = {sha(REF): [("cup", (50, 50, 100, 100), 0.9), ("book", (200, 150, 260, 210), 0.9)],
              sha(LAT): [("cup", (50, 50, 100, 100), 0.9), ("chair", (150, 20, 220, 120), 0.8)]}
    c = client_factory(script)
    r = c.post("/api/compare", files=files(reference=encode(REF), later=encode(LAT)), data={"enable_alignment": "false"})
    assert r.status_code == 200, r.text
    rep = r.json()
    types = sorted(f["change_type"] for f in rep["findings"])
    assert types == ["newly_observed", "not_observed", "unchanged"]
    assert rep["baseline"]["available"] and rep["baseline"]["region_count"] >= 1
    # outputs and report retrieval
    for url in rep["outputs"].values():
        assert c.get(url).status_code == 200
    assert c.get(f"/api/reports/{rep['report_id']}").json()["report_id"] == rep["report_id"]
    d = c.get(f"/api/reports/{rep['report_id']}?download=true")
    assert "attachment" in d.headers["content-disposition"]
    csv = c.get(f"/api/reports/{rep['report_id']}/csv")
    assert csv.text.startswith("finding_id,") and len(csv.text.strip().splitlines()) == 4
    # history persisted
    obs = c.get("/api/observations").json()
    assert obs["count"] >= 2 and obs["observations"][0]["comparison"]["report_id"] == rep["report_id"]


def test_zero_detections_do_not_crash(client_factory):
    r = client_factory().post("/api/compare", files=files(reference=encode(REF), later=encode(LAT)))
    assert r.status_code == 200 and r.json()["findings"] == [] and r.json()["warnings"]


def test_unsafe_paths_and_missing_resources_404(client_factory):
    c = client_factory()
    for url in ["/api/outputs/annotated/..%2f..%2fetc%2fpasswd", "/api/outputs/secrets/x.jpg", "/api/reports/rep_000000000000",
                "/api/reports/../../etc/passwd", "/api/observations/obs_000000000000", "/api/images/..%2fx"]:
        assert c.get(url).status_code == 404, url


def test_observe_stores_first_then_compares(client_factory):
    c = client_factory()
    a = c.post("/api/observe", files={"image": ("a.png", encode(REF), "image/png")}).json()
    assert a["status"] == "stored_first_observation"
    b = c.post("/api/observe", files={"image": ("b.png", encode(LAT), "image/png")}).json()
    assert b["status"] == "compared_with_latest" and b["report"]["reference_image"]["image_id"] == a["observation"]["image"]["image_id"]


def test_cors_only_for_dev_origin(client_factory):
    c = client_factory()
    ok = c.get("/health", headers={"Origin": "http://localhost:5173"})
    bad = c.get("/health", headers={"Origin": "http://evil.example"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers
