# Master Timeline Chabad — Ingestion Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the offline Python ingestion pipeline that consolidates all Chabad-history source corpora and emits `public/events.json + public/stories/<id>.md + public/photos/<id>.webp` ready for the static web app to consume.

**Architecture:** Five sequential, idempotent, resumable passes. Each pass reads the previous pass's intermediate JSON and writes a new intermediate JSON, except Pass 5 which writes final artifacts to `public/`. Per-chunk caching keeps LLM costs predictable; Pydantic schema validates every emit. TDD throughout — every utility and pass has tests; a fixed 50-event golden-file sample exercises the pipeline end-to-end.

**Tech Stack:** Python 3.12, Pydantic v2, anthropic SDK (Claude Sonnet 4.6 with prompt caching), `pyyaml`, `unidecode`, `pytest`, `pytest-asyncio`, `httpx`, `Pillow` (image resize), `markdown-it-py` (parse comprehensive .md), `aiofiles`. Project managed with `uv`.

**Spec:** `docs/superpowers/specs/2026-05-20-chabad-history-timeline-design.md`

---

## File Structure

The ingestion package lives entirely under `ingest/`. Web app code is out of scope for this plan.

| Path | Responsibility |
|---|---|
| `ingest/pyproject.toml` | Package metadata, dependencies, uv lock |
| `ingest/sources.yaml` | Absolute paths to every source file/dir on disk |
| `ingest/glossary.yaml` | Locked Hebrew→English renderings (Rebbe names, places, terms) |
| `ingest/level_overrides.yaml` | Manual `id → level` overrides applied in Pass 4 |
| `ingest/src/timeline_ingest/__init__.py` | Package marker, version |
| `ingest/src/timeline_ingest/schema.py` | Pydantic `EventRecord` + nested models |
| `ingest/src/timeline_ingest/ids.py` | `event_id(title, date)` hash function |
| `ingest/src/timeline_ingest/dates.py` | Hebrew/Gregorian date parsing + normalization |
| `ingest/src/timeline_ingest/llm.py` | Anthropic client wrapper: concurrency, caching, retries |
| `ingest/src/timeline_ingest/pass1_consolidate.py` | Load existing extractions → normalize → dedupe |
| `ingest/src/timeline_ingest/pass2_extract.py` | LLM extraction over Undaunted + 17 books + Chabadpedia bios |
| `ingest/src/timeline_ingest/pass3_translate.py` | Hebrew→English with glossary lock |
| `ingest/src/timeline_ingest/pass4_enrich.py` | Level + photo + cross-reference |
| `ingest/src/timeline_ingest/pass5_emit.py` | Final emit + post-emit linter |
| `ingest/src/timeline_ingest/review.py` | Generate `review.html` between passes 4 and 5 |
| `ingest/src/timeline_ingest/cli.py` | `python -m timeline_ingest <pass>` entrypoint |
| `ingest/tests/conftest.py` | Pytest fixtures: paths, sample data |
| `ingest/tests/fixtures/` | Sample data for golden-file tests |
| `ingest/tests/test_*.py` | One test module per source module |
| `ingest/Makefile` | `make pass1 … make all` convenience targets |

`ingest/intermediate/` and `ingest/cache/` are gitignored runtime directories.

---

## Anthropic SDK guidance

@superpowers:claude-api applies — use it when adding LLM-calling code (Pass 2, Pass 3). Key requirements from the skill: enable prompt caching on the long system/glossary prefix, use `claude-sonnet-4-6` for extraction, use `claude-haiku-4-5-20251001` for translation (cheaper, sufficient quality with glossary lock). Verify exact model ids against the claude-api skill at implementation time; if the API returns 404 on either id, that skill resolves the current canonical ids.

## Spec-coverage notes (read before starting)

- **Chabadpedia knowledge graphs (KGs)** are used by Pass 4 for *photo attachment only*. KG-based event mining (extracting birth/death/founding dates from entity records) is **deferred to v1.5**; major Rebbe-lifecycle events are already covered by the existing extractions (Pass 1) plus Undaunted and the 17 history books (Pass 2), so this defer doesn't leave a gap in the v1 corpus.
- **Chabadpedia biographical pages** ARE in scope for Pass 2 (see Task 16 — third loop). They are plain text under `nanoclaw/groups/whatsapp_main/chabadpedia-web/pages/`.
- **Full story bodies** travel through every pass via an optional `story_body` field on `EventRecord` (added in Task 2). Pass 2 fills it with the 2–4 sentence story the LLM produces; Pass 5 writes it to `stories/<id>.md`. Pass 1 records (from the older Hebrew extractions) have no rich story body — Pass 5 falls back to `title + year + summary` for those.
- **Photo files** are downloaded and resized to WebP in Pass 5 (see Task 23). The linter (Task 24) verifies every referenced `photo.url` resolves to an actual file in `public/photos/`.

---

## Task 1: Scaffold the ingest package

**Files:**
- Create: `ingest/pyproject.toml`
- Create: `ingest/src/timeline_ingest/__init__.py`
- Create: `ingest/.python-version`
- Create: `ingest/Makefile`
- Create: `ingest/README.md`

- [ ] **Step 1: Initialize uv project**

Run from repo root:

```bash
cd ingest && uv init --package --no-readme --no-workspace . && cd ..
```

Expected: creates `ingest/pyproject.toml` and `ingest/src/timeline_ingest/__init__.py` stub.

- [ ] **Step 2: Pin Python and write pyproject.toml**

Overwrite `ingest/.python-version` with:

```
3.12
```

Overwrite `ingest/pyproject.toml`:

```toml
[project]
name = "timeline-ingest"
version = "0.1.0"
description = "Offline ingestion pipeline for Master Timeline Chabad"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.7",
    "anthropic>=0.40",
    "pyyaml>=6.0",
    "unidecode>=1.3",
    "httpx>=0.27",
    "pillow>=10.3",
    "markdown-it-py>=3.0",
    "aiofiles>=23.0",
    "rich>=13.7",
]

[dependency-groups]
dev = [
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.5",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py312"
```

- [ ] **Step 3: Write src/timeline_ingest/__init__.py**

Overwrite with:

```python
"""Master Timeline Chabad — offline ingestion pipeline."""
__version__ = "0.1.0"
```

- [ ] **Step 4: Install dependencies**

Run from repo root:

```bash
cd ingest && uv sync && cd ..
```

Expected: creates `.venv/` and `uv.lock`. Lock file is committed.

- [ ] **Step 5: Write Makefile**

Create `ingest/Makefile`:

```make
.PHONY: install test lint pass1 pass2 pass3 pass4 pass5 review all clean

install:
	uv sync

test:
	uv run pytest -v

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

pass1:
	uv run python -m timeline_ingest pass1

pass2:
	uv run python -m timeline_ingest pass2

pass3:
	uv run python -m timeline_ingest pass3

pass4:
	uv run python -m timeline_ingest pass4

review:
	uv run python -m timeline_ingest review

pass5:
	uv run python -m timeline_ingest pass5

all: pass1 pass2 pass3 pass4 review pass5

clean:
	rm -rf intermediate/* cache/*
```

- [ ] **Step 6: Write ingest/README.md**

Create `ingest/README.md`:

```markdown
# timeline-ingest

Offline ingestion pipeline. Run `make all` to execute all passes; run `make pass<N>` for a single pass.

See top-level `docs/superpowers/specs/2026-05-20-chabad-history-timeline-design.md` for design.
```

- [ ] **Step 7: Verify tests can run**

Run:

```bash
cd ingest && uv run pytest --co -q && cd ..
```

Expected: `no tests ran` (zero collected, no errors).

- [ ] **Step 8: Commit**

```bash
git add ingest/.python-version ingest/pyproject.toml ingest/uv.lock ingest/src ingest/Makefile ingest/README.md
git commit -m "feat(ingest): scaffold ingestion package"
```

---

## Task 2: EventRecord Pydantic schema

**Files:**
- Create: `ingest/src/timeline_ingest/schema.py`
- Create: `ingest/tests/test_schema.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_schema.py`:

```python
import pytest
from pydantic import ValidationError

from timeline_ingest.schema import EventRecord, EventDate, EventSource


def test_minimal_valid_event():
    record = EventRecord(
        id="abc123",
        level="macro",
        date=EventDate(y=1812, precision="year"),
        title_en="Alter Rebbe passes away",
        summary_en="The first Chabad Rebbe passes away.",
        story_path="stories/abc123.md",
        category="rebbe",
        sources=[EventSource(name="Chabadpedia")],
    )
    assert record.id == "abc123"
    assert record.date.y == 1812
    assert record.rebbe is None


def test_invalid_level_raises():
    with pytest.raises(ValidationError):
        EventRecord(
            id="x",
            level="huge",
            date=EventDate(y=1812, precision="year"),
            title_en="t",
            summary_en="s",
            story_path="p",
            category="rebbe",
            sources=[],
        )


def test_invalid_category_raises():
    with pytest.raises(ValidationError):
        EventRecord(
            id="x",
            level="macro",
            date=EventDate(y=1812, precision="year"),
            title_en="t",
            summary_en="s",
            story_path="p",
            category="not-a-category",
            sources=[],
        )


def test_date_precision_year():
    d = EventDate(y=1812, precision="year")
    assert d.m is None and d.d is None


def test_date_precision_day_requires_m_and_d():
    with pytest.raises(ValidationError):
        EventDate(y=1812, precision="day")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ingest && uv run pytest tests/test_schema.py -v && cd ..
```

Expected: FAIL (ImportError on `timeline_ingest.schema`).

- [ ] **Step 3: Write minimal implementation**

Create `ingest/src/timeline_ingest/schema.py`:

```python
"""Pydantic models for EventRecord and nested types."""

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

EventLevel = Literal["macro", "meso", "micro"]
EventCategory = Literal[
    "rebbe",
    "publication",
    "conflict",
    "education",
    "organization",
    "location",
    "calendar",
    "general",
]
RebbeId = Literal[
    "besht",
    "magid",
    "alter",
    "mitteler",
    "tzemach-tzedek",
    "maharash",
    "rashab",
    "rayatz",
    "rebbe",
]
DatePrecision = Literal["year", "month", "day"]


class EventDate(BaseModel):
    y: int = Field(ge=1500, le=2100)
    m: int | None = Field(default=None, ge=1, le=12)
    d: int | None = Field(default=None, ge=1, le=31)
    precision: DatePrecision

    @model_validator(mode="after")
    def _check_precision(self) -> Self:
        if self.precision == "day" and (self.m is None or self.d is None):
            raise ValueError("precision=day requires m and d")
        if self.precision == "month" and self.m is None:
            raise ValueError("precision=month requires m")
        return self


class HebrewDate(BaseModel):
    y: int
    m: str | None = None
    d: int | None = None


class EventPhoto(BaseModel):
    url: str
    credit: str
    caption: str | None = None


class EventSource(BaseModel):
    name: str
    url: str | None = None
    page: int | None = None


class EventRecord(BaseModel):
    id: str
    level: EventLevel
    date: EventDate
    hebrew_date: HebrewDate | None = None
    title_en: str
    summary_en: str
    story_body: str | None = None         # 2-4 sentence full story; written to stories/<id>.md by Pass 5
    story_path: str
    category: EventCategory
    rebbe: RebbeId | None = None
    era: str | None = None
    photo: EventPhoto | None = None
    sources: list[EventSource]
    related: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd ingest && uv run pytest tests/test_schema.py -v && cd ..
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/src/timeline_ingest/schema.py ingest/tests/test_schema.py
git commit -m "feat(ingest): EventRecord pydantic schema with validation"
```

---

## Task 3: Stable event ID hashing

**Files:**
- Create: `ingest/src/timeline_ingest/ids.py`
- Create: `ingest/tests/test_ids.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_ids.py`:

```python
from timeline_ingest.ids import event_id, normalize_title


def test_normalize_strips_punctuation_and_lowercases():
    assert normalize_title("Alter Rebbe — Passes Away!") == "alter rebbe passes away"


def test_normalize_collapses_whitespace():
    assert normalize_title("  Tanya   First   Print  ") == "tanya first print"


def test_event_id_is_deterministic():
    a = event_id("Alter Rebbe passes away", year=1812, month=None, day=None)
    b = event_id("Alter Rebbe passes away", year=1812, month=None, day=None)
    assert a == b
    assert len(a) == 12


def test_event_id_differs_by_date():
    a = event_id("Same title", year=1812, month=None, day=None)
    b = event_id("Same title", year=1813, month=None, day=None)
    assert a != b


def test_event_id_normalizes_title_before_hashing():
    a = event_id("Tanya — First Print!", year=1797, month=None, day=None)
    b = event_id("tanya first print", year=1797, month=None, day=None)
    assert a == b
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_ids.py -v && cd ..
```

Expected: FAIL (module not found).

- [ ] **Step 3: Write the implementation**

Create `ingest/src/timeline_ingest/ids.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd ingest && uv run pytest tests/test_ids.py -v && cd ..
```

Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/src/timeline_ingest/ids.py ingest/tests/test_ids.py
git commit -m "feat(ingest): deterministic event_id from normalized title+date"
```

---

## Task 4: Date normalization utility

**Files:**
- Create: `ingest/src/timeline_ingest/dates.py`
- Create: `ingest/tests/test_dates.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_dates.py`:

```python
import pytest

from timeline_ingest.dates import (
    parse_year_only,
    parse_iso_partial,
    is_supported_year,
)


def test_parse_year_only_int():
    d = parse_year_only(1812)
    assert d.y == 1812 and d.precision == "year"


def test_parse_year_only_str_with_punct():
    d = parse_year_only("1812.")
    assert d.y == 1812 and d.precision == "year"


def test_parse_iso_partial_year_only():
    d = parse_iso_partial("1812")
    assert d.precision == "year" and d.m is None


def test_parse_iso_partial_year_month():
    d = parse_iso_partial("1812-03")
    assert d.precision == "month" and d.m == 3 and d.d is None


def test_parse_iso_partial_full_date():
    d = parse_iso_partial("1812-03-15")
    assert d.precision == "day" and d.m == 3 and d.d == 15


def test_parse_invalid_year_raises():
    with pytest.raises(ValueError):
        parse_year_only("not a year")


def test_is_supported_year_accepts_modern():
    assert is_supported_year(1741)
    assert is_supported_year(2026)


def test_is_supported_year_rejects_out_of_range():
    assert not is_supported_year(1200)
    assert not is_supported_year(2200)
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_dates.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Write the implementation**

Create `ingest/src/timeline_ingest/dates.py`:

```python
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
    month = int(m.group(2)) if m.group(2) else None
    day = int(m.group(3)) if m.group(3) else None
    if day is not None:
        return EventDate(y=y, m=month, d=day, precision="day")
    if month is not None:
        return EventDate(y=y, m=month, precision="month")
    return EventDate(y=y, precision="year")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd ingest && uv run pytest tests/test_dates.py -v && cd ..
```

Expected: 8 PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/src/timeline_ingest/dates.py ingest/tests/test_dates.py
git commit -m "feat(ingest): year and ISO-partial date parsing"
```

---

## Task 5: sources.yaml — pin all source paths

**Files:**
- Create: `ingest/sources.yaml`
- Create: `ingest/src/timeline_ingest/config.py`
- Create: `ingest/tests/test_config.py`

- [ ] **Step 1: Write sources.yaml**

Create `ingest/sources.yaml`:

```yaml
# Absolute paths to every source corpus on disk.
# All paths are read-only; this pipeline never writes to them.

existing_extractions:
  compact_json: /home/chassidusaicon/code/nanoclaw/groups/whatsapp_main/chabad-timeline-compact.json
  comprehensive_md: /home/chassidusaicon/code/nanoclaw/groups/whatsapp_main/chabad-history-timeline-comprehensive.md
  chabadpedia_kg_dir: /home/chassidusaicon/code/nanoclaw/groups/whatsapp_main/chabadpedia-web

books_to_extract:
  undaunted_dir: /home/chassidusaicon/code/nanoclaw/groups/whatsapp_main
  undaunted_chapters_glob: "undaunted_chapter*.txt"
  chabad_library_dir: /home/chassidusaicon/code/nanoclaw/groups/whatsapp_main/chabad-library-clean-books
  chabad_library_history_book_ids:
    # All 17 books from the Misaviv L'Chassidus category.
    - "6300000000"  # מאסר וגאולת אדמו"ר האמצעי
    - "5100000000"  # תולדות אברהם חיים
    - "5200000000"  # תולדות חב"ד בארץ הקודש
    - "6800000000"  # תולדות חב"ד ברוסיה הצארית
    - "7000000000"  # תולדות חב"ד בפולין, ליטא ולטביא
    - "5300000000"  # זכרון לבני ישראל
    - "5500000000"  # למען ידעו בנים יוולדו
    - "5800000000"  # זכרונותי
    - "6200000000"  # ליובאוויטש
    - "6900000000"  # מבית הגנזים
    - "7800000000"  # תערוכות הספריה
    - "7900000000"  # יומן השליחות המיוחדת
    - "11200000469"  # עבודת הקודש
    - "11200003993"  # בכל ביתי נאמן הוא
    - "11200004131"  # אדמו"רי חב"ד ויהדות בוכרה
    - "11200004207"  # אדמו"רי חב"ד ויהדות אוסטריה
    - "11200004103"  # אדמו"רי חב"ד ויהדות גרמניה

chabadpedia_pages:
  dir: /home/chassidusaicon/code/nanoclaw/groups/whatsapp_main/chabadpedia-web/pages

photos:
  knowledge_graph_files:
    - rebbes: /home/chassidusaicon/code/nanoclaw/groups/whatsapp_main/chabadpedia-web/chabadpedia_knowledge_graph_rebbes.json
    - people: /home/chassidusaicon/code/nanoclaw/groups/whatsapp_main/chabadpedia-web/chabadpedia_knowledge_graph_people.json
    - places: /home/chassidusaicon/code/nanoclaw/groups/whatsapp_main/chabadpedia-web/chabadpedia_knowledge_graph_places.json
    - publications: /home/chassidusaicon/code/nanoclaw/groups/whatsapp_main/chabadpedia-web/chabadpedia_knowledge_graph_publications.json

output:
  intermediate_dir: intermediate
  cache_dir: cache
  public_dir: ../public
  glossary_path: glossary.yaml
  level_overrides_path: level_overrides.yaml
```

- [ ] **Step 2: Write failing test for config loader**

Create `ingest/tests/test_config.py`:

```python
from pathlib import Path

from timeline_ingest.config import load_config


def test_load_config_returns_sources(tmp_path: Path):
    yml = tmp_path / "sources.yaml"
    yml.write_text(
        "existing_extractions:\n"
        "  compact_json: /a\n"
        "  comprehensive_md: /b\n"
        "  chabadpedia_kg_dir: /c\n"
        "books_to_extract:\n"
        "  undaunted_dir: /u\n"
        "  undaunted_chapters_glob: 'foo*.txt'\n"
        "  chabad_library_dir: /cl\n"
        "  chabad_library_history_book_ids: ['1']\n"
        "chabadpedia_pages:\n"
        "  dir: /cp\n"
        "photos:\n"
        "  knowledge_graph_files: []\n"
        "output:\n"
        "  intermediate_dir: intermediate\n"
        "  cache_dir: cache\n"
        "  public_dir: ../public\n"
        "  glossary_path: glossary.yaml\n"
        "  level_overrides_path: level_overrides.yaml\n"
    )
    cfg = load_config(yml)
    assert cfg.existing_extractions.compact_json == Path("/a")
    assert cfg.books_to_extract.chabad_library_history_book_ids == ["1"]
    assert cfg.output.intermediate_dir == Path("intermediate")
```

- [ ] **Step 3: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_config.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 4: Write the config implementation**

Create `ingest/src/timeline_ingest/config.py`:

```python
"""Strongly-typed loader for sources.yaml."""

from pathlib import Path

import yaml
from pydantic import BaseModel


class ExistingExtractions(BaseModel):
    compact_json: Path
    comprehensive_md: Path
    chabadpedia_kg_dir: Path


class BooksToExtract(BaseModel):
    undaunted_dir: Path
    undaunted_chapters_glob: str
    chabad_library_dir: Path
    chabad_library_history_book_ids: list[str]


class ChabadpediaPages(BaseModel):
    dir: Path


class PhotoSources(BaseModel):
    knowledge_graph_files: list[dict[str, Path]]


class OutputPaths(BaseModel):
    intermediate_dir: Path
    cache_dir: Path
    public_dir: Path
    glossary_path: Path
    level_overrides_path: Path


class Config(BaseModel):
    existing_extractions: ExistingExtractions
    books_to_extract: BooksToExtract
    chabadpedia_pages: ChabadpediaPages
    photos: PhotoSources
    output: OutputPaths


def load_config(path: Path = Path("sources.yaml")) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Config.model_validate(raw)
```

- [ ] **Step 5: Run to verify pass**

```bash
cd ingest && uv run pytest tests/test_config.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ingest/sources.yaml ingest/src/timeline_ingest/config.py ingest/tests/test_config.py
git commit -m "feat(ingest): typed config loader + sources.yaml manifest"
```

---

## Task 6: Glossary and level-overrides stub files

**Files:**
- Create: `ingest/glossary.yaml`
- Create: `ingest/level_overrides.yaml`

- [ ] **Step 1: Write glossary stub**

Create `ingest/glossary.yaml`. Initial seed; the implementing agent expands this as it encounters proper nouns in extracted Hebrew text.

```yaml
# Locked Hebrew → English renderings.
# When LLMs translate, they are instructed to use these exact phrases.
# Expand this file as new proper nouns appear in extractions.

rebbes:
  בעש"ט: "Baal Shem Tov"
  הרב המגיד ממעזריטש: "Maggid of Mezeritch"
  אדמו"ר הזקן: "Alter Rebbe"
  רבי שניאור זלמן: "Rabbi Schneur Zalman"
  אדמו"ר האמצעי: "Mitteler Rebbe"
  רבי דובער: "Rabbi DovBer"
  צמח צדק: "Tzemach Tzedek"
  אדמו"ר מהר"ש: "Maharash"
  אדמו"ר הרש"ב: "Rashab"
  אדמו"ר הריי"צ: "Rayatz"
  הרבי: "the Rebbe"
  רבי מנחם מענדל: "Rabbi Menachem Mendel"

places:
  ליובאוויטש: "Lubavitch"
  ליאזנא: "Liozna"
  פטרבורג: "Petersburg"
  ארץ הקודש: "Holy Land"
  ברית המועצות: "Soviet Union"
  רוסיה הצארית: "Tsarist Russia"

terms:
  ישיבת תומכי תמימים: "Tomchei Tmimim Yeshiva"
  חסידות: "Chassidus"
  שיחה: "sicha"
  מאמר: "maamar"
  פרסום: "publication"
  התוועדות: "farbrengen"
  נשיאות: "leadership"
  בעל הילולא: "yahrzeit subject"
```

- [ ] **Step 2: Write level_overrides stub**

Create `ingest/level_overrides.yaml`:

```yaml
# Manual overrides applied in Pass 4.
# Key is the 12-char hex event_id; value is one of macro|meso|micro.
# Populate after the first Pass 4 review when specific events need re-leveling.

overrides: {}
```

- [ ] **Step 3: Commit**

```bash
git add ingest/glossary.yaml ingest/level_overrides.yaml
git commit -m "feat(ingest): seed glossary and level-overrides files"
```

---

## Task 7: Pass 1 — Consolidate (compact JSON loader)

**Files:**
- Create: `ingest/src/timeline_ingest/pass1_consolidate.py`
- Create: `ingest/tests/test_pass1_compact.py`
- Create: `ingest/tests/fixtures/compact_sample.json`

- [ ] **Step 1: Build a fixture file**

Create `ingest/tests/fixtures/compact_sample.json`:

```json
[
  {"y": 1812, "t": "נפטר אדמו\"ר הזקן", "d": "ביום כ\"ד טבת", "c": "rebbe", "s": "כ\"ד טבת"},
  {"y": 1880, "t": "נולד אדמו\"ר הריי\"צ", "d": "ב'תרמ", "c": "rebbe", "s": "י\"ב תמוז"},
  {"y": 1812, "t": "נפטר אדמו\"ר הזקן", "d": "ביום כ\"ד טבת", "c": "rebbe", "s": "כ\"ד טבת"}
]
```

- [ ] **Step 2: Write the failing test**

Create `ingest/tests/test_pass1_compact.py`:

```python
from pathlib import Path

from timeline_ingest.pass1_consolidate import load_compact_json


def test_load_compact_dedupes_and_normalizes(tmp_path: Path):
    fixture = Path(__file__).parent / "fixtures" / "compact_sample.json"
    records = load_compact_json(fixture)
    # The sample has 3 rows but two are duplicates → 2 unique.
    assert len(records) == 2
    # First record uses placeholder English title pending Pass 3 translation.
    assert records[0].title_en == ""  # cleared, will be filled in Pass 3
    assert records[0].date.y in (1812, 1880)
    assert records[0].category == "rebbe"
    ids = {r.id for r in records}
    assert len(ids) == 2
```

- [ ] **Step 3: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_pass1_compact.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 4: Implement load_compact_json**

Create `ingest/src/timeline_ingest/pass1_consolidate.py`:

```python
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
                level="micro",  # default; Pass 4 reassigns
                date=date,
                title_en="",  # filled in Pass 3
                summary_en=row.get("d", "").strip(),
                story_path=f"stories/{eid}.md",
                category=_normalize_category(row.get("c", "general")),
                sources=[EventSource(name="chabad-timeline-compact.json")],
            )
        )
    return out
```

- [ ] **Step 5: Run tests**

```bash
cd ingest && uv run pytest tests/test_pass1_compact.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ingest/src/timeline_ingest/pass1_consolidate.py ingest/tests/test_pass1_compact.py ingest/tests/fixtures/compact_sample.json
git commit -m "feat(ingest): pass1 compact-json loader with dedupe"
```

---

## Task 8: Pass 1 — comprehensive markdown loader

**Files:**
- Modify: `ingest/src/timeline_ingest/pass1_consolidate.py`
- Create: `ingest/tests/test_pass1_md.py`
- Create: `ingest/tests/fixtures/comprehensive_sample.md`

- [ ] **Step 1: Build a fixture**

Create `ingest/tests/fixtures/comprehensive_sample.md`:

```markdown
# Comprehensive Chabad History Timeline

## Events by Era

### Early Chabad (1741-1812)

- **1812:** נפטר אדמו"ר הזקן
  - _ביום כ"ד טבת תקע"ג נסתלק אדמו"ר הזקן..._

### Beit Rivkah (1880-1920)

- **1880:** נולד אדמו"ר הריי"צ
  - _בי"ב תמוז ה'תר"ם..._
```

- [ ] **Step 2: Write the failing test**

Create `ingest/tests/test_pass1_md.py`:

```python
from pathlib import Path

from timeline_ingest.pass1_consolidate import load_comprehensive_md


def test_load_comprehensive_md_parses_events():
    fixture = Path(__file__).parent / "fixtures" / "comprehensive_sample.md"
    records = load_comprehensive_md(fixture)
    assert len(records) == 2
    years = {r.date.y for r in records}
    assert years == {1812, 1880}
    assert all(r.title_en == "" for r in records)  # filled in Pass 3
    assert all(
        r.sources[0].name == "chabad-history-timeline-comprehensive.md" for r in records
    )
```

- [ ] **Step 3: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_pass1_md.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 4: Implement load_comprehensive_md**

Append to `ingest/src/timeline_ingest/pass1_consolidate.py`:

```python
import re

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
                level="micro",
                date=date,
                title_en="",
                summary_en=summary_he,
                story_path=f"stories/{eid}.md",
                category="general",
                sources=[EventSource(name="chabad-history-timeline-comprehensive.md")],
            )
        )
    return out
```

- [ ] **Step 5: Run tests**

```bash
cd ingest && uv run pytest tests/test_pass1_md.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ingest/src/timeline_ingest/pass1_consolidate.py ingest/tests/test_pass1_md.py ingest/tests/fixtures/comprehensive_sample.md
git commit -m "feat(ingest): pass1 comprehensive-md loader"
```

---

## Task 9: Pass 1 — merge + cross-source dedupe + writer

**Files:**
- Modify: `ingest/src/timeline_ingest/pass1_consolidate.py`
- Create: `ingest/tests/test_pass1_merge.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_pass1_merge.py`:

```python
import json
from pathlib import Path

from timeline_ingest.pass1_consolidate import consolidate
from timeline_ingest.config import Config, ExistingExtractions, BooksToExtract, ChabadpediaPages, PhotoSources, OutputPaths


def _cfg(tmp_path: Path, compact: Path, md: Path) -> Config:
    return Config(
        existing_extractions=ExistingExtractions(
            compact_json=compact,
            comprehensive_md=md,
            chabadpedia_kg_dir=tmp_path,
        ),
        books_to_extract=BooksToExtract(
            undaunted_dir=tmp_path,
            undaunted_chapters_glob="*.txt",
            chabad_library_dir=tmp_path,
            chabad_library_history_book_ids=[],
        ),
        chabadpedia_pages=ChabadpediaPages(dir=tmp_path),
        photos=PhotoSources(knowledge_graph_files=[]),
        output=OutputPaths(
            intermediate_dir=tmp_path / "intermediate",
            cache_dir=tmp_path / "cache",
            public_dir=tmp_path / "public",
            glossary_path=tmp_path / "g.yaml",
            level_overrides_path=tmp_path / "l.yaml",
        ),
    )


def test_consolidate_merges_sources_and_writes_output(tmp_path: Path):
    fixtures = Path(__file__).parent / "fixtures"
    cfg = _cfg(tmp_path, fixtures / "compact_sample.json", fixtures / "comprehensive_sample.md")
    out_path = consolidate(cfg)
    assert out_path == tmp_path / "intermediate" / "01_consolidated.json"
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 2
    ids = {r["id"] for r in data}
    assert len(ids) == len(data)  # globally unique
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_pass1_merge.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Implement consolidate()**

Append to `ingest/src/timeline_ingest/pass1_consolidate.py`:

```python
from timeline_ingest.config import Config


def consolidate(cfg: Config) -> Path:
    records: list[EventRecord] = []
    records.extend(load_compact_json(cfg.existing_extractions.compact_json))
    records.extend(load_comprehensive_md(cfg.existing_extractions.comprehensive_md))

    seen: dict[str, EventRecord] = {}
    for r in records:
        if r.id not in seen:
            seen[r.id] = r
        else:
            # Merge sources lists on duplicate
            existing = seen[r.id]
            existing.sources.extend(r.sources)

    out_dir = cfg.output.intermediate_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "01_consolidated.json"
    payload = [r.model_dump(mode="json") for r in seen.values()]
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
```

- [ ] **Step 4: Run tests**

```bash
cd ingest && uv run pytest tests/test_pass1_merge.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/src/timeline_ingest/pass1_consolidate.py ingest/tests/test_pass1_merge.py
git commit -m "feat(ingest): pass1 cross-source merge + writer"
```

---

## Task 10: CLI entrypoint (pass1 wired up)

**Files:**
- Create: `ingest/src/timeline_ingest/__main__.py`
- Create: `ingest/src/timeline_ingest/cli.py`
- Create: `ingest/tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_cli.py`:

```python
import subprocess
import sys
from pathlib import Path


def test_cli_lists_known_passes():
    result = subprocess.run(
        [sys.executable, "-m", "timeline_ingest", "--help"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0
    assert "pass1" in result.stdout
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_cli.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Implement CLI**

Create `ingest/src/timeline_ingest/cli.py`:

```python
"""Command-line entrypoint: `python -m timeline_ingest <pass>`."""

import argparse
import sys
from pathlib import Path

from timeline_ingest.config import load_config
from timeline_ingest.pass1_consolidate import consolidate

PASSES = {
    "pass1": consolidate,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="timeline_ingest")
    parser.add_argument(
        "pass_name",
        choices=sorted(PASSES.keys()),
        help="which pass to run",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("sources.yaml"),
        help="path to sources.yaml",
    )
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    func = PASSES[args.pass_name]
    out = func(cfg)
    print(f"OK → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Create `ingest/src/timeline_ingest/__main__.py`:

```python
from timeline_ingest.cli import main

raise SystemExit(main())
```

- [ ] **Step 4: Run tests**

```bash
cd ingest && uv run pytest tests/test_cli.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/src/timeline_ingest/cli.py ingest/src/timeline_ingest/__main__.py ingest/tests/test_cli.py
git commit -m "feat(ingest): cli entrypoint wired to pass1"
```

---

## Task 11: Smoke-test pass1 against real data

**Files:**
- (no new files; runs the CLI against `sources.yaml`)

- [ ] **Step 1: Execute pass1**

Run from `ingest/`:

```bash
make pass1
```

Expected: `OK → intermediate/01_consolidated.json` and the file contains a few thousand records (~3.5–6k unique after dedupe; KG event mining is deferred to v1.5, so this pass only sources from the compact JSON and comprehensive markdown).

- [ ] **Step 2: Validate the output is well-formed**

Run:

```bash
uv run python -c "
import json
from timeline_ingest.schema import EventRecord
data = json.load(open('intermediate/01_consolidated.json'))
print(f'count: {len(data)}')
assert len(data) >= 3000, f'too few records ({len(data)}); loaders likely silently dropping rows'
for r in data:
    EventRecord.model_validate(r)  # raises on schema mismatch
# Pass 1 leaves title_en empty (filled in Pass 3); just sanity-check summaries exist.
non_empty_summary = sum(1 for r in data if r['summary_en'])
print(f'records with non-empty summary: {non_empty_summary}')
assert non_empty_summary >= 1000, 'too few records carried summary text through'
print('all records validate')
"
```

Expected: count >= 3,000; at least 1,000 records have a non-empty summary; `all records validate`. If either assertion fires, one of the loaders is silently dropping rows — debug before continuing.

- [ ] **Step 3: Commit no code; record the artifact size for future reference**

```bash
git status  # should be clean (intermediate/ is gitignored)
ls -lh ingest/intermediate/01_consolidated.json
```

(No commit — pass1 ran successfully against real data; the intermediate file is gitignored.)

---

## Task 12: LLM client wrapper with caching and concurrency

**Files:**
- Create: `ingest/src/timeline_ingest/llm.py`
- Create: `ingest/tests/test_llm.py`

@superpowers:claude-api — follow that skill's guidance on prompt caching and model selection.

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_llm.py`:

```python
import asyncio
from pathlib import Path

from timeline_ingest.llm import LLMClient


async def test_cache_hit_skips_call(tmp_path: Path, monkeypatch):
    calls = {"n": 0}

    async def fake_call(client, *, system, user, model):
        calls["n"] += 1
        return f"response-{calls['n']}"

    client = LLMClient(cache_dir=tmp_path, _call=fake_call)
    resp1 = await client.complete(system="sys", user="hello", model="claude-haiku-4-5-20251001")
    resp2 = await client.complete(system="sys", user="hello", model="claude-haiku-4-5-20251001")
    assert resp1 == resp2 == "response-1"
    assert calls["n"] == 1  # second call hit cache


async def test_different_payload_misses_cache(tmp_path: Path):
    calls = {"n": 0}

    async def fake_call(client, *, system, user, model):
        calls["n"] += 1
        return f"response-{calls['n']}"

    client = LLMClient(cache_dir=tmp_path, _call=fake_call)
    await client.complete(system="sys", user="hello", model="m")
    await client.complete(system="sys", user="hi", model="m")
    assert calls["n"] == 2
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_llm.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Implement LLMClient**

Create `ingest/src/timeline_ingest/llm.py`:

```python
"""Anthropic client wrapper: per-call disk cache + concurrency cap + retries.

Caching strategy: SHA256(system + user + model) → cache key. Hits skip the API.
Misses call the API, then write the response under cache_dir/<key>.txt.

Concurrency: bounded via an asyncio.Semaphore (default 20).
"""

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from pathlib import Path

import anthropic


CallFn = Callable[["LLMClient"], Awaitable[str]]


class LLMClient:
    def __init__(
        self,
        cache_dir: Path,
        *,
        max_concurrent: int = 20,
        _call: Callable | None = None,
    ) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._sem = asyncio.Semaphore(max_concurrent)
        self._call = _call or _default_call
        self._anthropic = anthropic.AsyncAnthropic() if _call is None else None

    def _key(self, *, system: str, user: str, model: str) -> Path:
        h = hashlib.sha256(f"{model}|{system}|{user}".encode("utf-8")).hexdigest()
        return self.cache_dir / f"{h}.txt"

    async def complete(self, *, system: str, user: str, model: str) -> str:
        cache_path = self._key(system=system, user=user, model=model)
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8")
        async with self._sem:
            response = await self._call(self, system=system, user=user, model=model)
        cache_path.write_text(response, encoding="utf-8")
        return response


async def _default_call(client: LLMClient, *, system: str, user: str, model: str) -> str:
    assert client._anthropic is not None
    msg = await client._anthropic.messages.create(
        model=model,
        max_tokens=4096,
        system=[
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}},
        ],
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")
```

- [ ] **Step 4: Run tests**

```bash
cd ingest && uv run pytest tests/test_llm.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/src/timeline_ingest/llm.py ingest/tests/test_llm.py
git commit -m "feat(ingest): LLM client wrapper with disk cache + concurrency cap"
```

---

## Task 13: Pass 2 — chunker for books

**Files:**
- Create: `ingest/src/timeline_ingest/chunking.py`
- Create: `ingest/tests/test_chunking.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_chunking.py`:

```python
from timeline_ingest.chunking import chunk_by_chars


def test_chunk_short_text_returns_single_chunk():
    chunks = list(chunk_by_chars("hello world", max_chars=100))
    assert chunks == ["hello world"]


def test_chunk_long_text_splits_on_paragraph_boundary():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = list(chunk_by_chars(text, max_chars=20))
    assert len(chunks) >= 2
    for c in chunks:
        assert c.strip()


def test_chunk_respects_max_chars_soft_limit():
    text = ("X" * 50 + "\n\n") * 10
    chunks = list(chunk_by_chars(text, max_chars=100))
    for c in chunks:
        assert len(c) <= 200  # allow ~2x slack to avoid mid-paragraph cuts
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_chunking.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Implement chunker**

Create `ingest/src/timeline_ingest/chunking.py`:

```python
"""Split long texts into ~max_chars chunks at paragraph boundaries."""

from collections.abc import Iterator


def chunk_by_chars(text: str, *, max_chars: int = 24000) -> Iterator[str]:
    """Yield chunks of approximately max_chars, splitting at \\n\\n boundaries."""
    paragraphs = text.split("\n\n")
    buf: list[str] = []
    buf_len = 0
    for p in paragraphs:
        if buf and buf_len + len(p) > max_chars:
            yield "\n\n".join(buf)
            buf = [p]
            buf_len = len(p)
        else:
            buf.append(p)
            buf_len += len(p) + 2
    if buf:
        yield "\n\n".join(buf)
```

- [ ] **Step 4: Run tests**

```bash
cd ingest && uv run pytest tests/test_chunking.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/src/timeline_ingest/chunking.py ingest/tests/test_chunking.py
git commit -m "feat(ingest): paragraph-boundary chunker"
```

---

## Task 14: Pass 2 — extraction prompt + JSON parser

**Files:**
- Create: `ingest/src/timeline_ingest/pass2_extract.py`
- Create: `ingest/tests/test_pass2_parse.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_pass2_parse.py`:

```python
from timeline_ingest.pass2_extract import parse_extraction_response, EXTRACTION_SYSTEM_PROMPT


def test_parse_extracts_valid_events():
    response = """Here are the events:
[
  {"title": "Alter Rebbe passes away", "year": 1812, "month": 12, "day": null, "category": "rebbe", "summary": "Passing in Piena.", "story": "On 24 Tevet 5573..."},
  {"title": "Tanya first print", "year": 1797, "month": null, "day": null, "category": "publication", "summary": "First edition.", "story": "Slavita printing."}
]
"""
    events = parse_extraction_response(response)
    assert len(events) == 2
    assert events[0]["title"] == "Alter Rebbe passes away"
    assert events[0]["year"] == 1812
    assert events[0]["month"] == 12


def test_parse_handles_empty_list():
    assert parse_extraction_response("[]") == []


def test_parse_raises_on_garbage():
    import pytest
    with pytest.raises(ValueError):
        parse_extraction_response("This is not JSON at all.")


def test_extraction_prompt_mentions_required_fields():
    assert "title" in EXTRACTION_SYSTEM_PROMPT
    assert "year" in EXTRACTION_SYSTEM_PROMPT
    assert "category" in EXTRACTION_SYSTEM_PROMPT
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_pass2_parse.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Implement parser and prompt**

Create `ingest/src/timeline_ingest/pass2_extract.py`:

```python
"""Pass 2 — LLM extraction from books to dated events."""

import json
import re

EXTRACTION_SYSTEM_PROMPT = """You extract dated historical events from Chabad history texts.

For every clearly dated event in the input, output one JSON object with these fields:
- title: ≤ 90 chars, in English (translate from Hebrew/Yiddish if needed)
- year: integer Gregorian year (required)
- month: integer 1–12 or null
- day: integer 1–31 or null
- category: one of rebbe | publication | conflict | education | organization | location | calendar | general
- summary: one English sentence
- story: 2–4 English sentences with context

Return ONLY a JSON array (possibly empty). No commentary, no markdown fences."""


_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*\]")


def parse_extraction_response(text: str) -> list[dict]:
    m = _JSON_ARRAY_RE.search(text)
    if not m:
        raise ValueError("no JSON array found in response")
    return json.loads(m.group(0))
```

- [ ] **Step 4: Run tests**

```bash
cd ingest && uv run pytest tests/test_pass2_parse.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/src/timeline_ingest/pass2_extract.py ingest/tests/test_pass2_parse.py
git commit -m "feat(ingest): pass2 extraction prompt + JSON parser"
```

---

## Task 15: Pass 2 — book ingestion driver

**Files:**
- Modify: `ingest/src/timeline_ingest/pass2_extract.py`
- Create: `ingest/tests/test_pass2_driver.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_pass2_driver.py`:

```python
import asyncio
from pathlib import Path

from timeline_ingest.llm import LLMClient
from timeline_ingest.pass2_extract import extract_book


async def fake_call(client, *, system, user, model):
    # Return one event regardless of input
    return '[{"title": "Test event", "year": 1812, "month": null, "day": null, "category": "rebbe", "summary": "s", "story": "story body"}]'


async def test_extract_book_returns_records(tmp_path: Path):
    book_path = tmp_path / "book.txt"
    book_path.write_text("Some long text.\n\nAnother paragraph.", encoding="utf-8")
    client = LLMClient(cache_dir=tmp_path / "cache", _call=fake_call)
    records = await extract_book(client, book_path, source_name="Book")
    assert len(records) >= 1
    assert records[0].title_en == "Test event"
    assert records[0].date.y == 1812
    assert records[0].sources[0].name == "Book"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_pass2_driver.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Implement extract_book**

Append to `ingest/src/timeline_ingest/pass2_extract.py`:

```python
import asyncio
from pathlib import Path

from timeline_ingest.chunking import chunk_by_chars
from timeline_ingest.dates import is_supported_year
from timeline_ingest.ids import event_id
from timeline_ingest.llm import LLMClient
from timeline_ingest.schema import EventCategory, EventDate, EventRecord, EventSource

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
    cat = row.get("category", "general")
    if cat not in _VALID_CATEGORIES:
        cat = "general"
    precision = "day" if (month and day) else ("month" if month else "year")
    date = EventDate(y=year, m=month, d=day, precision=precision)
    eid = event_id(title, year=year, month=month, day=day)
    story_body = (row.get("story") or "").strip() or None
    return EventRecord(
        id=eid,
        level="micro",
        date=date,
        title_en=title,
        summary_en=row.get("summary", "").strip(),
        story_body=story_body,
        story_path=f"stories/{eid}.md",
        category=cat,
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
```

- [ ] **Step 4: Run tests**

```bash
cd ingest && uv run pytest tests/test_pass2_driver.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/src/timeline_ingest/pass2_extract.py ingest/tests/test_pass2_driver.py
git commit -m "feat(ingest): pass2 single-book extraction driver"
```

---

## Task 16: Pass 2 — top-level extract() across all books AND Chabadpedia pages

**Files:**
- Modify: `ingest/src/timeline_ingest/pass2_extract.py`
- Modify: `ingest/src/timeline_ingest/cli.py`
- Create: `ingest/tests/test_pass2_all.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_pass2_all.py`:

```python
import asyncio
import json
from pathlib import Path

from timeline_ingest.pass2_extract import run_pass2
from timeline_ingest.config import Config, ExistingExtractions, BooksToExtract, ChabadpediaPages, PhotoSources, OutputPaths


async def fake_call(client, *, system, user, model):
    # Vary title per chunk so events from different sources don't dedupe to the same id.
    suffix = abs(hash(user)) % 10_000
    return (
        f'[{{"title": "Fake event {suffix}", "year": 1800, "month": null, "day": null, '
        f'"category": "general", "summary": "x", "story": "y"}}]'
    )


def _cfg(tmp_path: Path) -> Config:
    book = tmp_path / "books" / "u_chapter1.txt"
    book.parent.mkdir(parents=True, exist_ok=True)
    book.write_text("some chapter text", encoding="utf-8")

    pages_dir = tmp_path / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / "Alter_Rebbe.txt").write_text("Some bio text.", encoding="utf-8")

    return Config(
        existing_extractions=ExistingExtractions(
            compact_json=tmp_path / "x.json",
            comprehensive_md=tmp_path / "y.md",
            chabadpedia_kg_dir=tmp_path,
        ),
        books_to_extract=BooksToExtract(
            undaunted_dir=tmp_path / "books",
            undaunted_chapters_glob="u_chapter*.txt",
            chabad_library_dir=tmp_path / "lib",
            chabad_library_history_book_ids=[],
        ),
        chabadpedia_pages=ChabadpediaPages(dir=pages_dir),
        photos=PhotoSources(knowledge_graph_files=[]),
        output=OutputPaths(
            intermediate_dir=tmp_path / "intermediate",
            cache_dir=tmp_path / "cache",
            public_dir=tmp_path / "public",
            glossary_path=tmp_path / "g.yaml",
            level_overrides_path=tmp_path / "l.yaml",
        ),
    )


async def test_run_pass2_writes_extracted(tmp_path: Path):
    cfg = _cfg(tmp_path)
    out = await run_pass2(cfg, _call_override=fake_call)
    assert out == tmp_path / "intermediate" / "02_extracted.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    # Both Undaunted chapter AND Chabadpedia page should produce records.
    sources_seen = {s["name"] for rec in data for s in rec["sources"]}
    assert any(s == "Undaunted" for s in sources_seen)
    assert any(s.startswith("Chabadpedia/") for s in sources_seen)
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_pass2_all.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Implement run_pass2**

Append to `ingest/src/timeline_ingest/pass2_extract.py`:

```python
from timeline_ingest.config import Config


async def run_pass2(cfg: Config, *, _call_override=None) -> Path:
    """Run extraction across all configured sources.

    On duplicate event_id (same event surfacing from multiple sources), we MERGE
    the sources lists instead of dropping the second occurrence — preserves
    provenance and matches Pass 1's consolidate() behavior.
    """
    client = LLMClient(cache_dir=cfg.output.cache_dir, _call=_call_override)
    records_by_id: dict[str, EventRecord] = {}

    def _ingest(recs: list[EventRecord]) -> None:
        for r in recs:
            if r.id in records_by_id:
                records_by_id[r.id].sources.extend(r.sources)
            else:
                records_by_id[r.id] = r

    # Undaunted chapters
    chapter_paths = sorted(cfg.books_to_extract.undaunted_dir.glob(
        cfg.books_to_extract.undaunted_chapters_glob
    ))
    for ch in chapter_paths:
        _ingest(await extract_book(client, ch, source_name="Undaunted"))

    # Chabad Library history books
    for book_id in cfg.books_to_extract.chabad_library_history_book_ids:
        candidates = list(cfg.books_to_extract.chabad_library_dir.glob(f"*{book_id}*"))
        if not candidates:
            continue
        book_path = candidates[0]
        _ingest(await extract_book(client, book_path, source_name=f"Chabad Library/{book_id}"))

    # Chabadpedia biographical pages
    pages_dir = cfg.chabadpedia_pages.dir
    if pages_dir.exists():
        for page_path in sorted(pages_dir.glob("*.txt")) + sorted(pages_dir.glob("*.json")):
            _ingest(await extract_book(
                client, page_path, source_name=f"Chabadpedia/{page_path.stem}"
            ))

    out_dir = cfg.output.intermediate_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "02_extracted.json"
    payload = [r.model_dump(mode="json") for r in records_by_id.values()]
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
```

- [ ] **Step 4: Wire pass2 into CLI**

Modify `ingest/src/timeline_ingest/cli.py` — replace the PASSES dict and import area:

```python
import asyncio
from timeline_ingest.config import load_config
from timeline_ingest.pass1_consolidate import consolidate
from timeline_ingest.pass2_extract import run_pass2


def _pass2_sync(cfg):
    return asyncio.run(run_pass2(cfg))


PASSES = {
    "pass1": consolidate,
    "pass2": _pass2_sync,
}
```

- [ ] **Step 5: Run tests**

```bash
cd ingest && uv run pytest tests/test_pass2_all.py tests/test_cli.py -v && cd ..
```

Expected: PASS for both.

- [ ] **Step 6: Commit**

```bash
git add ingest/src/timeline_ingest/pass2_extract.py ingest/src/timeline_ingest/cli.py ingest/tests/test_pass2_all.py
git commit -m "feat(ingest): pass2 top-level runner across all books"
```

---

## Task 17: Pass 3 — translation prompt + driver

**Files:**
- Create: `ingest/src/timeline_ingest/pass3_translate.py`
- Create: `ingest/tests/test_pass3.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_pass3.py`:

```python
import asyncio
import json
from pathlib import Path

from timeline_ingest.pass3_translate import translate_records, _format_glossary_block, TRANSLATION_SYSTEM_PROMPT
from timeline_ingest.schema import EventRecord, EventDate, EventSource


async def fake_call(client, *, system, user, model):
    return '[{"id": "abc", "title_en": "Alter Rebbe passes away", "summary_en": "Passing in 1812."}]'


def _rec() -> EventRecord:
    return EventRecord(
        id="abc",
        level="micro",
        date=EventDate(y=1812, precision="year"),
        title_en="",
        summary_en="נפטר אדמו\"ר הזקן",
        story_path="stories/abc.md",
        category="rebbe",
        sources=[EventSource(name="x")],
    )


def test_glossary_block_format():
    block = _format_glossary_block({"rebbes": {"אדמו\"ר הזקן": "Alter Rebbe"}})
    assert "Alter Rebbe" in block
    assert "אדמו" in block


def test_translation_prompt_mentions_glossary_lock():
    assert "glossary" in TRANSLATION_SYSTEM_PROMPT.lower()


async def test_translate_fills_english_fields(tmp_path: Path):
    from timeline_ingest.llm import LLMClient
    client = LLMClient(cache_dir=tmp_path, _call=fake_call)
    records = [_rec()]
    glossary = {"rebbes": {"אדמו\"ר הזקן": "Alter Rebbe"}}
    translated = await translate_records(client, records, glossary=glossary)
    assert translated[0].title_en == "Alter Rebbe passes away"
    assert translated[0].summary_en == "Passing in 1812."
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_pass3.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Implement translation**

Create `ingest/src/timeline_ingest/pass3_translate.py`:

```python
"""Pass 3 — translate Hebrew title/summary to English with glossary lock."""

import asyncio
import json
from collections.abc import Iterable
from pathlib import Path

import yaml

from timeline_ingest.config import Config
from timeline_ingest.llm import LLMClient
from timeline_ingest.schema import EventRecord

TRANSLATION_SYSTEM_PROMPT = """You translate Hebrew/Yiddish event titles and summaries to English.

CRITICAL: A glossary follows. Use the EXACT English rendering for every term in the glossary —
do not paraphrase, do not vary capitalization.

Output ONLY a JSON array, each element: {"id": "...", "title_en": "...", "summary_en": "..."}.
No commentary."""


def _format_glossary_block(glossary: dict) -> str:
    lines = []
    for cat, terms in glossary.items():
        lines.append(f"[{cat}]")
        for he, en in terms.items():
            lines.append(f"  {he}  →  {en}")
    return "\n".join(lines)


async def translate_records(
    client: LLMClient,
    records: Iterable[EventRecord],
    *,
    glossary: dict,
    model: str = "claude-haiku-4-5-20251001",
    batch_size: int = 25,
) -> list[EventRecord]:
    rec_list = list(records)
    glossary_block = _format_glossary_block(glossary)
    system = TRANSLATION_SYSTEM_PROMPT + "\n\nGlossary:\n" + glossary_block

    out: list[EventRecord] = []
    for i in range(0, len(rec_list), batch_size):
        batch = rec_list[i : i + batch_size]
        payload = [
            {
                "id": r.id,
                "title_he": r.title_en or r.summary_en[:50],
                "summary_he": r.summary_en,
            }
            for r in batch
            if not r.title_en
        ]
        if not payload:
            out.extend(batch)
            continue
        user = json.dumps(payload, ensure_ascii=False)
        resp = await client.complete(system=system, user=user, model=model)
        try:
            translated = json.loads(resp)
        except json.JSONDecodeError:
            out.extend(batch)
            continue
        by_id = {t["id"]: t for t in translated if "id" in t}
        for r in batch:
            t = by_id.get(r.id)
            if t:
                r = r.model_copy(update={
                    "title_en": t.get("title_en", r.title_en),
                    "summary_en": t.get("summary_en", r.summary_en),
                })
            out.append(r)
    return out


async def run_pass3(cfg: Config, *, _call_override=None) -> Path:
    # Merge pass1 + pass2 outputs
    p1 = cfg.output.intermediate_dir / "01_consolidated.json"
    p2 = cfg.output.intermediate_dir / "02_extracted.json"

    records: dict[str, EventRecord] = {}
    for path in (p1, p2):
        if not path.exists():
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        for row in rows:
            r = EventRecord.model_validate(row)
            if r.id in records:
                records[r.id].sources.extend(r.sources)
            else:
                records[r.id] = r

    glossary = yaml.safe_load(cfg.output.glossary_path.read_text(encoding="utf-8")) or {}
    client = LLMClient(cache_dir=cfg.output.cache_dir, _call=_call_override)
    translated = await translate_records(client, records.values(), glossary=glossary)

    out_path = cfg.output.intermediate_dir / "03_translated.json"
    out_path.write_text(
        json.dumps([r.model_dump(mode="json") for r in translated], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path
```

- [ ] **Step 4: Wire pass3 into CLI**

Modify `ingest/src/timeline_ingest/cli.py` — add pass3:

```python
from timeline_ingest.pass3_translate import run_pass3


def _pass3_sync(cfg):
    return asyncio.run(run_pass3(cfg))


PASSES = {
    "pass1": consolidate,
    "pass2": _pass2_sync,
    "pass3": _pass3_sync,
}
```

- [ ] **Step 5: Run tests**

```bash
cd ingest && uv run pytest tests/test_pass3.py tests/test_cli.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ingest/src/timeline_ingest/pass3_translate.py ingest/src/timeline_ingest/cli.py ingest/tests/test_pass3.py
git commit -m "feat(ingest): pass3 batch translation with glossary lock"
```

---

## Task 18: Pass 4 — level heuristic + manual overrides

**Files:**
- Create: `ingest/src/timeline_ingest/pass4_enrich.py`
- Create: `ingest/tests/test_pass4_level.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_pass4_level.py`:

```python
from timeline_ingest.pass4_enrich import assign_level, apply_overrides
from timeline_ingest.schema import EventRecord, EventDate, EventSource


def _r(title, category, sources=None):
    return EventRecord(
        id="x",
        level="micro",
        date=EventDate(y=1812, precision="year"),
        title_en=title,
        summary_en="",
        story_path="stories/x.md",
        category=category,
        sources=sources or [EventSource(name="t")],
    )


def test_macro_for_rebbe_birth():
    r = _r("Alter Rebbe born", "rebbe")
    assert assign_level(r) == "macro"


def test_macro_for_tanya_publication():
    r = _r("Tanya first printed", "publication")
    assert assign_level(r) == "macro"


def test_meso_for_yeshiva_founding():
    r = _r("Tomchei Tmimim founded in Lubavitch", "education")
    assert assign_level(r) == "meso"


def test_micro_for_random_letter():
    r = _r("Letter from Rebbe to a chossid in Paris", "general")
    assert assign_level(r) == "micro"


def test_apply_overrides_overrides_heuristic():
    r = _r("Letter from Rebbe to a chossid", "general")
    out = apply_overrides([r], {"x": "macro"})
    assert out[0].level == "macro"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_pass4_level.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Implement level logic**

Create `ingest/src/timeline_ingest/pass4_enrich.py`:

```python
"""Pass 4 — assign macro/meso/micro level, attach photos, build related[]."""

import re
from collections.abc import Iterable

from timeline_ingest.schema import EventLevel, EventRecord

_MACRO_KEYWORDS = [
    r"\bborn\b",
    r"\bpasses away\b",
    r"\bpassing\b",
    r"\bbecame? .* rebbe\b",
    r"\bbecomes? .* rebbe\b",
    r"\barrest(ed)?\b",
    r"\bexile(d)?\b",
    r"\bredemption\b",
    r"\btanya\b",
    r"\blikkutei torah\b",
    r"\btorah or\b",
    r"\btomchei tmimim\b",
]
_MESO_KEYWORDS = [
    r"\byeshiva\b",
    r"\bfounded\b",
    r"\bestablished\b",
    r"\bpogrom\b",
    r"\bwar\b",
    r"\bmaamar\b",
    r"\bsicha\b",
    r"\bemigration\b",
    r"\bfarbrengen\b",
]

_MACRO_RE = re.compile("|".join(_MACRO_KEYWORDS), re.IGNORECASE)
_MESO_RE = re.compile("|".join(_MESO_KEYWORDS), re.IGNORECASE)


def assign_level(rec: EventRecord) -> EventLevel:
    text = f"{rec.title_en} {rec.summary_en}".lower()
    if _MACRO_RE.search(text):
        return "macro"
    if _MESO_RE.search(text):
        return "meso"
    if rec.category in {"rebbe"} and any(
        kw in rec.title_en.lower() for kw in ["born", "passing", "becomes"]
    ):
        return "macro"
    return "micro"


def apply_overrides(
    records: Iterable[EventRecord],
    overrides: dict[str, str],
) -> list[EventRecord]:
    out: list[EventRecord] = []
    for r in records:
        level = overrides.get(r.id) or assign_level(r)
        out.append(r.model_copy(update={"level": level}))
    return out
```

- [ ] **Step 4: Run tests**

```bash
cd ingest && uv run pytest tests/test_pass4_level.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/src/timeline_ingest/pass4_enrich.py ingest/tests/test_pass4_level.py
git commit -m "feat(ingest): pass4 level heuristic + manual overrides"
```

---

## Task 19: Pass 4 — photo attachment from knowledge graphs

**Files:**
- Modify: `ingest/src/timeline_ingest/pass4_enrich.py`
- Create: `ingest/tests/test_pass4_photos.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_pass4_photos.py`:

```python
from timeline_ingest.pass4_enrich import attach_photos, _build_entity_index
from timeline_ingest.schema import EventRecord, EventDate, EventSource


def test_build_entity_index_extracts_image_urls():
    kg = {
        "Alter Rebbe": {"image": "https://example.org/alter.jpg", "credit": "Chabadpedia"},
        "Tanya": {"image": "https://example.org/tanya.jpg"},
    }
    idx = _build_entity_index(kg)
    assert "alter rebbe" in idx
    assert idx["alter rebbe"].url == "https://example.org/alter.jpg"


def test_attach_photos_matches_by_title_token():
    rec = EventRecord(
        id="x", level="macro",
        date=EventDate(y=1812, precision="year"),
        title_en="Alter Rebbe passes away",
        summary_en="",
        story_path="stories/x.md",
        category="rebbe",
        sources=[EventSource(name="t")],
    )
    idx = {
        "alter rebbe": __import__("timeline_ingest.schema", fromlist=["EventPhoto"]).EventPhoto(
            url="https://x/a.jpg", credit="Chabadpedia"
        )
    }
    out = attach_photos([rec], entity_index=idx)
    assert out[0].photo is not None
    assert out[0].photo.url == "https://x/a.jpg"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_pass4_photos.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Implement photo attachment**

Append to `ingest/src/timeline_ingest/pass4_enrich.py`:

```python
from timeline_ingest.schema import EventPhoto


def _build_entity_index(kg: dict) -> dict[str, EventPhoto]:
    out: dict[str, EventPhoto] = {}
    for name, entity in kg.items():
        if not isinstance(entity, dict):
            continue
        url = entity.get("image")
        if not url:
            continue
        out[name.lower()] = EventPhoto(
            url=url,
            credit=entity.get("credit", "Chabadpedia"),
            caption=entity.get("caption"),
        )
    return out


_TOKEN_RE = re.compile(r"[\w\u0590-\u05FF]+", re.UNICODE)


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text)}


def attach_photos(
    records: Iterable[EventRecord],
    *,
    entity_index: dict[str, EventPhoto],
) -> list[EventRecord]:
    """Match entity → event by full-token overlap on title+summary.

    Substring matching would over-fire (e.g. "Tanya" inside "Tannaya"); we require
    every token of the entity name to appear as a whole token in the event text.
    """
    out: list[EventRecord] = []
    entity_tokens = {name: _tokenize(name) for name in entity_index}
    for r in records:
        if r.photo is not None:
            out.append(r)
            continue
        event_tokens = _tokenize(f"{r.title_en} {r.summary_en}")
        photo: EventPhoto | None = None
        for entity_name, e_toks in entity_tokens.items():
            if e_toks and e_toks.issubset(event_tokens):
                photo = entity_index[entity_name]
                break
        out.append(r.model_copy(update={"photo": photo}))
    return out
```

- [ ] **Step 4: Run tests**

```bash
cd ingest && uv run pytest tests/test_pass4_photos.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/src/timeline_ingest/pass4_enrich.py ingest/tests/test_pass4_photos.py
git commit -m "feat(ingest): pass4 photo attachment from KG entity index"
```

---

## Task 20: Pass 4 — related[] cross-references

**Files:**
- Modify: `ingest/src/timeline_ingest/pass4_enrich.py`
- Create: `ingest/tests/test_pass4_related.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_pass4_related.py`:

```python
from timeline_ingest.pass4_enrich import build_related
from timeline_ingest.schema import EventRecord, EventDate, EventSource


def _r(id, y, title):
    return EventRecord(
        id=id, level="micro",
        date=EventDate(y=y, precision="year"),
        title_en=title, summary_en="",
        story_path=f"stories/{id}.md",
        category="general",
        sources=[EventSource(name="t")],
    )


def test_related_links_events_within_window():
    recs = [
        _r("a", 1812, "Alter Rebbe passes away"),
        _r("b", 1813, "Mitteler Rebbe becomes leader after Alter Rebbe"),
        _r("c", 1900, "Unrelated event in 1900"),
    ]
    out = build_related(recs, window=20)
    rel_a = next(r.related for r in out if r.id == "a")
    assert "b" in rel_a
    assert "c" not in rel_a


def test_related_excludes_self():
    recs = [_r("a", 1812, "Alter Rebbe passes")]
    out = build_related(recs, window=20)
    assert "a" not in out[0].related
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_pass4_related.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Implement build_related**

Append to `ingest/src/timeline_ingest/pass4_enrich.py`:

```python
def _tokens(rec: EventRecord) -> set[str]:
    text = f"{rec.title_en} {rec.summary_en}".lower()
    return {t for t in re.findall(r"[a-z]{4,}", text)}


def build_related(records: list[EventRecord], *, window: int = 20, top_k: int = 5) -> list[EventRecord]:
    tokens_by_id: dict[str, set[str]] = {r.id: _tokens(r) for r in records}
    out: list[EventRecord] = []
    for r in records:
        candidates: list[tuple[float, str]] = []
        for other in records:
            if other.id == r.id:
                continue
            if abs(other.date.y - r.date.y) > window:
                continue
            t1 = tokens_by_id[r.id]
            t2 = tokens_by_id[other.id]
            if not t1 or not t2:
                continue
            jaccard = len(t1 & t2) / len(t1 | t2)
            if jaccard > 0.1:
                candidates.append((jaccard, other.id))
        candidates.sort(reverse=True)
        related_ids = [oid for _, oid in candidates[:top_k]]
        out.append(r.model_copy(update={"related": related_ids}))
    return out
```

- [ ] **Step 4: Run tests**

```bash
cd ingest && uv run pytest tests/test_pass4_related.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/src/timeline_ingest/pass4_enrich.py ingest/tests/test_pass4_related.py
git commit -m "feat(ingest): pass4 related[] via jaccard within time window"
```

---

## Task 21: Pass 4 — top-level run_pass4 + CLI wire-up

**Files:**
- Modify: `ingest/src/timeline_ingest/pass4_enrich.py`
- Modify: `ingest/src/timeline_ingest/cli.py`
- Create: `ingest/tests/test_pass4_all.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_pass4_all.py`:

```python
import json
from pathlib import Path

from timeline_ingest.pass4_enrich import run_pass4
from timeline_ingest.config import Config, ExistingExtractions, BooksToExtract, ChabadpediaPages, PhotoSources, OutputPaths
from timeline_ingest.schema import EventRecord, EventDate, EventSource


def _cfg(tmp_path: Path) -> Config:
    return Config(
        existing_extractions=ExistingExtractions(
            compact_json=tmp_path / "x", comprehensive_md=tmp_path / "y", chabadpedia_kg_dir=tmp_path),
        books_to_extract=BooksToExtract(
            undaunted_dir=tmp_path, undaunted_chapters_glob="*.txt",
            chabad_library_dir=tmp_path, chabad_library_history_book_ids=[]),
        chabadpedia_pages=ChabadpediaPages(dir=tmp_path),
        photos=PhotoSources(knowledge_graph_files=[]),
        output=OutputPaths(
            intermediate_dir=tmp_path / "intermediate", cache_dir=tmp_path / "cache",
            public_dir=tmp_path / "public", glossary_path=tmp_path / "g.yaml",
            level_overrides_path=tmp_path / "l.yaml"),
    )


def test_run_pass4_emits_enriched(tmp_path: Path):
    cfg = _cfg(tmp_path)
    cfg.output.intermediate_dir.mkdir(parents=True)
    rec = EventRecord(
        id="abc", level="micro",
        date=EventDate(y=1812, precision="year"),
        title_en="Alter Rebbe passes away", summary_en="",
        story_path="stories/abc.md", category="rebbe",
        sources=[EventSource(name="t")],
    )
    p3 = cfg.output.intermediate_dir / "03_translated.json"
    p3.write_text(json.dumps([rec.model_dump(mode="json")]), encoding="utf-8")
    cfg.output.level_overrides_path.write_text("overrides: {}\n", encoding="utf-8")

    out = run_pass4(cfg)
    assert out == cfg.output.intermediate_dir / "04_enriched.json"
    data = json.loads(out.read_text())
    assert data[0]["level"] == "macro"  # heuristic should fire on "passes away"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_pass4_all.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Implement run_pass4**

Append to `ingest/src/timeline_ingest/pass4_enrich.py`:

```python
import json
from pathlib import Path

import yaml

from timeline_ingest.config import Config


def run_pass4(cfg: Config) -> Path:
    p3 = cfg.output.intermediate_dir / "03_translated.json"
    rows = json.loads(p3.read_text(encoding="utf-8"))
    records = [EventRecord.model_validate(r) for r in rows]

    overrides_doc = yaml.safe_load(cfg.output.level_overrides_path.read_text(encoding="utf-8")) or {}
    overrides = overrides_doc.get("overrides", {})

    records = apply_overrides(records, overrides)

    # Build entity index from all KG files
    entity_index: dict[str, EventPhoto] = {}
    for entry in cfg.photos.knowledge_graph_files:
        for _, path in entry.items():
            if not path.exists():
                continue
            kg = json.loads(path.read_text(encoding="utf-8"))
            entity_index.update(_build_entity_index(kg))

    records = attach_photos(records, entity_index=entity_index)
    records = build_related(records, window=20)

    out_path = cfg.output.intermediate_dir / "04_enriched.json"
    out_path.write_text(
        json.dumps([r.model_dump(mode="json") for r in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path
```

- [ ] **Step 4: Wire into CLI**

Add to `ingest/src/timeline_ingest/cli.py`:

```python
from timeline_ingest.pass4_enrich import run_pass4

PASSES = {
    "pass1": consolidate,
    "pass2": _pass2_sync,
    "pass3": _pass3_sync,
    "pass4": run_pass4,
}
```

- [ ] **Step 5: Run tests**

```bash
cd ingest && uv run pytest tests/test_pass4_all.py tests/test_cli.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ingest/src/timeline_ingest/pass4_enrich.py ingest/src/timeline_ingest/cli.py ingest/tests/test_pass4_all.py
git commit -m "feat(ingest): pass4 top-level runner"
```

---

## Task 22: Review HTML generator

**Files:**
- Create: `ingest/src/timeline_ingest/review.py`
- Create: `ingest/tests/test_review.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_review.py`:

```python
from pathlib import Path

from timeline_ingest.review import generate_review
from timeline_ingest.config import Config, ExistingExtractions, BooksToExtract, ChabadpediaPages, PhotoSources, OutputPaths


def _cfg(tmp_path):
    return Config(
        existing_extractions=ExistingExtractions(
            compact_json=tmp_path, comprehensive_md=tmp_path, chabadpedia_kg_dir=tmp_path),
        books_to_extract=BooksToExtract(
            undaunted_dir=tmp_path, undaunted_chapters_glob="*.txt",
            chabad_library_dir=tmp_path, chabad_library_history_book_ids=[]),
        chabadpedia_pages=ChabadpediaPages(dir=tmp_path),
        photos=PhotoSources(knowledge_graph_files=[]),
        output=OutputPaths(
            intermediate_dir=tmp_path / "i", cache_dir=tmp_path / "c",
            public_dir=tmp_path / "p", glossary_path=tmp_path / "g",
            level_overrides_path=tmp_path / "l"),
    )


def test_review_lists_only_macro(tmp_path: Path):
    cfg = _cfg(tmp_path)
    cfg.output.intermediate_dir.mkdir(parents=True)
    import json
    payload = [
        {"id": "m1", "level": "macro", "date": {"y": 1812, "precision": "year"},
         "title_en": "Macro one", "summary_en": "s", "story_path": "p", "category": "rebbe", "sources": [{"name": "x"}], "related": []},
        {"id": "x1", "level": "micro", "date": {"y": 1800, "precision": "year"},
         "title_en": "Micro one", "summary_en": "s", "story_path": "p", "category": "general", "sources": [{"name": "x"}], "related": []},
    ]
    (cfg.output.intermediate_dir / "04_enriched.json").write_text(json.dumps(payload))
    out = generate_review(cfg)
    html = out.read_text(encoding="utf-8")
    assert "Macro one" in html
    assert "Micro one" not in html
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_review.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Implement review generator**

Create `ingest/src/timeline_ingest/review.py`:

```python
"""Generate review.html listing all macro events for maintainer approval."""

import html
import json
from pathlib import Path

from timeline_ingest.config import Config
from timeline_ingest.schema import EventRecord


_TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<title>Pass 4 — Macro Event Review</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 900px; margin: 2em auto; padding: 0 1em; }}
  .event {{ border: 1px solid #ddd; padding: 1em; margin-bottom: 1em; border-radius: 6px; }}
  .event h3 {{ margin: 0 0 0.3em; }}
  .meta {{ color: #666; font-size: 0.9em; }}
</style>
<h1>Macro events ({n})</h1>
<p>Review each. Edit <code>level_overrides.yaml</code> to re-level any event, then re-run pass4.</p>
{events}
"""


def generate_review(cfg: Config) -> Path:
    src = cfg.output.intermediate_dir / "04_enriched.json"
    rows = json.loads(src.read_text(encoding="utf-8"))
    macro = [EventRecord.model_validate(r) for r in rows if r["level"] == "macro"]
    macro.sort(key=lambda r: (r.date.y, r.date.m or 0, r.date.d or 0))

    blocks = []
    for r in macro:
        blocks.append(
            "<div class='event'>"
            f"<h3>{html.escape(r.title_en)}</h3>"
            f"<div class='meta'>{r.date.y} · id={r.id} · category={r.category}</div>"
            f"<p>{html.escape(r.summary_en)}</p>"
            "</div>"
        )

    out_path = cfg.output.intermediate_dir / "review.html"
    out_path.write_text(_TEMPLATE.format(n=len(macro), events="\n".join(blocks)), encoding="utf-8")
    return out_path
```

- [ ] **Step 4: Wire into CLI**

Add to `ingest/src/timeline_ingest/cli.py`:

```python
from timeline_ingest.review import generate_review

PASSES["review"] = generate_review
```

- [ ] **Step 5: Run tests**

```bash
cd ingest && uv run pytest tests/test_review.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ingest/src/timeline_ingest/review.py ingest/src/timeline_ingest/cli.py ingest/tests/test_review.py
git commit -m "feat(ingest): macro-event review.html generator"
```

---

## Task 23: Pass 5 — emit events.json + stories + photos

**Files:**
- Create: `ingest/src/timeline_ingest/pass5_emit.py`
- Create: `ingest/tests/test_pass5.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_pass5.py`:

```python
import json
from pathlib import Path

from timeline_ingest.pass5_emit import run_pass5
from timeline_ingest.config import Config, ExistingExtractions, BooksToExtract, ChabadpediaPages, PhotoSources, OutputPaths


def _cfg(tmp_path):
    return Config(
        existing_extractions=ExistingExtractions(
            compact_json=tmp_path, comprehensive_md=tmp_path, chabadpedia_kg_dir=tmp_path),
        books_to_extract=BooksToExtract(
            undaunted_dir=tmp_path, undaunted_chapters_glob="*.txt",
            chabad_library_dir=tmp_path, chabad_library_history_book_ids=[]),
        chabadpedia_pages=ChabadpediaPages(dir=tmp_path),
        photos=PhotoSources(knowledge_graph_files=[]),
        output=OutputPaths(
            intermediate_dir=tmp_path / "i", cache_dir=tmp_path / "c",
            public_dir=tmp_path / "p", glossary_path=tmp_path / "g",
            level_overrides_path=tmp_path / "l"),
    )


def test_pass5_writes_events_and_stories(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.output.intermediate_dir.mkdir(parents=True)
    payload = [
        {
            "id": "abc", "level": "macro",
            "date": {"y": 1812, "precision": "year"},
            "title_en": "Alter Rebbe passes",
            "summary_en": "Summary.",
            "story_body": "Full story paragraph one. And paragraph two.",
            "story_path": "stories/abc.md",
            "category": "rebbe",
            "sources": [{"name": "x"}],
            "related": [],
        },
        {
            "id": "xyz", "level": "micro",
            "date": {"y": 1813, "precision": "year"},
            "title_en": "Letter to a chossid",
            "summary_en": "Fallback summary text.",
            "story_body": None,
            "story_path": "stories/xyz.md",
            "category": "general",
            "sources": [{"name": "x"}],
            "related": [],
        },
    ]
    (cfg.output.intermediate_dir / "04_enriched.json").write_text(json.dumps(payload))
    run_pass5(cfg)

    events_path = cfg.output.public_dir / "events.json"
    assert events_path.exists()
    stored = json.loads(events_path.read_text())
    assert {r["id"] for r in stored} == {"abc", "xyz"}

    story_abc = (cfg.output.public_dir / "stories" / "abc.md").read_text()
    assert "Full story paragraph one." in story_abc          # story_body used

    story_xyz = (cfg.output.public_dir / "stories" / "xyz.md").read_text()
    assert "Fallback summary text." in story_xyz             # summary fallback used
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_pass5.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Implement pass5**

Create `ingest/src/timeline_ingest/pass5_emit.py`:

```python
"""Pass 5 — write final artifacts: events.json + stories/ + photos/."""

import json
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

from timeline_ingest.config import Config
from timeline_ingest.schema import EventPhoto, EventRecord


_PHOTO_MAX_WIDTH = 800
_PHOTO_TIMEOUT_S = 15.0


def _render_story_md(r: EventRecord) -> str:
    body = r.story_body or r.summary_en
    return (
        f"# {r.title_en}\n\n"
        f"*{r.date.y}*\n\n"
        f"{body}\n"
    )


def _download_and_resize(url: str, out_path: Path) -> bool:
    """Fetch URL, resize to WebP at <=_PHOTO_MAX_WIDTH wide. Return True on success."""
    try:
        with httpx.Client(timeout=_PHOTO_TIMEOUT_S, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
        im = Image.open(BytesIO(resp.content))
        im = im.convert("RGB")
        if im.width > _PHOTO_MAX_WIDTH:
            ratio = _PHOTO_MAX_WIDTH / im.width
            new_size = (_PHOTO_MAX_WIDTH, int(im.height * ratio))
            im = im.resize(new_size, Image.LANCZOS)
        im.save(out_path, format="WEBP", quality=82, method=6)
        return True
    except (httpx.HTTPError, OSError, ValueError):
        return False


def run_pass5(cfg: Config) -> Path:
    src = cfg.output.intermediate_dir / "04_enriched.json"
    rows = json.loads(src.read_text(encoding="utf-8"))
    records = [EventRecord.model_validate(r) for r in rows]

    public = cfg.output.public_dir
    public.mkdir(parents=True, exist_ok=True)
    stories_dir = public / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)
    photos_dir = public / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    # Download / resize photos; rewrite r.photo.url to local relative path on success.
    final_records: list[EventRecord] = []
    for r in records:
        photo = r.photo
        if photo is not None:
            local = photos_dir / f"{r.id}.webp"
            if local.exists() or _download_and_resize(photo.url, local):
                photo = EventPhoto(
                    url=f"photos/{r.id}.webp",
                    credit=photo.credit,
                    caption=photo.caption,
                )
                r = r.model_copy(update={"photo": photo})
            else:
                # Remote fetch failed — drop the photo rather than ship a broken URL.
                r = r.model_copy(update={"photo": None})
        final_records.append(r)

    # Write events.json (compact)
    events_path = public / "events.json"
    events_path.write_text(
        json.dumps([r.model_dump(mode="json") for r in final_records], ensure_ascii=False),
        encoding="utf-8",
    )

    # Write per-event story markdown
    for r in final_records:
        (stories_dir / f"{r.id}.md").write_text(_render_story_md(r), encoding="utf-8")

    return events_path
```

- [ ] **Step 4: Wire into CLI**

Add to `ingest/src/timeline_ingest/cli.py`:

```python
from timeline_ingest.pass5_emit import run_pass5

PASSES["pass5"] = run_pass5
```

- [ ] **Step 5: Run tests**

```bash
cd ingest && uv run pytest tests/test_pass5.py tests/test_cli.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ingest/src/timeline_ingest/pass5_emit.py ingest/src/timeline_ingest/cli.py ingest/tests/test_pass5.py
git commit -m "feat(ingest): pass5 emit events.json + stories/"
```

---

## Task 24: Post-emit linter

**Files:**
- Create: `ingest/src/timeline_ingest/lint.py`
- Create: `ingest/tests/test_lint.py`
- Modify: `ingest/src/timeline_ingest/pass5_emit.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_lint.py`:

```python
import pytest
from pathlib import Path

from timeline_ingest.lint import lint_emit, LintError


def _write(path: Path, payload):
    import json
    path.write_text(json.dumps(payload))


def test_lint_passes_for_valid(tmp_path):
    public = tmp_path / "public"
    (public / "stories").mkdir(parents=True)
    payload = [{
        "id": "x", "level": "micro",
        "date": {"y": 1812, "precision": "year"},
        "title_en": "t", "summary_en": "s", "story_path": "stories/x.md",
        "category": "general", "sources": [{"name": "x"}], "related": [],
    }]
    _write(public / "events.json", payload)
    (public / "stories" / "x.md").write_text("# t\n")
    lint_emit(public)


def test_lint_fails_for_duplicate_ids(tmp_path):
    public = tmp_path / "public"
    (public / "stories").mkdir(parents=True)
    payload = [
        {"id": "x", "level": "micro", "date": {"y": 1812, "precision": "year"},
         "title_en": "t", "summary_en": "s", "story_path": "stories/x.md",
         "category": "general", "sources": [{"name": "x"}], "related": []},
        {"id": "x", "level": "micro", "date": {"y": 1813, "precision": "year"},
         "title_en": "t", "summary_en": "s", "story_path": "stories/x.md",
         "category": "general", "sources": [{"name": "x"}], "related": []},
    ]
    _write(public / "events.json", payload)
    (public / "stories" / "x.md").write_text("# t\n")
    with pytest.raises(LintError, match="duplicate"):
        lint_emit(public)


def test_lint_fails_for_orphan_related(tmp_path):
    public = tmp_path / "public"
    (public / "stories").mkdir(parents=True)
    payload = [{
        "id": "x", "level": "micro", "date": {"y": 1812, "precision": "year"},
        "title_en": "t", "summary_en": "s", "story_path": "stories/x.md",
        "category": "general", "sources": [{"name": "x"}], "related": ["nope"],
    }]
    _write(public / "events.json", payload)
    (public / "stories" / "x.md").write_text("# t\n")
    with pytest.raises(LintError, match="orphan"):
        lint_emit(public)


def test_lint_fails_for_missing_story_file(tmp_path):
    public = tmp_path / "public"
    (public / "stories").mkdir(parents=True)
    payload = [{
        "id": "x", "level": "micro", "date": {"y": 1812, "precision": "year"},
        "title_en": "t", "summary_en": "s", "story_path": "stories/x.md",
        "category": "general", "sources": [{"name": "x"}], "related": [],
    }]
    _write(public / "events.json", payload)
    # no story file
    with pytest.raises(LintError, match="story file"):
        lint_emit(public)


def test_lint_fails_for_remote_photo_url(tmp_path):
    public = tmp_path / "public"
    (public / "stories").mkdir(parents=True)
    payload = [{
        "id": "x", "level": "macro", "date": {"y": 1812, "precision": "year"},
        "title_en": "t", "summary_en": "s", "story_path": "stories/x.md",
        "category": "rebbe", "sources": [{"name": "x"}], "related": [],
        "photo": {"url": "https://example.org/p.jpg", "credit": "c"},
    }]
    _write(public / "events.json", payload)
    (public / "stories" / "x.md").write_text("# t\n")
    with pytest.raises(LintError, match="still remote"):
        lint_emit(public)


def test_lint_fails_for_missing_photo_file(tmp_path):
    public = tmp_path / "public"
    (public / "stories").mkdir(parents=True)
    payload = [{
        "id": "x", "level": "macro", "date": {"y": 1812, "precision": "year"},
        "title_en": "t", "summary_en": "s", "story_path": "stories/x.md",
        "category": "rebbe", "sources": [{"name": "x"}], "related": [],
        "photo": {"url": "photos/x.webp", "credit": "c"},
    }]
    _write(public / "events.json", payload)
    (public / "stories" / "x.md").write_text("# t\n")
    # no photos/x.webp
    with pytest.raises(LintError, match="photo file missing"):
        lint_emit(public)
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ingest && uv run pytest tests/test_lint.py -v && cd ..
```

Expected: FAIL.

- [ ] **Step 3: Implement linter**

Create `ingest/src/timeline_ingest/lint.py`:

```python
"""Post-emit linter: schema, integrity, story/photo file existence."""

import json
from pathlib import Path

from timeline_ingest.schema import EventRecord


class LintError(RuntimeError):
    pass


def lint_emit(public_dir: Path) -> None:
    events_path = public_dir / "events.json"
    rows = json.loads(events_path.read_text(encoding="utf-8"))
    records = [EventRecord.model_validate(r) for r in rows]

    # Duplicate id check
    ids = [r.id for r in records]
    if len(ids) != len(set(ids)):
        raise LintError(f"duplicate event ids in events.json")

    id_set = set(ids)

    # Orphan related check
    for r in records:
        for rid in r.related:
            if rid not in id_set:
                raise LintError(f"orphan related id {rid!r} on event {r.id!r}")

    # Story file existence
    for r in records:
        story_file = public_dir / r.story_path
        if not story_file.exists():
            raise LintError(f"missing story file {story_file}")

    # Photo url resolves (after Pass 5 rewrites remote URLs to local relative paths)
    for r in records:
        if r.photo is None:
            continue
        url = r.photo.url
        if url.startswith(("http://", "https://")):
            # A remote URL surviving past Pass 5 means the download failed and the
            # record wasn't cleared. That's a Pass 5 bug — fail loudly here.
            raise LintError(f"event {r.id} photo.url is still remote ({url})")
        local = public_dir / url
        if not local.exists():
            raise LintError(f"event {r.id} photo file missing at {local}")

    # Soft warnings (not failures): suspicious categorizations
    for r in records:
        if r.level == "macro" and r.category == "general":
            print(f"WARN: event {r.id} is macro+general — review")
        if r.level == "macro" and r.photo is None:
            print(f"WARN: event {r.id} is macro but has no photo — review")
```

- [ ] **Step 4: Call linter from pass5**

Modify `ingest/src/timeline_ingest/pass5_emit.py`. Add at end of `run_pass5`, before `return`:

```python
    from timeline_ingest.lint import lint_emit
    lint_emit(public)
```

- [ ] **Step 5: Run tests**

```bash
cd ingest && uv run pytest tests/test_lint.py tests/test_pass5.py -v && cd ..
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ingest/src/timeline_ingest/lint.py ingest/src/timeline_ingest/pass5_emit.py ingest/tests/test_lint.py
git commit -m "feat(ingest): post-emit linter (duplicates, orphans, file existence)"
```

---

## Task 25: Golden-file end-to-end sample test

**Files:**
- Create: `ingest/tests/fixtures/golden_input.json`
- Create: `ingest/tests/fixtures/golden_expected.json`
- Create: `ingest/tests/test_golden.py`

- [ ] **Step 1: Build golden fixtures**

Create `ingest/tests/fixtures/golden_input.json`:

```json
{
  "compact": [
    {"y": 1812, "t": "Alter Rebbe passes away", "d": "On 24 Tevet", "c": "rebbe", "s": "24 Tevet"},
    {"y": 1880, "t": "Rayatz born", "d": "Birth of the sixth Rebbe", "c": "rebbe", "s": "12 Tammuz"}
  ]
}
```

Create `ingest/tests/fixtures/golden_expected.json`:

```json
{
  "min_records": 2,
  "expected_ids_contain_year": [1812, 1880]
}
```

- [ ] **Step 2: Write the failing test**

Create `ingest/tests/test_golden.py`:

```python
import json
from pathlib import Path

from timeline_ingest.pass1_consolidate import load_compact_json


def test_golden_compact_loads(tmp_path: Path):
    fixture_in = Path(__file__).parent / "fixtures" / "golden_input.json"
    expected = json.loads(
        (Path(__file__).parent / "fixtures" / "golden_expected.json").read_text()
    )
    compact = tmp_path / "compact.json"
    compact.write_text(json.dumps(json.loads(fixture_in.read_text())["compact"]))
    records = load_compact_json(compact)
    assert len(records) >= expected["min_records"]
    years = {r.date.y for r in records}
    for y in expected["expected_ids_contain_year"]:
        assert y in years
```

- [ ] **Step 3: Run tests**

```bash
cd ingest && uv run pytest tests/test_golden.py -v && cd ..
```

Expected: PASS (this is a regression guard — adding new sources should not break this).

- [ ] **Step 4: Commit**

```bash
git add ingest/tests/fixtures/golden_input.json ingest/tests/fixtures/golden_expected.json ingest/tests/test_golden.py
git commit -m "test(ingest): golden-file regression guard for pass1 compact loader"
```

---

## Task 26: Idempotency test

**Spec requirement:** Re-running each pass against the previous pass's output must produce identical bytes (modulo cache hits).

**Files:**
- Create: `ingest/tests/test_idempotency.py`

- [ ] **Step 1: Write the failing test**

Create `ingest/tests/test_idempotency.py`:

```python
import json
from pathlib import Path

from timeline_ingest.config import Config, ExistingExtractions, BooksToExtract, ChabadpediaPages, PhotoSources, OutputPaths
from timeline_ingest.pass1_consolidate import consolidate
from timeline_ingest.pass4_enrich import run_pass4
from timeline_ingest.pass5_emit import run_pass5


def _cfg(tmp_path: Path) -> Config:
    return Config(
        existing_extractions=ExistingExtractions(
            compact_json=Path(__file__).parent / "fixtures" / "compact_sample.json",
            comprehensive_md=Path(__file__).parent / "fixtures" / "comprehensive_sample.md",
            chabadpedia_kg_dir=tmp_path,
        ),
        books_to_extract=BooksToExtract(
            undaunted_dir=tmp_path, undaunted_chapters_glob="*.txt",
            chabad_library_dir=tmp_path, chabad_library_history_book_ids=[]),
        chabadpedia_pages=ChabadpediaPages(dir=tmp_path),
        photos=PhotoSources(knowledge_graph_files=[]),
        output=OutputPaths(
            intermediate_dir=tmp_path / "intermediate", cache_dir=tmp_path / "cache",
            public_dir=tmp_path / "public", glossary_path=tmp_path / "g.yaml",
            level_overrides_path=tmp_path / "l.yaml"),
    )


def test_pass1_idempotent(tmp_path):
    cfg = _cfg(tmp_path)
    out_a = consolidate(cfg)
    bytes_a = out_a.read_bytes()
    out_b = consolidate(cfg)
    bytes_b = out_b.read_bytes()
    assert bytes_a == bytes_b


def test_pass4_idempotent(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.output.intermediate_dir.mkdir(parents=True)
    cfg.output.level_overrides_path.write_text("overrides: {}\n", encoding="utf-8")
    payload = [{
        "id": "abc", "level": "micro",
        "date": {"y": 1812, "precision": "year"},
        "title_en": "Alter Rebbe passes away",
        "summary_en": "",
        "story_body": None,
        "story_path": "stories/abc.md",
        "category": "rebbe",
        "sources": [{"name": "t"}], "related": [],
    }]
    (cfg.output.intermediate_dir / "03_translated.json").write_text(json.dumps(payload))
    out_a = run_pass4(cfg)
    bytes_a = out_a.read_bytes()
    out_b = run_pass4(cfg)
    bytes_b = out_b.read_bytes()
    assert bytes_a == bytes_b


def test_pass5_idempotent_without_photos(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.output.intermediate_dir.mkdir(parents=True)
    payload = [{
        "id": "abc", "level": "macro",
        "date": {"y": 1812, "precision": "year"},
        "title_en": "Alter Rebbe passes",
        "summary_en": "Summary.",
        "story_body": "Full story text.",
        "story_path": "stories/abc.md",
        "category": "rebbe",
        "sources": [{"name": "t"}], "related": [],
    }]
    (cfg.output.intermediate_dir / "04_enriched.json").write_text(json.dumps(payload))
    out_a = run_pass5(cfg)
    bytes_a = out_a.read_bytes()
    out_b = run_pass5(cfg)
    bytes_b = out_b.read_bytes()
    assert bytes_a == bytes_b
```

- [ ] **Step 2: Run tests**

```bash
cd ingest && uv run pytest tests/test_idempotency.py -v && cd ..
```

Expected: PASS. (If any pass non-deterministically reorders or re-stringifies dicts, this will fail — fix by sorting keys in JSON dumps or carrying ordered inputs through.)

- [ ] **Step 3: Commit**

```bash
git add ingest/tests/test_idempotency.py
git commit -m "test(ingest): idempotency tests for pass1, pass4, pass5"
```

---

## Task 27: Final integration — run the full pipeline against real data

**Files:** (no new files)

This is a wall-clock task: actually run the pipeline end-to-end against the real corpora. **Costs $80–200 in LLM API calls. Do not run lightly.**

- [ ] **Step 1: Set ANTHROPIC_API_KEY**

```bash
export ANTHROPIC_API_KEY="<key>"
```

- [ ] **Step 2: Run pass1 (fast)**

```bash
cd ingest && make pass1
```

Expected: `intermediate/01_consolidated.json` written, ~4-5k records.

- [ ] **Step 3: Run pass2 (slow + expensive)**

```bash
cd ingest && make pass2
```

Expected: 12–24 hours wall-clock. `intermediate/02_extracted.json` written.

- [ ] **Step 4: Run pass3**

```bash
cd ingest && make pass3
```

Expected: 2–4 hours. `intermediate/03_translated.json` written.

- [ ] **Step 5: Run pass4**

```bash
cd ingest && make pass4
```

Expected: <5 minutes. `intermediate/04_enriched.json` written.

- [ ] **Step 6: Run review**

```bash
cd ingest && make review
```

Expected: `intermediate/review.html` opens with ~50–80 macro events. Manually review; edit `level_overrides.yaml` for any re-leveling.

- [ ] **Step 7: Re-run pass4 if overrides changed**

```bash
cd ingest && make pass4
```

- [ ] **Step 8: Run pass5**

```bash
cd ingest && make pass5
```

Expected: `public/events.json + public/stories/<id>.md` written; linter passes.

- [ ] **Step 9: Commit the public artifacts**

```bash
cd /home/chassidusaicon/code/master-timeline-chabad
git add public/events.json public/stories/
git commit -m "data: ingest run $(date +%Y-%m-%d) — full corpus emit"
```

---

## Plan-end checklist

After all 27 tasks complete, the repo state should be:

- [ ] `ingest/` package fully implemented and tested (~85+ tests passing)
- [ ] `public/events.json` committed, ~5,000 records (or however many the real ingest yields)
- [ ] `public/stories/<id>.md` committed, one per event (uses `story_body` when Pass 2 captured it, else falls back to `title + year + summary`)
- [ ] `public/photos/<id>.webp` committed for every event with a `photo` (downloaded from Chabadpedia, resized to ≤800px wide, WebP @ 82 quality)
- [ ] Linter passes on the emitted artifacts (no duplicates, no orphan related ids, no missing story files, no remote photo URLs, no missing photo files)
- [ ] Idempotency tests green for passes 1, 4, 5
- [ ] `make all` is the one-command rebuild

**Deferred to v1.5 (out of scope for this plan):**

- Chabadpedia knowledge-graph event mining (extracting birth/death/start-of-leadership events from entity records). Major Rebbe-lifecycle events already arrive via the existing extractions and via Pass 2 over Undaunted / history books, so this defer doesn't leave a v1 gap.
- Translating the multi-paragraph `story_body` for Pass 1 records (the older Hebrew extractions, which only carry short Hebrew summaries — these get translated by Pass 3 and then surface as one-sentence stories in the UI).
- Golden-file regression coverage for passes 2–5 (Task 25 only exercises Pass 1).

**Next plan:** `docs/superpowers/plans/2026-05-2N-web-app.md` — Vite + TypeScript + vis-timeline web app consuming this ingestion's output.
