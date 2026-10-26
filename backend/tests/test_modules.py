import json

import cv2
import numpy as np
import pytest
from conftest import det, encode, textured
from src import baseline, spatial_analysis
from src.image_alignment import estimate_alignment, transform_box
from src.image_io import ImageValidationError, decode_upload
from src.scene_memory import SceneMemory


# ---------- image validation ----------
@pytest.mark.parametrize("data,status", [(b"", 400), (b"not an image at all", 415), (b"\xff\xd8\xff" + b"garbage" * 20, 400),
                                         (b"\x89PNG\r\n\x1a\n" + b"truncated", 400)])
def test_malformed_images_rejected(settings, data, status):
    with pytest.raises(ImageValidationError) as e:
        decode_upload(data, "x", settings)
    assert e.value.status_code == status


def test_oversize_and_tiny_rejected(settings):
    with pytest.raises(ImageValidationError) as e:
        decode_upload(encode(textured()), "x", settings.with_overrides(max_upload_bytes=100))
    assert e.value.status_code == 413
    with pytest.raises(ImageValidationError):
        decode_upload(encode(np.zeros((10, 10, 3), np.uint8)), "tiny", settings)


def test_valid_image_decodes_and_keeps_dimensions(settings):
    li = decode_upload(encode(textured(w=320, h=240), ".jpg"), "a.jpg", settings)
    assert (li.width, li.height, li.fmt) == (320, 240, "jpeg") and li.image_id.startswith("img_")


# ---------- baseline ----------
def test_baseline_identical_has_no_regions(settings):
    img = textured()
    b = baseline.compute_baseline(img, img.copy(), settings)
    assert b["available"] and b["region_count"] == 0 and b["changed_pixel_fraction"] == 0


def test_baseline_detects_block_and_refuses_distorting_resize(settings):
    a = textured(); b = a.copy(); b[80:160, 100:200] = 255
    r = baseline.compute_baseline(a, b, settings)
    assert r["region_count"] >= 1
    r2 = baseline.compute_baseline(a, cv2.resize(a, (320, 120)), settings)
    assert not r2["available"] and "aspect" in r2["warnings"][0]


# ---------- alignment ----------
def test_alignment_recovers_translation(settings):
    a = textured(1, 640, 480)
    M = np.float32([[1, 0, 25], [0, 1, 12]])
    b = cv2.warpAffine(a, M, (640, 480), borderMode=cv2.BORDER_REFLECT)
    res = estimate_alignment(a, b, settings)
    assert res.applied and res.inlier_ratio > 0.5
    box = transform_box((100, 100, 200, 200), res.H, 640, 480)
    assert box == pytest.approx((125, 112, 225, 212), abs=3)


def test_alignment_fails_cleanly_on_featureless_images(settings):
    flat = np.full((240, 320, 3), 128, np.uint8)
    res = estimate_alignment(flat, flat, settings)
    assert not res.applied and res.reason


def test_transform_box_outside_frame_returns_none():
    H = np.array([[1, 0, 1000], [0, 1, 0], [0, 0, 1]], float)
    assert transform_box((10, 10, 50, 50), H, 320, 240) is None


# ---------- spatial ----------
ZONE = {"zones": [{"id": "z", "polygon": [[0, 0.5], [1, 0.5], [1, 1], [0, 1]], "rule": {"min_overlap_fraction": 0.5, "classes": ["cup"]}}]}


def test_spatial_rule_reports_only_when_met(tmp_path):
    p = tmp_path / "z.json"; p.write_text(json.dumps(ZONE))
    zones, w = spatial_analysis.load_zones(p)
    inside, outside, wrong = (det("a", "cup", (100, 600, 200, 700)), det("b", "cup", (100, 100, 200, 200)),
                              det("c", "book", (100, 600, 200, 700)))
    f = spatial_analysis.analyze(zones, [inside, outside, wrong], "later")
    assert [x["detection_id"] for x in f] == ["a"] and f[0]["status"] == "potential_concern"


def test_zones_corrupt_file_is_safe(tmp_path):
    p = tmp_path / "z.json"; p.write_text("{not json")
    zones, w = spatial_analysis.load_zones(p)
    assert zones == [] and w


# ---------- scene memory ----------
def test_memory_persists_across_instances_and_never_overwrites(tmp_path):
    m1 = SceneMemory(tmp_path / "o", tmp_path / "i")
    a = m1.save({"role": "later", "image": {"image_id": "img_1"}, "detections": []})
    b = m1.save({"role": "later", "image": {"image_id": "img_2"}, "detections": []})
    m2 = SceneMemory(tmp_path / "o", tmp_path / "i")
    assert {r["observation_id"] for r in m2.all()} == {a["observation_id"], b["observation_id"]}
    assert m2.latest()["observation_id"] in (a["observation_id"], b["observation_id"])


def test_memory_recovers_from_corrupt_file(tmp_path):
    m = SceneMemory(tmp_path / "o", tmp_path / "i")
    good = m.save({"role": "later", "image": {}, "detections": []})
    (tmp_path / "o" / "obs_deadbeef0000.json").write_text("{broken")
    recs = m.all()
    assert [r["observation_id"] for r in recs] == [good["observation_id"]]
    assert m.warnings and (tmp_path / "o" / "obs_deadbeef0000.json.corrupt").exists()


def test_memory_rejects_unsafe_ids(tmp_path):
    m = SceneMemory(tmp_path / "o", tmp_path / "i")
    assert m.get("../../etc/passwd") is None and m.image_path("../../etc/passwd") is None
