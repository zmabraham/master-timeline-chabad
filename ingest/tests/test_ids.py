import pytest

from timeline_ingest.ids import event_id, normalize_title


def test_normalize_strips_punctuation_and_lowercases():
    assert normalize_title("Alter Rebbe — Passes Away!") == "alter rebbe passes away"


def test_normalize_collapses_whitespace():
    assert normalize_title("  Tanya   First   Print  ") == "tanya first print"


def test_event_id_is_deterministic():
    a = event_id("Alter Rebbe passes away", year=1812, month=None, day=None)
    b = event_id("Alter Rebbe passes away", year=1812, month=None, day=None)
    assert a == b
    assert len(a) == 12


def test_event_id_differs_by_date():
    a = event_id("Same title", year=1812, month=None, day=None)
    b = event_id("Same title", year=1813, month=None, day=None)
    assert a != b


def test_event_id_normalizes_title_before_hashing():
    a = event_id("Tanya — First Print!", year=1797, month=None, day=None)
    b = event_id("tanya first print", year=1797, month=None, day=None)
    assert a == b


def test_event_id_rejects_invalid_month():
    with pytest.raises(ValueError, match="month"):
        event_id("title", year=1812, month=0, day=None)
    with pytest.raises(ValueError, match="month"):
        event_id("title", year=1812, month=13, day=None)


def test_event_id_rejects_invalid_day():
    with pytest.raises(ValueError, match="day"):
        event_id("title", year=1812, month=3, day=0)
    with pytest.raises(ValueError, match="day"):
        event_id("title", year=1812, month=3, day=32)


def test_event_id_none_month_is_stable():
    """None means 'unknown', not 0. Test that None inputs are valid and produce
    a stable, consistent hash."""
    a = event_id("Same title", year=1812, month=None, day=None)
    b = event_id("Same title", year=1812, month=None, day=None)
    assert a == b
