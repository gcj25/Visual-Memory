from conftest import det
from src.change_detection import classify_changes, summarize
from src.object_matching import match_detections


def run(ref, later, s):
    return classify_changes(ref, later, match_detections(ref, later, s), s)


def test_identical_is_unchanged_supported(settings):
    f = run([det("r1", "cup", (100, 100, 200, 200))], [det("l1", "cup", (100, 100, 200, 200), img="B")], settings)
    assert [(x.change_type, x.status) for x in f] == [("unchanged", "supported")]


def test_small_jitter_is_not_relocation(settings):
    f = run([det("r1", "cup", (100, 100, 200, 200))], [det("l1", "cup", (103, 102, 203, 202), img="B")], settings)
    assert f[0].change_type == "unchanged"


def test_moved_object_possibly_relocated(settings):
    f = run([det("r1", "cup", (100, 100, 200, 200))], [det("l1", "cup", (250, 100, 350, 200), img="B")], settings)
    assert f[0].change_type == "possibly_relocated" and f[0].displacement_norm > settings.relocated_threshold


def test_new_object_newly_observed(settings):
    f = run([], [det("l1", "cup", (100, 100, 200, 200), img="B")], settings)
    assert f[0].change_type == "newly_observed" and f[0].reference_detection is None


def test_missing_object_not_observed_without_claiming_removal(settings):
    f = run([det("r1", "cup", (100, 100, 200, 200))], [], settings)[0]
    assert f.change_type == "not_observed"
    text = (f.explanation + " ".join(f.caveats)).lower()
    assert "not evidence of removal" in text and "stolen" not in text and "disappear" not in text


def test_borderline_displacement_marked_uncertain(settings):
    # displacement ~0.05: above unchanged tolerance (0.03) but not above relocation threshold (0.06)
    f = run([det("r1", "cup", (100, 100, 200, 200))], [det("l1", "cup", (171, 100, 271, 200), img="B")], settings)[0]
    assert f.change_type == "possibly_relocated" and f.status == "uncertain"
    assert "borderline_displacement" in [r["code"] for r in f.uncertainty_reasons]


def test_both_empty_gives_no_findings(settings):
    assert run([], [], settings) == []


def test_findings_use_only_allowed_vocabulary_and_summarize(settings):
    ref = [det("r1", "cup", (100, 100, 200, 200)), det("r2", "book", (500, 500, 600, 600))]
    later = [det("l1", "cup", (100, 100, 200, 200), img="B"), det("l2", "chair", (700, 100, 800, 300), img="B")]
    f = run(ref, later, settings)
    assert {x.change_type for x in f} == {"unchanged", "not_observed", "newly_observed"}
    assert all(x.status in ("supported", "uncertain") and x.explanation for x in f)
    s = summarize(f)
    assert s["total"] == 3 and s["by_change_type"]["unchanged"] == 1
