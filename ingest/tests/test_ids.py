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
