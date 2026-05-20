"""Pass 1 — load existing extractions, normalize, dedupe."""

import json
from pathlib import Path

from timeline_ingest.dates import parse_year_only
from timeline_ingest.ids import event_id
from timeline_ingest.schema import EventCategory, EventRecord, EventSource

_CATEGORY_MAP: dict[str, EventCategory] = {
    "rebbe": "rebbe",
    "publication": "publication",
    "conflict": "conflict",
    "education": "education",
    "organization": "organization",
    "location": "location",
    "calendar": "calendar",
    "general": "general",
}


def _normalize_category(raw: str) -> EventCategory:
    return _CATEGORY_MAP.get(raw.lower(), "general")


def load_compact_json(path: Path) -> list[EventRecord]:
    """Load `chabad-timeline-compact.json`. Each row has y/t/d/c/s fields (Hebrew)."""
    with open(path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    seen: set[str] = set()
    out: list[EventRecord] = []
    for row in rows:
        try:
            date = parse_year_only(row["y"])
        except ValueError:
            continue
        title_he = row.get("t", "").strip()
        if not title_he:
            continue
        eid = event_id(title_he, year=date.y, month=None, day=None)
        if eid in seen:
            continue
        seen.add(eid)
        out.append(
            EventRecord(
                id=eid,
                significance=25,
                date=date,
                title_en="",
                summary_en=row.get("d", "").strip(),
                story_path=f"stories/{eid}.md",
                categories=[_normalize_category(row.get("c", "general"))],
                sources=[EventSource(name="chabad-timeline-compact.json")],
            )
        )
    return out
