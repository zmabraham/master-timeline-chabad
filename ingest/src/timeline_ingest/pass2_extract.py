"""Pass 2 — LLM extraction from books to dated events."""

import json
import re

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
