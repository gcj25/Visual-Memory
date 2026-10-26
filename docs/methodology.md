# Methodology

**Preprocessing.** Uploads are validated and decoded (EXIF orientation applied by OpenCV). Detection runs on the original image (Ultralytics letterboxes internally) and boxes are returned in original pixels. Images are never resized for matching; boxes are normalised to [0,1] per image.

**Detection.** Pretrained COCO `yolo11n`, CPU, same model/threshold for both images, whitelist: chair, laptop, tv, keyboard, mouse, bottle, cup, book, backpack, cell phone.

**IoU / centroid distance.** IoU = intersection / union of normalised boxes. Centroid distance is Euclidean in normalised coordinates divided by √2 (the unit-square diagonal), giving [0,1].

**Matching.** `cost = α(1−IoU) + β·d` (defaults α=0.6, β=0.4). Different classes and costs above `max_match_cost` (0.80) are gated out with a large constant, so `scipy.optimize.linear_sum_assignment` can never prefer an invalid pair; any assignment on a gated cell is discarded. A match is flagged *ambiguous* if another same-class candidate (for either side) has a cost within `ambiguity_margin` (0.10) and under the limit.

**Alignment (optional).** ORB (2000 features, max side 1000), ratio test 0.75, RANSAC homography. Accepted only with ≥20 good matches, ≥15 inliers, inlier ratio ≥0.35 and a plausible homography. The inlier ratio is a consistency indicator, not a probability. Reference box corners are warped into the later frame and their axis-aligned hull (clipped) is used; boxes falling wholly outside the later frame are excluded from matching.

**Classification.** Displacement = normalised centroid distance. ≤0.03 → `unchanged`; >0.03 → `possibly_relocated` (between 0.03 and 0.06 additionally flagged `borderline_displacement`, hence uncertain). Unmatched reference → `not_observed`; unmatched later → `newly_observed`. No cause or intent is inferred.

**Rule-based uncertainty.** Triggered rules: low detector score (<0.50), weak association (cost >0.70), ambiguous match, near image edge (2% margin), possible overlap/occlusion (≥30% covered by another detection), box-area ratio outside 1/2–2, displacement >0.45, borderline displacement, alignment failed/weak (non-`unchanged` findings only), projected outside frame. Any triggered rule ⇒ `uncertain`. No combined score is produced. These thresholds are engineering choices, not calibrated values.

**Spatial analysis.** Zones are polygons (normalised or pixel coordinates). Rule: overlap area / box area ≥ threshold for allowed classes. A hit is reported only as `potential_concern`.

**Pixel baseline.** Gaussian blur → absdiff → fixed threshold (30) → open/close → contours above a minimum area. If sizes differ, a uniform resize is used only when aspect ratios agree within 2%; otherwise the baseline is skipped with a warning.

**Temporal memory.** Each compare stores reference (once per image id) and later observations (detections, comparison summary) as separate JSON files; `/api/observe` compares a new image with the latest stored observation.

**Evaluation protocol.** `scripts/evaluate.py` takes a manifest of pairs with expected `(class, change_type)` entries and reports TP/FP/FN, precision/recall/F1 for the object-level method, a pair-level confusion count for the baseline, and mean time per pair. **No labelled dataset exists in this repository, so no formal results are reported.**
