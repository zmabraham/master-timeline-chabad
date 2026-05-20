"""Pass 4 — assign significance score (0–100), attach photos, build related[]."""

import re
from collections.abc import Iterable

from timeline_ingest.schema import EventCategory, EventRecord

_PATTERN_SCORES: list[tuple[re.Pattern, int]] = [
    (re.compile(r"\bborn\b", re.I), 50),
    (re.compile(r"\bpasses away\b|\bpassing\b", re.I), 50),
    (re.compile(r"\bbecame? .* rebbe\b|\bbecomes? .* rebbe\b", re.I), 50),
    (re.compile(r"\barrest(ed)?\b|\bexile(d)?\b|\bredemption\b", re.I), 45),
    (re.compile(r"\btanya\b|\blikkutei torah\b|\btorah or\b", re.I), 50),
    (re.compile(r"\btomchei tmimim\b", re.I), 30),
    (re.compile(r"\byeshiva\b|\bfounded\b|\bestablished\b", re.I), 25),
    (re.compile(r"\bpogrom\b|\bwar\b", re.I), 25),
    (re.compile(r"\bmaamar\b|\bsicha\b|\bfarbrengen\b", re.I), 15),
    (re.compile(r"\bemigration\b", re.I), 15),
]

_BASE_SCORE = 20
_CATEGORY_BONUSES: dict[EventCategory, int] = {
    "rebbe": 20,
    "publication": 10,
    "conflict": 10,
    "education": 5,
    "organization": 5,
    "location": 0,
    "calendar": 0,
    "general": 0,
}
_REBBE_FIELD_BONUS = 10


def assign_significance(rec: EventRecord) -> int:
    text = f"{rec.title_en} {rec.summary_en}".lower()
    score = _BASE_SCORE
    for pat, points in _PATTERN_SCORES:
        if pat.search(text):
            score += points
    if rec.categories:
        score += max(_CATEGORY_BONUSES.get(c, 0) for c in rec.categories)
    if rec.rebbe is not None:
        score += _REBBE_FIELD_BONUS
    return max(0, min(100, score))


def apply_overrides(
    records: Iterable[EventRecord],
    overrides: dict[str, int],
) -> list[EventRecord]:
    out: list[EventRecord] = []
    for r in records:
        score = overrides.get(r.id)
        if score is None:
            score = assign_significance(r)
        out.append(r.model_copy(update={"significance": int(score)}))
    return out
