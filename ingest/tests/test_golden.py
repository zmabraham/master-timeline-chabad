import json
from pathlib import Path

from timeline_ingest.pass1_consolidate import load_compact_json


def test_golden_compact_loads(tmp_path: Path):
    fixture_in = Path(__file__).parent / "fixtures" / "golden_input.json"
    expected = json.loads(
        (Path(__file__).parent / "fixtures" / "golden_expected.json").read_text()
    )
    compact = tmp_path / "compact.json"
    compact.write_text(json.dumps(json.loads(fixture_in.read_text())["compact"]))
    records = load_compact_json(compact)
    assert len(records) >= expected["min_records"]
    years = {r.date.y for r in records}
    for y in expected["expected_ids_contain_year"]:
        assert y in years
