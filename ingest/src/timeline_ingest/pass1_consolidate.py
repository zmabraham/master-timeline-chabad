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


_EVENT_ERA_RE = re.compile(
    r"^-\s*\*\*(\d{4}):\*\*\s*(.+?)$\n(?:\s*-\s*_(.+?)_)?",
    re.MULTILINE,
)

_YEAR_HEADING_RE = re.compile(r"^###\s+(\d{4})\s*$", re.MULTILINE)
_YEAR_ENTRY_RE = re.compile(r"^-\s+\*\*(.+?)\*\*\s*\n((?:  -.*\n?)*)", re.MULTILINE)


def _parse_era_section(text: str) -> list[tuple[int, str, str]]:
    """Return (year, title_he, summary_he) tuples from the Events by Era section."""
    results = []
    for m in _EVENT_ERA_RE.finditer(text):
        year = int(m.group(1))
        title_he = m.group(2).strip()
        summary_he = (m.group(3) or "").strip()
        results.append((year, title_he, summary_he))
    return results


def _parse_year_section(text: str) -> list[tuple[int, str, str]]:
    """Return (year, title_he, summary_he) tuples from the Events by Year section.

    That section uses:
        ### YYYY
        - **title**
          - Category: <cat>
          - <description text>
          - Source: <source>
    """
    section_marker = "## Events by Year"
    start = text.find(section_marker)
    if start < 0:
        return []
    section_text = text[start:]

    results = []
    year_matches = list(_YEAR_HEADING_RE.finditer(section_text))
    for i, ym in enumerate(year_matches):
        year = int(ym.group(1))
        block_start = ym.end()
        block_end = year_matches[i + 1].start() if i + 1 < len(year_matches) else len(section_text)
        block = section_text[block_start:block_end]
        for entry in _YEAR_ENTRY_RE.finditer(block):
            title_he = entry.group(1).strip()
            detail_block = entry.group(2)
            summary_he = ""
            for dl in detail_block.splitlines():
                stripped = dl.strip().lstrip("- ").strip()
                if stripped and not stripped.startswith("Category:") and not stripped.startswith("Source:"):
                    summary_he = stripped
                    break
            results.append((year, title_he, summary_he))
    return results


def load_comprehensive_md(path: Path) -> list[EventRecord]:
    text = path.read_text(encoding="utf-8")
    seen: set[str] = set()
    out: list[EventRecord] = []

    all_entries: list[tuple[int, str, str]] = []
    all_entries.extend(_parse_era_section(text))
    all_entries.extend(_parse_year_section(text))

    for year, title_he, summary_he in all_entries:
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
