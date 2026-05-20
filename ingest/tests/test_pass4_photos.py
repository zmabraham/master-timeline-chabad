from timeline_ingest.pass4_enrich import attach_photos, _build_entity_index
from timeline_ingest.schema import EventRecord, EventDate, EventSource


def test_build_entity_index_extracts_image_urls():
    kg = {
        "Alter Rebbe": {"image": "https://example.org/alter.jpg", "credit": "Chabadpedia"},
        "Tanya": {"image": "https://example.org/tanya.jpg"},
    }
    idx = _build_entity_index(kg)
    assert "alter rebbe" in idx
    assert idx["alter rebbe"].url == "https://example.org/alter.jpg"


def test_attach_photos_matches_by_title_token():
    rec = EventRecord(
        id="x", significance=85,
        date=EventDate(y=1812, precision="year"),
        title_en="Alter Rebbe passes away",
        summary_en="",
        story_path="stories/x.md",
        categories=["rebbe"],
        sources=[EventSource(name="t")],
    )
    idx = {
        "alter rebbe": __import__("timeline_ingest.schema", fromlist=["EventPhoto"]).EventPhoto(
            url="https://x/a.jpg", credit="Chabadpedia"
        )
    }
    out = attach_photos([rec], entity_index=idx)
    assert out[0].photo is not None
    assert out[0].photo.url == "https://x/a.jpg"
