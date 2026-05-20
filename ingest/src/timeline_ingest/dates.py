"""Date parsing utilities. Hebrew dates remain optional; Gregorian is primary."""

import re

from timeline_ingest.schema import EventDate

_SUPPORTED_MIN_YEAR = 1500
_SUPPORTED_MAX_YEAR = 2100

_YEAR_RE = re.compile(r"^\s*(\d{3,4})")
_ISO_RE = re.compile(r"^(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?$")


def is_supported_year(y: int) -> bool:
    return _SUPPORTED_MIN_YEAR <= y <= _SUPPORTED_MAX_YEAR


def parse_year_only(value: int | str) -> EventDate:
    if isinstance(value, int):
        y = value
    else:
        m = _YEAR_RE.match(value)
        if not m:
            raise ValueError(f"cannot parse year from {value!r}")
        y = int(m.group(1))
    if not is_supported_year(y):
        raise ValueError(f"year {y} out of supported range")
    return EventDate(y=y, precision="year")


def parse_iso_partial(s: str) -> EventDate:
    m = _ISO_RE.match(s.strip())
    if not m:
        raise ValueError(f"not an iso date: {s!r}")
    y = int(m.group(1))
    if not is_supported_year(y):
        raise ValueError(f"year {y} out of supported range")
    month = int(m.group(2)) if m.group(2) else None
    day = int(m.group(3)) if m.group(3) else None
    if day is not None:
        return EventDate(y=y, m=month, d=day, precision="day")
    if month is not None:
        return EventDate(y=y, m=month, precision="month")
    return EventDate(y=y, precision="year")
