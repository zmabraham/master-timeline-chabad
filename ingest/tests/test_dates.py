import pytest

from timeline_ingest.dates import (
    parse_year_only,
    parse_iso_partial,
    is_supported_year,
)


def test_parse_year_only_int():
    d = parse_year_only(1812)
    assert d.y == 1812 and d.precision == "year"


def test_parse_year_only_str_with_punct():
    d = parse_year_only("1812.")
    assert d.y == 1812 and d.precision == "year"


def test_parse_iso_partial_year_only():
    d = parse_iso_partial("1812")
    assert d.precision == "year" and d.m is None


def test_parse_iso_partial_year_month():
    d = parse_iso_partial("1812-03")
    assert d.precision == "month" and d.m == 3 and d.d is None


def test_parse_iso_partial_full_date():
    d = parse_iso_partial("1812-03-15")
    assert d.precision == "day" and d.m == 3 and d.d == 15


def test_parse_invalid_year_raises():
    with pytest.raises(ValueError):
        parse_year_only("not a year")


def test_is_supported_year_accepts_modern():
    assert is_supported_year(1741)
    assert is_supported_year(2026)


def test_is_supported_year_rejects_out_of_range():
    assert not is_supported_year(1200)
    assert not is_supported_year(2200)
