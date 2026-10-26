# Implementation status

## 1. Implemented and verified
- Upload validation (type, size, decode, dimensions, bombs) — unit + API tests
- Real pretrained YOLO11n CPU detection with whitelist filtering — integration test + manual run
- Class-gated Hungarian matching, ambiguity detection — 22 tests
- Four-way change classification with explanations; supported/uncertain via rule-based reasons — tests
- Optional ORB/RANSAC alignment with failure handling — synthetic-translation test; real images aligned (inlier ratio ≈0.99–1.0 on edited copies)
- Pixel-difference baseline incl. refusal on mismatched aspect ratios — tests~
- Zone polygons + overlap rule — unit tests (the UI/image output for zones was produced but only the API output was checked)
- JSON observation memory with persistence, corruption recovery, no overwrite — tests
- JSON/CSV reports, annotated/baseline images, FastAPI endpoints, restricted CORS, safe file serving — tests + manual HTTP checks
- React app builds with no TypeScript errors and the dev server serves it

## 2. Partially implemented
- **Frontend behaviour** is type-checked and served, but I did not open it in a browser; layout, interaction and visual quality are unverified.
- Evaluation: script written but never run on labelled data; **no formal accuracy/precision/recall exists**.
- Spatial analysis uses one *example* zone; zone editing is by file only.
- shadcn/ui not used (registry unreachable); Python 3.12 instead of 3.11.
- Foreign files: `backend/tests/test_memory_and_api.py`, `helpers.py` and `tests/__init__.py` appeared in the workspace during the build and were not created by me. I kept them, and their tests pass after I fixed two real bugs they exposed (detector-coupled persistence; second-resolution timestamps). Review or remove them as you see fit.

## 3. Planned or not implemented
- Labelled real image pairs and formal evaluation; threshold calibration
- Viewpoint-robust matching beyond a planar homography; appearance (re-identification) features
- Zone drawing UI; authentication/multi-user; database; GPU use
