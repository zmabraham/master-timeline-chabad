"""Pass 2 — LLM extraction from books to dated events."""

import asyncio
import json
import re
from pathlib import Path

from timeline_ingest.chunking import chunk_by_chars
from timeline_ingest.dates import is_supported_year
from timeline_ingest.ids import event_id
from timeline_ingest.llm import LLMClient
from timeline_ingest.schema import EventCategory, EventDate, EventRecord, EventSource

EXTRACTION_SYSTEM_PROMPT = """You extract dated historical events from Chabad history texts.

For every clearly dated event in the input, output one JSON object with these fields:
- title: ≤ 90 chars, in English (translate from Hebrew/Yiddish if needed)
- year: integer Gregorian year (required)
- month: integer 1–12 or null
- day: integer 1–31 or null
- categories: an array of one or more strings from this fixed set:
    rebbe | publication | conflict | education | organization | location | calendar | general
  An event can have multiple categories (e.g. ["publication","education"]).
- tags: an array of 0+ free-form lowercase string labels (geography like "russia"/"poland",
  themes like "samizdat"/"kgb"/"war", named figures, named institutions). Useful for
  faceted search and filtering. Do not duplicate the categories here.
- summary: one English sentence
- story: 2–4 English sentences with context

Return ONLY a JSON array (possibly empty). No commentary, no markdown fences."""


_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*\]")


def parse_extraction_response(text: str) -> list[dict]:
    m = _JSON_ARRAY_RE.search(text)
    if not m:
        raise ValueError("no JSON array found in response")
    return json.loads(m.group(0))


_VALID_CATEGORIES: set[EventCategory] = {
    "rebbe", "publication", "conflict", "education",
    "organization", "location", "calendar", "general",
}


def _row_to_record(row: dict, *, source_name: str) -> EventRecord | None:
    year = row.get("year")
    if not isinstance(year, int) or not is_supported_year(year):
        return None
    title = (row.get("title") or "").strip()
    if not title:
        return None
    month = row.get("month") if isinstance(row.get("month"), int) else None
    day = row.get("day") if isinstance(row.get("day"), int) else None

    raw_cats = row.get("categories") or row.get("category") or ["general"]
    if isinstance(raw_cats, str):
        raw_cats = [raw_cats]
    cats = [c for c in raw_cats if c in _VALID_CATEGORIES] or ["general"]

    raw_tags = row.get("tags") or []
    if not isinstance(raw_tags, list):
        raw_tags = []
    tags = [t.lower().strip() for t in raw_tags if isinstance(t, str) and t.strip()]

    precision = "day" if (month and day) else ("month" if month else "year")
    date = EventDate(y=year, m=month, d=day, precision=precision)
    eid = event_id(title, year=year, month=month, day=day)
    story_body = (row.get("story") or "").strip() or None
    return EventRecord(
        id=eid,
        significance=25,
        date=date,
        title_en=title,
        summary_en=row.get("summary", "").strip(),
        story_body=story_body,
        story_path=f"stories/{eid}.md",
        categories=cats,
        tags=tags,
        sources=[EventSource(name=source_name)],
    )


async def extract_book(
    client: LLMClient,
    book_path: Path,
    *,
    source_name: str,
    model: str = "claude-sonnet-4-6",
    max_chars: int = 24000,
) -> list[EventRecord]:
    text = book_path.read_text(encoding="utf-8")
    chunks = list(chunk_by_chars(text, max_chars=max_chars))
    tasks = [
        client.complete(system=EXTRACTION_SYSTEM_PROMPT, user=chunk, model=model)
        for chunk in chunks
    ]
    responses = await asyncio.gather(*tasks)
    out: list[EventRecord] = []
    seen: set[str] = set()
    for resp in responses:
        try:
            rows = parse_extraction_response(resp)
        except ValueError:
            continue
        for row in rows:
            rec = _row_to_record(row, source_name=source_name)
            if rec and rec.id not in seen:
                seen.add(rec.id)
                out.append(rec)
    return out
