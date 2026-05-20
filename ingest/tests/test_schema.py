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


def test_unknown_field_raises():
    """Schema is strict — typo'd field names must fail loudly."""
    with pytest.raises(ValidationError):
        EventRecord(
            id="x", significance=10,
            date=EventDate(y=1812, precision="year"),
            title_en="t", summary_en="s", story_path="p",
            categories=["rebbe"], sources=[],
            catagories=["rebbe"],  # typo
        )


def test_date_precision_year_rejects_m_and_d():
    with pytest.raises(ValidationError):
        EventDate(y=1812, m=3, precision="year")
    with pytest.raises(ValidationError):
        EventDate(y=1812, m=3, d=15, precision="year")


def test_date_precision_month_rejects_d():
    with pytest.raises(ValidationError):
        EventDate(y=1812, m=3, d=15, precision="month")


def test_date_precision_month_valid_with_just_m():
    d = EventDate(y=1812, m=3, precision="month")
    assert d.m == 3 and d.d is None


def test_empty_id_raises():
    with pytest.raises(ValidationError):
        EventRecord(
            id="",  # empty
            significance=10,
            date=EventDate(y=1812, precision="year"),
            title_en="t", summary_en="s", story_path="p",
            categories=["rebbe"], sources=[],
        )


def test_empty_title_allowed_for_intermediate_passes():
    """Pass 1/Pass 2 records may have empty title_en — Pass 3 fills English.
    The non-empty constraint at emit time is enforced by the Pass 5 linter, not the schema."""
    record = EventRecord(
        id="x", significance=10,
        date=EventDate(y=1812, precision="year"),
        title_en="",          # empty is allowed (intermediate stage)
        summary_en="",         # empty is allowed
        story_path="p",
        categories=["rebbe"], sources=[],
    )
    assert record.title_en == ""
