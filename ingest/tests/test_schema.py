import pytest
from pydantic import ValidationError

from timeline_ingest.schema import EventRecord, EventDate, EventSource


def test_minimal_valid_event():
    record = EventRecord(
        id="abc123",
        significance=85,
        date=EventDate(y=1812, precision="year"),
        title_en="Alter Rebbe passes away",
        summary_en="The first Chabad Rebbe passes away.",
        story_path="stories/abc123.md",
        categories=["rebbe"],
        sources=[EventSource(name="Chabadpedia")],
    )
    assert record.id == "abc123"
    assert record.date.y == 1812
    assert record.rebbe is None
    assert record.tags == []  # default empty


def test_event_supports_multiple_categories_and_tags():
    record = EventRecord(
        id="x",
        significance=60,
        date=EventDate(y=1900, precision="year"),
        title_en="t", summary_en="s", story_path="p",
        categories=["publication", "education"],
        tags=["russia", "tomchei tmimim", "yeshiva curriculum"],
        sources=[],
    )
    assert "publication" in record.categories
    assert "education" in record.categories
    assert "russia" in record.tags


def test_invalid_significance_raises():
    with pytest.raises(ValidationError):
        EventRecord(
            id="x", significance=150,
            date=EventDate(y=1812, precision="year"),
            title_en="t", summary_en="s", story_path="p",
            categories=["rebbe"], sources=[],
        )
    with pytest.raises(ValidationError):
        EventRecord(
            id="x", significance=-1,
            date=EventDate(y=1812, precision="year"),
            title_en="t", summary_en="s", story_path="p",
            categories=["rebbe"], sources=[],
        )


def test_invalid_category_raises():
    with pytest.raises(ValidationError):
        EventRecord(
            id="x", significance=10,
            date=EventDate(y=1812, precision="year"),
            title_en="t", summary_en="s", story_path="p",
            categories=["not-a-category"], sources=[],
        )


def test_empty_categories_raises():
    with pytest.raises(ValidationError):
        EventRecord(
            id="x", significance=10,
            date=EventDate(y=1812, precision="year"),
            title_en="t", summary_en="s", story_path="p",
            categories=[], sources=[],
        )


def test_date_precision_year():
    d = EventDate(y=1812, precision="year")
    assert d.m is None and d.d is None


def test_date_precision_day_requires_m_and_d():
    with pytest.raises(ValidationError):
        EventDate(y=1812, precision="day")
