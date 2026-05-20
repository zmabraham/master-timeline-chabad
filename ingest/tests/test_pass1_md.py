from pathlib import Path

from timeline_ingest.pass1_consolidate import load_comprehensive_md


def test_load_comprehensive_md_parses_events():
    fixture = Path(__file__).parent / "fixtures" / "comprehensive_sample.md"
    records = load_comprehensive_md(fixture)
    assert len(records) == 2
    years = {r.date.y for r in records}
    assert years == {1812, 1880}
    assert all(r.title_en == "" for r in records)
    assert all(
        r.sources[0].name == "chabad-history-timeline-comprehensive.md" for r in records
    )
