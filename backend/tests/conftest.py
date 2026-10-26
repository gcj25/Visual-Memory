import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import Paths, Settings  # noqa: E402
from src.schemas import Detection  # noqa: E402


def det(id_, cls, bbox, conf=0.9, img="A", w=1000, h=1000):
    return Detection(id=id_, image_id=img, class_name=cls, bbox=tuple(bbox), confidence=conf, image_width=w, image_height=h)


@pytest.fixture
def settings():
    return Settings().validate()


class StubDetector:
    """Test double that returns scripted detections keyed by image sha256 (no model involved)."""

    def __init__(self, settings, script=None, fail=False):
        self.settings, self.script, self.fail, self.ready = settings, script or {}, fail, True

    def load(self):
        if self.fail:
            from src.detector import DetectorUnavailable
            raise DetectorUnavailable("stub: weights missing")

    def info(self):
        return {"name": "stub", "device": "cpu"}

    def status(self):
        return {"initialized": not self.fail, "model": "stub", "error": "stub: weights missing" if self.fail else None}

    def detect(self, image_bgr, image_id, sha256=None, conf=None):
        h, w = image_bgr.shape[:2]
        return [det(f"{image_id}_d{i:02d}", c, b, s, image_id, w, h) for i, (c, b, s) in enumerate(self.script.get(sha256, []))]


def textured(seed=0, w=320, h=240):
    rng = np.random.default_rng(seed)
    img = cv2.GaussianBlur(rng.integers(0, 255, (h, w, 3), dtype=np.uint8), (3, 3), 0)
    for _ in range(60):
        cv2.circle(img, (int(rng.integers(0, w)), int(rng.integers(0, h))), int(rng.integers(3, 12)),
                   tuple(int(v) for v in rng.integers(0, 255, 3)), -1)
    return img


def encode(img, ext=".png"):
    ok, buf = cv2.imencode(ext, img)
    assert ok
    return buf.tobytes()


@pytest.fixture
def paths(tmp_path):
    return Paths(tmp_path / "data", tmp_path / "out").ensure()
