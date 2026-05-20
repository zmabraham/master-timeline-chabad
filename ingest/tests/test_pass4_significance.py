from timeline_ingest.pass4_enrich import assign_significance, apply_overrides
from timeline_ingest.schema import EventRecord, EventDate, EventSource


def _r(title, categories, sources=None):
    return EventRecord(
        id="x",
        significance=0,
        date=EventDate(y=1812, precision="year"),
        title_en=title,
        summary_en="",
        story_path="stories/x.md",
        categories=categories,
        sources=sources or [EventSource(name="t")],
    )


def test_macro_band_for_rebbe_birth():
    r = _r("Alter Rebbe born", ["rebbe"])
    assert assign_significance(r) >= 80


def test_macro_band_for_tanya_publication():
    r = _r("Tanya first printed", ["publication"])
    assert assign_significance(r) >= 80


def test_meso_band_for_generic_yeshiva_founding():
    r = _r("Yeshiva founded in Krasnik", ["education"])
    s = assign_significance(r)
    assert 40 <= s < 80


def test_macro_band_for_flagship_tomchei_tmimim():
    r = _r("Tomchei Tmimim founded", ["education"])
    s = assign_significance(r)
    assert s >= 80


def test_micro_band_for_random_letter():
    r = _r("Letter from Rebbe to a chossid in Paris", ["general"])
    assert assign_significance(r) < 40


def test_score_is_clamped_to_0_100():
    r = _r("Alter Rebbe born and tanya printed and tomchei tmimim founded", ["rebbe"])
    s = assign_significance(r)
    assert 0 <= s <= 100


def test_apply_overrides_pins_score():
    r = _r("Letter from Rebbe to a chossid", ["general"])
    out = apply_overrides([r], {"x": 90})
    assert out[0].significance == 90
