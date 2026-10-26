# Visual Memory

An uncertainty-aware spatial and temporal intelligence system for visual scene change detection.

Compare two images of the same indoor scene. A COCO-pretrained YOLO detector finds ten object classes, Hungarian assignment links detections across the images, and every finding is classified as `unchanged`, `possibly_relocated`, `newly_observed` or `not_observed`, with `supported` or `uncertain` status and the evidence behind it. This project **integrates established techniques** (YOLO, IoU, Hungarian assignment, ORB/RANSAC registration, pixel differencing). It does not invent any of them, and its uncertainty handling is transparent rule-based abstention, not a Bayesian or calibrated method.

## Problem and objectives
Detect candidate object-level changes between observations, explain each one geometrically, and abstain (mark `uncertain`) when evidence is weak. "Not observed" never means "removed": the object may be occluded, out of frame, poorly lit or missed by the detector.

## Architecture
React (Vite, TypeScript, Tailwind) → HTTP/multipart → FastAPI → Python CV pipeline (validation → detection → optional alignment → matching → classification → uncertainty rules → spatial zones → pixel baseline → reports/annotations → JSON memory). All CV runs in Python. See `docs/architecture.md`.

## Stack
Python 3.12 (3.11 was not available), FastAPI, Uvicorn, Ultralytics 8.4 + PyTorch (CPU), OpenCV, NumPy, SciPy, Shapely, pytest; React 18, Vite 5, TypeScript, Tailwind 3, lucide-react. shadcn/ui was **not** used (its registry is not reachable from the build environment); the UI uses a few small hand-written components.

## Install
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt          # torch wheel is large; CUDA libs are bundled but unused
cd frontend && npm install && cd ..
```
**Model setup:** `yolo11n.pt` is downloaded automatically on first use into `backend/weights/` (from the Ultralytics assets release). Offline? Place the file there manually. Inference runs on CPU (`device` in `backend/config.py`); no GPU is used.

## Run
```bash
# terminal 1
cd backend && ../.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
# terminal 2
cd frontend && npm run dev          # http://127.0.0.1:5173
```
Set `VITE_API_URL` if the backend is elsewhere. CORS allows only `http://localhost:5173` and `http://127.0.0.1:5173`.

## First comparison
Open http://127.0.0.1:5173 → Compare → upload `data/sample_images/chairs_original.jpg` as the reference and e.g. `edit_removed_chair.jpg` as the later image. (The `edit_*` files are **edited copies** of one real photo, made by `backend/scripts/make_sample_pairs.py`; they are not independent real captures.)

API: `curl -F reference=@a.jpg -F later=@b.jpg localhost:8000/api/compare`. Endpoints: `GET /health`, `POST /api/compare`, `POST /api/observe` (single image vs latest stored observation), `GET /api/observations[/{id}]`, `GET /api/reports[/{id}]` (`?download=true`), `GET /api/reports/{id}/csv`, `GET /api/outputs/{annotated|baseline}/{file}`, `GET /api/images/{file}`, `GET /api/zones`, `GET /api/config`.

## Tests
```bash
cd backend && ../.venv/bin/python -m pytest -q
```
Details in `docs/testing.md`. Evaluation utility: `python backend/scripts/evaluate.py manifest.json` (protocol in `docs/methodology.md`).

## Storage
Reports: `outputs/reports/`; annotated images: `outputs/annotated/`; baseline masks: `outputs/baseline/`; observations (one JSON file each): `data/observations/`; stored originals (content-addressed): `data/images/`; zones: `data/zones/zones.json` (the shipped zone is an **example**; edit it).

## Limitations
- Detector confidence is a model score, not the probability of correct identification.
- COCO models may call a monitor `tv`; desks and specialised lab equipment may not be detected.
- A match between detections is not proof of the same physical object.
- Matching assumes a similar viewpoint or a successfully applied ORB/RANSAC alignment (homography is only valid for planar scenes or pure rotation).
- No formal performance evaluation has been done (no labelled dataset); see `IMPLEMENTATION_STATUS.md`.
- The UI was built and served but **not inspected in a real browser** in the build environment.
