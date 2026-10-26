# Testing

Run: `cd backend && ../.venv/bin/python -m pytest -q` — last result in this environment: **84 passed** (~90 s, dominated by the real-model integration tests).

| File | Tests | Scope |
|---|---|---|
| test_matching.py | 22 | empty lists, identical, moved, incompatible classes, weak matches, multiple same-class, no duplicate assignment, ambiguity, invalid boxes, invalid configuration |
| test_change_detection.py | 8 | four change types, jitter, borderline, vocabulary, no removal claims |
| test_uncertainty.py | 8 | each main uncertainty rule, alignment handling |
| test_modules.py | 16 | malformed images, limits, baseline, alignment (synthetic translation recovered; featureless failure), zones, memory persistence/recovery/unsafe ids |
| test_api.py | 12 | error codes (422/415/400/413/503/404), CORS, end-to-end with a stub detector, reports/CSV, observe |
| test_memory_and_api.py | 15 | additional API/memory tests that were found in `tests/` during the build; I did not write them (see IMPLEMENTATION_STATUS.md) |
| test_integration_real.py | 3 | **real YOLO + real photo**: detects chairs, identical copy → all unchanged, removed-chair pair → `not_observed` without removal wording |

Unit and API tests use synthetic detections or a stub detector; only `test_integration_real.py` uses the real model.

## Observed results on edited pairs (real model, `data/sample_images`)
These are edits of one photograph (two adjacent, small chairs: scores 0.49 and 0.75), not independent captures. They show behaviour, not accuracy.

| Pair | Ground truth | System output |
|---|---|---|
| identical copy (re-encoded) | no change | 2 × unchanged (one uncertain: low score); baseline 0 regions |
| removed chair | 1 chair removed | 2 × `not_observed` (the weaker chair, score 0.49, was also lost after editing); baseline 2 regions |
| moved chair | 1 chair moved | 1 × `possibly_relocated` (uncertain: low score, ambiguous) + 1 × `not_observed` |
| added chair | 1 chair added | 1 × unchanged, 1 × `possibly_relocated` (uncertain: ambiguous) — the addition was not reported as `newly_observed` |

So detector instability near the threshold and adjacent same-class objects produce results that differ from ground truth, and uncertainty flags marked most of them. Not covered by tests: browser UI, GPU, large-scale accuracy, viewpoint changes beyond planar homography.

## Manual end-to-end verification (HTTP)
Backend and Vite dev server started; `/health`, CORS (allowed origin accepted, other origin rejected), real compare (HTTP 200, ~4 s including model load; ~0.1 s detection once loaded), annotated/baseline image fetches, JSON download, CSV, observations list, 415/422 error responses all checked; no errors in backend or frontend logs.
