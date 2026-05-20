from timeline_ingest.pass2_extract import parse_extraction_response, EXTRACTION_SYSTEM_PROMPT


def test_parse_extracts_valid_events():
    response = """Here are the events:
[
  {"title": "Alter Rebbe passes away", "year": 1812, "month": 12, "day": null,
   "categories": ["rebbe"], "tags": ["piena"],
   "summary": "Passing in Piena.", "story": "On 24 Tevet 5573..."},
  {"title": "Tanya first print", "year": 1797, "month": null, "day": null,
   "categories": ["publication", "education"], "tags": ["slavita"],
   "summary": "First edition.", "story": "Slavita printing."}
]
"""
    events = parse_extraction_response(response)
    assert len(events) == 2
    assert events[0]["title"] == "Alter Rebbe passes away"
    assert events[0]["year"] == 1812
    assert events[0]["month"] == 12
    assert events[1]["categories"] == ["publication", "education"]
    assert "slavita" in events[1]["tags"]


def test_parse_handles_empty_list():
    assert parse_extraction_response("[]") == []


def test_parse_raises_on_garbage():
    import pytest
    with pytest.raises(ValueError):
        parse_extraction_response("This is not JSON at all.")


def test_extraction_prompt_mentions_required_fields():
    assert "title" in EXTRACTION_SYSTEM_PROMPT
    assert "year" in EXTRACTION_SYSTEM_PROMPT
    assert "categories" in EXTRACTION_SYSTEM_PROMPT
    assert "tags" in EXTRACTION_SYSTEM_PROMPT
