"""Integration tests using the REAL pretrained YOLO model and real image files.
Skipped automatically if the weights or sample images are unavailable."""
from pathlib import Path

import pytest
from config import WEIGHTS_DIR, Paths, Settings
from src.detector import Detector
from src.image_io import decode_upload
from src.pipeline import Pipeline
from src.scene_memory import SceneMemory

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "sample_images"
pytestmark = pytest.mark.skipif(not (WEIGHTS_DIR / "yolo11n.pt").exists() or not (SAMPLES / "chairs_original.jpg").exists(),
                                reason="model weights or sample images missing")


@pytest.fixture(scope="module")
def pipe(tmp_path_factory):
    t = tmp_path_factory.mktemp("real")
    s = Settings().validate()
    paths = Paths(t / "d", t / "o").ensure()
    return Pipeline(s, Detector(s), SceneMemory(paths.observations, paths.images), paths), s


def load(name, s):
    return decode_upload((SAMPLES / name).read_bytes(), name, s)


def test_real_detector_finds_chairs_in_real_photo(pipe):
    p, s = pipe
    img = load("chairs_original.jpg", s)
    dets = p.detector.detect(img.bgr, img.image_id, img.sha256, s.detector_conf)
    assert len(dets) >= 1 and {d.class_name for d in dets} <= {"chair"}
    assert all(0 <= d.bbox[0] < d.bbox[2] <= img.width and 0 <= d.bbox[1] < d.bbox[3] <= img.height for d in dets)


def test_real_pair_identical_copy_has_no_changes(pipe):
    p, s = pipe
    r = p.compare(load("chairs_original.jpg", s), load("edit_identical_copy.jpg", s))
    assert r["findings"] and {f["change_type"] for f in r["findings"]} == {"unchanged"}
    assert r["model"]["family"].startswith("Ultralytics YOLO") and r["alignment"]["applied"]
    assert r["baseline"]["region_count"] == 0


def test_real_pair_removed_chair_reports_not_observed_not_removal(pipe):
    p, s = pipe
    r = p.compare(load("chairs_original.jpg", s), load("edit_removed_chair.jpg", s))
    kinds = {f["change_type"] for f in r["findings"]}
    assert "not_observed" in kinds
    assert all("removed" not in f["explanation"].lower() for f in r["findings"])
