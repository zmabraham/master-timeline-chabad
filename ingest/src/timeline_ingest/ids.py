"""Stable, deterministic event IDs derived from normalized title + date."""

import hashlib
import re

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    s = _PUNCT_RE.sub(" ", title.lower())
    return _WS_RE.sub(" ", s).strip()


def event_id(title: str, *, year: int, month: int | None, day: int | None) -> str:
    norm = normalize_title(title)
    date_part = f"{year:04d}-{month or 0:02d}-{day or 0:02d}"
    payload = f"{norm}|{date_part}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]
