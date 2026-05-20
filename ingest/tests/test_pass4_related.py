from timeline_ingest.pass4_enrich import build_related
from timeline_ingest.schema import EventRecord, EventDate, EventSource


def _r(id, y, title):
    return EventRecord(
        id=id, significance=25,
        date=EventDate(y=y, precision="year"),
        title_en=title, summary_en="",
        story_path=f"stories/{id}.md",
        categories=["general"],
        sources=[EventSource(name="t")],
    )


def test_related_links_events_within_window():
    recs = [
        _r("a", 1812, "Alter Rebbe passes away"),
        _r("b", 1813, "Mitteler Rebbe becomes leader after Alter Rebbe"),
        _r("c", 1900, "Unrelated event in 1900"),
    ]
    out = build_related(recs, window=20)
    rel_a = next(r.related for r in out if r.id == "a")
    assert "b" in rel_a
    assert "c" not in rel_a


def test_related_excludes_self():
    recs = [_r("a", 1812, "Alter Rebbe passes")]
    out = build_related(recs, window=20)
    assert "a" not in out[0].related
