"""Optional ORB + RANSAC homography registration (reference -> later frame)."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from config import Settings
from .geometry import BBox, clip_box


@dataclass
class AlignmentResult:
    attempted: bool
    applied: bool
    reason: str
    n_keypoints_ref: int = 0
    n_keypoints_later: int = 0
    n_good_matches: int = 0
    n_inliers: int = 0
    inlier_ratio: float | None = None
    H: np.ndarray | None = None  # maps reference pixel coords -> later pixel coords

    def to_dict(self) -> dict:
        return {"attempted": self.attempted, "applied": self.applied, "reason": self.reason,
                "keypoints_reference": self.n_keypoints_ref, "keypoints_later": self.n_keypoints_later,
                "good_matches": self.n_good_matches, "inliers": self.n_inliers,
                "inlier_ratio": None if self.inlier_ratio is None else round(self.inlier_ratio, 4),
                "note": "inlier ratio is a RANSAC consistency indicator, not a calibrated probability"}


def _prep(img: np.ndarray, max_side: int):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    s = min(1.0, max_side / max(g.shape))
    if s < 1.0:
        g = cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return g, s


def estimate_alignment(ref_bgr: np.ndarray, later_bgr: np.ndarray, settings: Settings) -> AlignmentResult:
    try:
        g1, s1 = _prep(ref_bgr, settings.orb_max_side)
        g2, s2 = _prep(later_bgr, settings.orb_max_side)
        orb = cv2.ORB_create(nfeatures=settings.orb_features)
        k1, d1 = orb.detectAndCompute(g1, None)
        k2, d2 = orb.detectAndCompute(g2, None)
        res = AlignmentResult(True, False, "", len(k1 or []), len(k2 or []))
        if d1 is None or d2 is None or len(k1) < 8 or len(k2) < 8:
            res.reason = "too few ORB features"
            return res
        knn = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(d1, d2, k=2)
        good = [p[0] for p in knn if len(p) == 2 and p[0].distance < settings.orb_ratio_test * p[1].distance]
        res.n_good_matches = len(good)
        if len(good) < settings.alignment_min_matches:
            res.reason = f"only {len(good)} good feature matches (< {settings.alignment_min_matches})"
            return res
        p1 = np.float32([k1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        p2 = np.float32([k2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        Hs, mask = cv2.findHomography(p1, p2, cv2.RANSAC, settings.ransac_reproj_threshold)
        if Hs is None or mask is None:
            res.reason = "RANSAC failed to estimate a homography"
            return res
        res.n_inliers = int(mask.sum())
        res.inlier_ratio = res.n_inliers / len(good)
        if res.n_inliers < settings.alignment_min_inliers or res.inlier_ratio < settings.alignment_min_inlier_ratio:
            res.reason = f"insufficient inlier evidence ({res.n_inliers} inliers, ratio {res.inlier_ratio:.2f})"
            return res
        # back to full-resolution pixel coordinates: H = S2^-1 * Hs * S1
        S1, S2 = np.diag([s1, s1, 1.0]), np.diag([s2, s2, 1.0])
        H = np.linalg.inv(S2) @ Hs @ S1
        H = H / H[2, 2]
        det = np.linalg.det(H[:2, :2])
        if not np.all(np.isfinite(H)) or det <= 0 or not (0.1 < det < 10.0) or abs(H[2, 0]) > 1e-2 or abs(H[2, 1]) > 1e-2:
            res.reason = "estimated homography is geometrically implausible"
            return res
        res.H, res.applied, res.reason = H, True, "homography accepted"
        return res
    except cv2.error as e:
        return AlignmentResult(True, False, f"OpenCV error during alignment: {e}")


def transform_box(bbox: BBox, H: np.ndarray, width: int, height: int) -> BBox | None:
    """Warp reference box corners into the later frame; return their axis-aligned hull, clipped
    to the later image, or None when it lies completely outside."""
    x1, y1, x2, y2 = bbox
    corners = np.float32([[x1, y1], [x2, y1], [x2, y2], [x1, y2]]).reshape(-1, 1, 2)
    w = cv2.perspectiveTransform(corners, H.astype(np.float64)).reshape(-1, 2)
    hull = (float(w[:, 0].min()), float(w[:, 1].min()), float(w[:, 0].max()), float(w[:, 1].max()))
    return clip_box(hull, width, height)
