import pytest
from config import Settings
from conftest import det
from src.object_matching import match_detections


def test_empty_reference(settings):
    r = match_detections([], [det("l1", "cup", (0, 0, 10, 10), img="B")], settings)
    assert r.matches == [] and r.unmatched_later == ["l1"] and r.unmatched_reference == []


def test_empty_later(settings):
    r = match_detections([det("r1", "cup", (0, 0, 10, 10))], [], settings)
    assert r.matches == [] and r.unmatched_reference == ["r1"]


def test_both_empty(settings):
    r = match_detections([], [], settings)
    assert r.matches == [] and r.unmatched_reference == [] and r.unmatched_later == []


def test_identical_detections_match_with_zero_cost(settings):
    r = match_detections([det("r1", "cup", (100, 100, 200, 200))], [det("l1", "cup", (100, 100, 200, 200), img="B")], settings)
    assert len(r.matches) == 1 and r.matches[0].cost == pytest.approx(0.0) and r.matches[0].iou == pytest.approx(1.0)


def test_moved_object_still_matches_with_distance(settings):
    r = match_detections([det("r1", "cup", (100, 100, 200, 200))], [det("l1", "cup", (180, 100, 280, 200), img="B")], settings)
    assert len(r.matches) == 1 and r.matches[0].norm_distance == pytest.approx(0.08 / 2 ** 0.5)


def test_incompatible_classes_never_match(settings):
    r = match_detections([det("r1", "cup", (100, 100, 200, 200))], [det("l1", "bottle", (100, 100, 200, 200), img="B")], settings)
    assert r.matches == [] and r.unmatched_reference == ["r1"] and r.unmatched_later == ["l1"]


def test_weak_match_rejected_by_threshold(settings):
    r = match_detections([det("r1", "cup", (0, 0, 50, 50))], [det("l1", "cup", (900, 900, 950, 950), img="B")], settings)
    assert r.matches == []


def test_multiple_same_class_matched_to_nearest(settings):
    ref = [det("r1", "cup", (100, 100, 150, 150)), det("r2", "cup", (700, 700, 750, 750))]
    later = [det("l1", "cup", (705, 705, 755, 755), img="B"), det("l2", "cup", (105, 100, 155, 150), img="B")]
    pairs = {(m.ref_id, m.later_id) for m in match_detections(ref, later, settings).matches}
    assert pairs == {("r1", "l2"), ("r2", "l1")}


def test_no_duplicate_assignments(settings):
    ref = [det(f"r{i}", "cup", (100 + i * 5, 100, 150 + i * 5, 150)) for i in range(3)]
    later = [det(f"l{i}", "cup", (100 + i * 5, 100, 150 + i * 5, 150), img="B") for i in range(2)]
    r = match_detections(ref, later, settings)
    assert len({m.ref_id for m in r.matches}) == len(r.matches) == 2
    assert len({m.later_id for m in r.matches}) == 2 and len(r.unmatched_reference) == 1


def test_ambiguity_flagged_for_near_equal_candidates(settings):
    ref = [det("r1", "cup", (400, 400, 450, 450))]
    later = [det("l1", "cup", (410, 400, 460, 450), img="B"), det("l2", "cup", (390, 400, 440, 450), img="B")]
    m = match_detections(ref, later, settings).matches[0]
    assert m.ambiguous and "near-equal" in m.ambiguity_detail


@pytest.mark.parametrize("bbox", [(10, 10, 5, 20), (10, 10, 10, 20), (0, 0, 2000, 10), (float("nan"), 0, 5, 5), (1, 2, 3)])
def test_invalid_bounding_boxes_rejected(settings, bbox):
    with pytest.raises(ValueError):
        match_detections([det("r1", "cup", bbox)], [det("l1", "cup", (0, 0, 10, 10), img="B")], settings)


@pytest.mark.parametrize("kw", [{"detector_conf": 0}, {"detector_conf": 1.5}, {"match_alpha": 0, "match_beta": 0},
                                {"unchanged_tolerance": 0.2, "relocated_threshold": 0.1}, {"match_alpha": -1},
                                {"baseline_blur_kernel": 4}, {"nonexistent_key": 1}])
def test_invalid_configuration_rejected(kw):
    with pytest.raises(ValueError, match="Invalid configuration"):
        Settings().with_overrides(**kw)
