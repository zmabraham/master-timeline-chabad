"""Pass 1 — load existing extractions, normalize, dedupe."""

import json
import re
from pathlib import Path

from timeline_ingest.config import Config
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


_EVENT_RE = re.compile(
    r"^-\s*\*\*(\d{4}):\*\*\s*(.+?)$\n(?:\s*-\s*_(.+?)_)?",
    re.MULTILINE,
)


def load_comprehensive_md(path: Path) -> list[EventRecord]:
    text = path.read_text(encoding="utf-8")
    seen: set[str] = set()
    out: list[EventRecord] = []
    for m in _EVENT_RE.finditer(text):
        year = int(m.group(1))
        title_he = m.group(2).strip()
        summary_he = (m.group(3) or "").strip()
        try:
            date = parse_year_only(year)
        except ValueError:
            continue
        eid = event_id(title_he, year=year, month=None, day=None)
        if eid in seen:
            continue
        seen.add(eid)
        out.append(
            EventRecord(
                id=eid,
                significance=25,
                date=date,
                title_en="",
                summary_en=summary_he,
                story_path=f"stories/{eid}.md",
                categories=["general"],
                sources=[EventSource(name="chabad-history-timeline-comprehensive.md")],
            )
        )
    return out


def consolidate(cfg: Config) -> Path:
    records: list[EventRecord] = []
    records.extend(load_compact_json(cfg.existing_extractions.compact_json))
    records.extend(load_comprehensive_md(cfg.existing_extractions.comprehensive_md))

    seen: dict[str, EventRecord] = {}
    for r in records:
        if r.id not in seen:
            seen[r.id] = r
        else:
            existing = seen[r.id]
            existing.sources.extend(r.sources)

    out_dir = cfg.output.intermediate_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "01_consolidated.json"
    payload = [r.model_dump(mode="json") for r in seen.values()]
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
