"""Evaluate object-level change detection vs the pixel baseline on labelled pairs.

Manifest (JSON): [{"reference": "a.jpg", "later": "b.jpg", "expected": [
    {"class_name": "chair", "change_type": "not_observed"}, ...]}]
Paths are relative to the manifest. A predicted finding counts as a true positive when an
unmatched expected (class, change_type) entry exists; only non-'unchanged' findings are scored.
The baseline has no classes, so it is scored per pair: 'changed?' = any region, vs expected non-empty.
Usage: python scripts/evaluate.py manifest.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import Paths, load_settings  # noqa: E402
from src.detector import Detector  # noqa: E402
from src.image_io import decode_upload  # noqa: E402
from src.pipeline import Pipeline  # noqa: E402
from src.scene_memory import SceneMemory  # noqa: E402


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * p * r / (p + r) if p and r else None
    return p, r, f


def main(manifest_path):
    mp = Path(manifest_path)
    pairs = json.loads(mp.read_text())
    s = load_settings()
    import tempfile
    t = Path(tempfile.mkdtemp())
    paths = Paths(t / "d", t / "o").ensure()
    pipe = Pipeline(s, Detector(s), SceneMemory(paths.observations, paths.images), paths)
    tp = fp = fn = 0
    b_tp = b_fp = b_fn = b_tn = 0
    times = []
    for p in pairs:
        ref = decode_upload((mp.parent / p["reference"]).read_bytes(), p["reference"], s)
        lat = decode_upload((mp.parent / p["later"]).read_bytes(), p["later"], s)
        rep = pipe.compare(ref, lat, persist=False)
        times.append(rep["timings"]["total_s"])
        exp = Counter((e["class_name"], e["change_type"]) for e in p["expected"])
        pred = Counter((f["class_name"], f["change_type"]) for f in rep["findings"] if f["change_type"] != "unchanged")
        hit = sum((exp & pred).values())
        tp += hit; fp += sum(pred.values()) - hit; fn += sum(exp.values()) - hit
        bl = rep["baseline"].get("region_count", 0) > 0 if rep["baseline"]["available"] else False
        if p["expected"]:
            b_tp += bl; b_fn += not bl
        else:
            b_fp += bl; b_tn += not bl
    P, R, F = prf(tp, fp, fn)
    print(json.dumps({"pairs": len(pairs), "object_level": {"tp": tp, "fp": fp, "fn": fn, "precision": P, "recall": R, "f1": F},
                      "pixel_baseline_pair_level": {"tp": b_tp, "fp": b_fp, "fn": b_fn, "tn": b_tn},
                      "mean_seconds_per_pair": sum(times) / len(times) if times else None}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
