# Architecture

Flow: `frontend → POST /api/compare (multipart) → main.py → Pipeline.compare → report JSON + images`.

| Module (backend/src) | Responsibility |
|---|---|
| `image_io.py` | Magic-byte type check, size/pixel/dimension limits, header-first bomb check, decode; content-derived image id (`img_<sha256[:12]>`); original bytes never modified |
| `detector.py` | Loads YOLO once (thread-locked), filters to the whitelist, returns original-pixel boxes `(x1,y1,x2,y2)`; caches raw results per (sha256, conf) |
| `image_alignment.py` | Optional ORB + RANSAC homography; rejects weak/implausible results; warps reference boxes into the later frame |
| `object_matching.py` | Class-gated cost, Hungarian assignment, cost-gated rejection, ambiguity detection |
| `change_detection.py` | Findings from matches/unmatched detections, explanations, caveats |
| `uncertainty.py` | Transparent rule list → `uncertain` + reasons |
| `spatial_analysis.py` | Zone polygons (Shapely) and overlap rule evidence |
| `baseline.py` | Grayscale absdiff + threshold + contours |
| `visualization.py`, `reporting.py` | Annotated images; JSON/CSV reports |
| `scene_memory.py` | One atomic JSON file per observation; corrupt files quarantined as `.corrupt` |
| `pipeline.py` | Orchestration, timings (measured with `perf_counter`) |

`main.py` is a thin HTTP layer (`create_app` factory so tests can inject a detector). `config.py` holds all thresholds and paths; overrides are validated.
