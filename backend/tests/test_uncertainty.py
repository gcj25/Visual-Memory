from conftest import det
from src.change_detection import classify_changes
from src.object_matching import match_detections


def one(ref, later, s, alignment=None):
    mr = match_detections(ref, later, s)
    return classify_changes(ref, later, mr, s, alignment)


def codes(f):
    return {r["code"] for r in f.uncertainty_reasons}


def test_clean_finding_is_supported(settings):
    f = one([det("r1", "cup", (400, 400, 500, 500))], [det("l1", "cup", (400, 400, 500, 500), img="B")], settings)[0]
    assert f.status == "supported" and f.uncertainty_reasons == []


def test_low_detector_confidence_triggers_uncertain(settings):
    f = one([det("r1", "cup", (400, 400, 500, 500), 0.3)], [det("l1", "cup", (400, 400, 500, 500), 0.9, "B")], settings)[0]
    assert f.status == "uncertain" and "low_detector_confidence" in codes(f)


def test_object_near_boundary(settings):
    f = one([det("r1", "cup", (0, 400, 100, 500))], [det("l1", "cup", (0, 400, 100, 500), img="B")], settings)[0]
    assert "near_image_boundary" in codes(f)


def test_possible_occlusion_by_overlapping_detection(settings):
    ref = [det("r1", "cup", (400, 400, 500, 500)), det("r2", "laptop", (380, 380, 520, 520))]
    later = [det("l1", "cup", (400, 400, 500, 500), img="B"), det("l2", "laptop", (380, 380, 520, 520), img="B")]
    fs = one(ref, later, settings)
    assert "possible_overlap_or_occlusion" in codes([f for f in fs if f.class_name == "cup"][0])


def test_ambiguous_match_triggers_uncertain(settings):
    ref = [det("r1", "cup", (400, 400, 450, 450))]
    later = [det("l1", "cup", (410, 400, 460, 450), img="B"), det("l2", "cup", (390, 400, 440, 450), img="B")]
    assert "ambiguous_match" in codes(one(ref, later, settings)[0])


def test_area_inconsistency(settings):
    f = one([det("r1", "cup", (400, 400, 450, 450))], [det("l1", "cup", (395, 395, 495, 495), img="B")], settings)[0]
    assert "bbox_area_inconsistency" in codes(f)


def test_failed_alignment_marks_geometry_findings_but_not_unchanged(settings):
    al = {"attempted": True, "applied": False, "reason": "too few features"}
    fs = one([det("r1", "cup", (400, 400, 500, 500))], [], settings, al)
    assert "alignment_unavailable" in codes(fs[0])
    ok = one([det("r1", "cup", (400, 400, 500, 500))], [det("l1", "cup", (400, 400, 500, 500), img="B")], settings, al)[0]
    assert ok.status == "supported"


def test_weak_alignment_reason(settings):
    al = {"attempted": True, "applied": True, "inlier_ratio": 0.4}
    assert "weak_alignment" in codes(one([], [det("l1", "cup", (400, 400, 500, 500), img="B")], settings, al)[0])
