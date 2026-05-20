from pathlib import Path

from timeline_ingest.pass1_consolidate import load_compact_json


def test_load_compact_dedupes_and_normalizes(tmp_path: Path):
    fixture = Path(__file__).parent / "fixtures" / "compact_sample.json"
    records = load_compact_json(fixture)
    assert len(records) == 2
    assert records[0].title_en == ""
    assert records[0].date.y in (1812, 1880)
    assert records[0].categories == ["rebbe"]
    assert records[0].tags == []
    assert records[0].significance == 25
    ids = {r.id for r in records}
    assert len(ids) == 2
