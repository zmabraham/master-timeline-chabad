"""Stable, deterministic event IDs derived from normalized title + date."""

import hashlib
import re

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    s = _PUNCT_RE.sub(" ", title.lower())
    return _WS_RE.sub(" ", s).strip()


def event_id(title: str, *, year: int, month: int | None, day: int | None) -> str:
    if month is not None and not (1 <= month <= 12):
        raise ValueError(f"month must be 1..12 or None, got {month!r}")
    if day is not None and not (1 <= day <= 31):
        raise ValueError(f"day must be 1..31 or None, got {day!r}")
    norm = normalize_title(title)
    month_str = f"{month:02d}" if month is not None else "00"
    day_str = f"{day:02d}" if day is not None else "00"
    date_part = f"{year:04d}-{month_str}-{day_str}"
    payload = f"{norm}|{date_part}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]
