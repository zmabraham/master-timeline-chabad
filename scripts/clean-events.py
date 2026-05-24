#!/usr/bin/env python3
"""Clean Pass 5 emit artifacts: drop garbage events, strip prefix junk, prune orphan story files.

Reads public/events.json, applies a fixed set of heuristic filters to drop
LLM-extraction artifacts (Chabadpedia bio templates, anachronisms, calendar
labels, mis-parsed bullets), and writes the cleaned file back. Also removes
any stories/<id>.md whose event was dropped.

Run with `uv run python scripts/clean-events.py` from repo root.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVENTS_JSON = REPO / "public" / "events.json"
STORIES_DIR = REPO / "public" / "stories"


# --- Filter rules ----------------------------------------------------------

_MODERN_TERMS = re.compile(
    r"\b(?:hamas|israeli|nazi|holocaust|world\s+war|telegram|internet|email|fbi|"
    r"194[0-5]|19[5-9]\d|20\d{2})\b",
    re.IGNORECASE,
)
_BULLET_PREFIX = re.compile(r"^[-*•]\s+")
_DIGIT_PREFIX = re.compile(r"^\d+[\.\-]\d+\s")
_CALENDAR_LABEL = re.compile(
    r"^(?:eighteenth|nineteenth|first|second|third|fourth|fifth|sixth|seventh|"
    r"eighth|ninth|tenth|eleventh|twelfth|thirteenth|fourteenth|fifteenth|"
    r"sixteenth|seventeenth|twentieth|thirtieth)\b",
    re.IGNORECASE,
)


def should_drop(e: dict) -> str | None:
    """Return a reason string if event should be dropped, else None."""
    title = (e.get("title_en") or "").strip()
    summary = (e.get("summary_en") or "").strip()
    year = e.get("date", {}).get("y")
    haystack = f"{title} {summary}".lower()

    if not title:
        return "empty title"

    # Anachronism: pre-1800 mentioning modern terms
    if isinstance(year, int) and year < 1800 and _MODERN_TERMS.search(haystack):
        return "anachronism: pre-1800 with modern terms"

    # Chabadpedia "No free image. Rabbi X" — bio page template leakage
    if title.lower().startswith("no free image"):
        return "chabadpedia bio template (no free image)"

    # Page metadata leakage
    if "editing the source code" in title.lower():
        return "page metadata leakage"

    # Just a calendar ordinal ("Eighteenth of the second month")
    if _CALENDAR_LABEL.match(title) and "jewish calendar" in title.lower():
        return "calendar label only"

    # Title starts with stray punctuation
    if title.startswith((";", ":")) or title.startswith(",  "):
        return "starts with stray punctuation"

    # Title is "Free choice", "Special needs", "Tishrei", etc — single-concept
    # fragments that aren't actually events. But preserve named events like
    # "Bolshevik Revolution", "Kishinev pogrom", "Hebron massacre".
    KEEPER_TOKENS = re.compile(
        r"\b("
        # action verbs
        r"born|died|founded|published|printed|established|arrested|exiled|appointed|"
        r"passed|emigrated|fled|arrived|left|completed|begins?|ended?|created|"
        r"opened|closed|destroyed|liberated|captured|launched|signed|reached|"
        # event-noun heads (a 2-word title like 'Kishinev pogrom' should survive)
        r"revolution|massacre|pogrom|war|attack|uprising|rebellion|raid|"
        r"earthquake|fire|flood|expulsion|trial|conference|farbrengen|wedding|"
        r"bar\s+mitzvah|funeral|burial|publication|coronation|escape|rescue|"
        r"liberation|deportation|holocaust"
        r")\b"
    )
    if len(title.split()) < 3 and not KEEPER_TOKENS.search(title.lower()):
        return f"fragment (<3 words, no verb): {title!r}"

    return None


def clean_title(title: str) -> str:
    """Strip leading bullet/dash/digit-prefix noise."""
    t = title.strip()
    t = _BULLET_PREFIX.sub("", t)
    t = _DIGIT_PREFIX.sub("", t)
    return t.strip()


# --- Main ------------------------------------------------------------------


def main() -> int:
    if not EVENTS_JSON.exists():
        print(f"FATAL: {EVENTS_JSON} not found")
        return 1

    events = json.loads(EVENTS_JSON.read_text(encoding="utf-8"))
    print(f"loaded: {len(events)} events from {EVENTS_JSON}")

    kept: list[dict] = []
    dropped: list[tuple[dict, str]] = []
    reasons: dict[str, int] = {}

    for e in events:
        reason = should_drop(e)
        if reason:
            dropped.append((e, reason))
            reasons[reason] = reasons.get(reason, 0) + 1
            continue
        # Clean title in-place for kept records
        original = e.get("title_en") or ""
        cleaned = clean_title(original)
        if cleaned != original:
            e["title_en"] = cleaned
        kept.append(e)

    print(f"\nkept:    {len(kept)}")
    print(f"dropped: {len(dropped)}")
    print("\ndrop reasons:")
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"  {count:4d}  {reason}")

    # Fix orphan related[] ids (any record that referenced a dropped event)
    kept_ids = {e["id"] for e in kept}
    related_pruned = 0
    for e in kept:
        before = len(e.get("related") or [])
        e["related"] = [rid for rid in (e.get("related") or []) if rid in kept_ids]
        related_pruned += before - len(e["related"])
    if related_pruned:
        print(f"\npruned {related_pruned} orphan related[] refs to dropped events")

    # Write back events.json
    EVENTS_JSON.write_text(
        json.dumps(kept, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nwrote: {EVENTS_JSON} ({EVENTS_JSON.stat().st_size:,} bytes)")

    # Remove orphan story files
    if STORIES_DIR.exists():
        removed = 0
        for e, _ in dropped:
            md = STORIES_DIR / f"{e['id']}.md"
            if md.exists():
                md.unlink()
                removed += 1
        print(f"removed {removed} orphan story files from {STORIES_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
