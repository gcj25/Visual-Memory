"""Single configuration module: all thresholds, weights and paths live here.

Defaults can be overridden by an optional ``backend/settings.json`` (unknown keys are
rejected) and, for a small whitelist of values, per request. Every override is validated.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
WEIGHTS_DIR = BACKEND_DIR / "weights"

# Frozen detection whitelist (COCO label names).
WHITELIST = ("chair", "laptop", "tv", "keyboard", "mouse", "bottle", "cup", "book", "backpack", "cell phone")

# Explicit local development origins only (no wildcard).
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


@dataclass(frozen=True)
class Settings:
    # --- detector ---
    model_name: str = "yolo11n.pt"
    model_url: str = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt"
    detector_conf: float = 0.25
    detector_imgsz: int = 640
    device: str = "cpu"
    # --- upload validation ---
    max_upload_bytes: int = 10 * 1024 * 1024
    min_dimension: int = 32
    max_dimension: int = 8000
    max_pixels: int = 40_000_000
    # --- matching: cost = alpha*(1-IoU) + beta*normalized_centroid_distance ---
    match_alpha: float = 0.6
    match_beta: float = 0.4
    max_match_cost: float = 0.80
    ambiguity_margin: float = 0.10
    # --- change classification (displacement = centroid distance / unit-square diagonal) ---
    unchanged_tolerance: float = 0.03
    relocated_threshold: float = 0.06
    # --- uncertainty rules ---
    low_confidence_threshold: float = 0.50
    weak_match_cost: float = 0.70
    boundary_margin_frac: float = 0.02
    occlusion_overlap_fraction: float = 0.30
    area_ratio_limit: float = 2.0
    large_displacement_threshold: float = 0.45
    # --- alignment (optional ORB + RANSAC) ---
    enable_alignment: bool = True
    orb_features: int = 2000
    orb_max_side: int = 1000
    orb_ratio_test: float = 0.75
    ransac_reproj_threshold: float = 4.0
    alignment_min_matches: int = 20
    alignment_min_inliers: int = 15
    alignment_min_inlier_ratio: float = 0.35
    alignment_good_inlier_ratio: float = 0.60
    # --- pixel-difference baseline ---
    baseline_threshold: int = 30
    baseline_blur_kernel: int = 5
    baseline_morph_kernel: int = 5
    baseline_min_region_frac: float = 0.0005
    baseline_aspect_tolerance: float = 0.02
    # --- output ---
    output_max_side: int = 1280

    def validate(self) -> "Settings":
        def need(cond: bool, msg: str) -> None:
            if not cond:
                raise ValueError(f"Invalid configuration: {msg}")

        need(0.0 < self.detector_conf <= 1.0, "detector_conf must be in (0, 1]")
        need(self.detector_imgsz >= 32, "detector_imgsz must be >= 32")
        need(self.match_alpha >= 0 and self.match_beta >= 0 and (self.match_alpha + self.match_beta) > 0,
             "match_alpha/match_beta must be non-negative and not both zero")
        need(self.max_match_cost > 0, "max_match_cost must be > 0")
        need(0 <= self.ambiguity_margin <= 1, "ambiguity_margin must be in [0, 1]")
        need(0 <= self.unchanged_tolerance <= self.relocated_threshold,
             "require 0 <= unchanged_tolerance <= relocated_threshold")
        need(0 <= self.low_confidence_threshold <= 1, "low_confidence_threshold must be in [0, 1]")
        need(self.weak_match_cost > 0, "weak_match_cost must be > 0")
        need(0 <= self.boundary_margin_frac < 0.5, "boundary_margin_frac must be in [0, 0.5)")
        need(0 < self.occlusion_overlap_fraction <= 1, "occlusion_overlap_fraction must be in (0, 1]")
        need(self.area_ratio_limit > 1, "area_ratio_limit must be > 1")
        need(self.max_upload_bytes > 0, "max_upload_bytes must be > 0")
        need(0 < self.min_dimension < self.max_dimension, "dimension limits inconsistent")
        need(0 < self.alignment_min_inlier_ratio <= 1, "alignment_min_inlier_ratio must be in (0, 1]")
        need(self.alignment_min_inliers >= 4, "alignment_min_inliers must be >= 4 (homography needs 4 points)")
        need(0 <= self.baseline_threshold <= 255, "baseline_threshold must be in [0, 255]")
        need(self.baseline_blur_kernel % 2 == 1 and self.baseline_morph_kernel >= 1,
             "baseline_blur_kernel must be odd; baseline_morph_kernel >= 1")
        return self

    def with_overrides(self, **kw) -> "Settings":
        allowed = {f.name for f in fields(self)}
        unknown = set(kw) - allowed
        if unknown:
            raise ValueError(f"Invalid configuration: unknown keys {sorted(unknown)}")
        return replace(self, **kw).validate()

    def to_dict(self) -> dict:
        return asdict(self)


def load_settings(path: Path | None = None) -> Settings:
    path = path or (BACKEND_DIR / "settings.json")
    base = Settings()
    if path.exists():
        try:
            overrides = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid configuration: {path} is not valid JSON ({e})") from e
        return base.with_overrides(**overrides)
    return base.validate()


@dataclass(frozen=True)
class Paths:
    data: Path
    outputs: Path

    @staticmethod
    def default() -> "Paths":
        return Paths(Path(os.environ.get("VM_DATA_DIR", PROJECT_DIR / "data")),
                     Path(os.environ.get("VM_OUTPUT_DIR", PROJECT_DIR / "outputs")))

    @property
    def images(self) -> Path: return self.data / "images"
    @property
    def observations(self) -> Path: return self.data / "observations"
    @property
    def zones(self) -> Path: return self.data / "zones"
    @property
    def annotated(self) -> Path: return self.outputs / "annotated"
    @property
    def reports(self) -> Path: return self.outputs / "reports"
    @property
    def baseline(self) -> Path: return self.outputs / "baseline"

    def ensure(self) -> "Paths":
        for p in (self.images, self.observations, self.zones, self.annotated, self.reports, self.baseline):
            p.mkdir(parents=True, exist_ok=True)
        return self
