# Master Timeline Chabad — Design Spec

**Date:** 2026-05-20
**Status:** Approved (pending spec review loop)
**Owner:** zmabraham

---

## Problem

Chabad history spans 1700–present, is documented across multiple Hebrew-language corpora (Chabadpedia, the Chabad Library's *Misaviv L'Chassidus* category, biographies like *Undaunted*, and a handful of existing extractions), and currently has no single navigable, English-language, multi-level visualization that lets a reader zoom from "era of the Alter Rebbe" all the way down to a single dated letter or anecdote and read the full background story.

Several partial extractions already exist on disk (3,716-event compact JSON, 4,201-event comprehensive markdown, ~20 Undaunted events, Chabadpedia knowledge graphs), but they're Hebrew, fragmented across folders, and ship without a UI.

## Solution

A static web app — `master-timeline-chabad` — built around vis-timeline with clustering, fed by a one-time English-language ingestion pipeline that consolidates the existing extractions and adds fresh LLM extraction over *Undaunted*, the 17 Chabad Library history books, and Chabadpedia biographical pages. Every event is tagged macro / meso / micro; the UI renders the appropriate level for the current zoom; clicking an event opens a side panel with the full markdown story body, Gregorian + Hebrew dates, photo (when available from Chabadpedia), sources, and related events.

## Architecture

Two cleanly decoupled subsystems:

```
Sources (read-only)   →   Ingestion pipeline (Python, offline)   →   public/events.json
                                                                      public/stories/<id>.md
                                                                      public/photos/<id>.{jpg,webp}
                                                                            │
                                                                            ▼
                                                              Web app (Vanilla TS + Vite + vis-timeline)
                                                                            │
                                                                            ▼
                                                              GitHub Pages: master-timeline-chabad
```

The ingestion pipeline emits static artifacts. The web app loads `events.json` at boot, lazy-fetches per-event markdown stories on side-panel open, and lazy-loads photos. No server, no runtime API, no database.

## Sources

### Already extracted (consolidate → translate → dedupe)

| Source | Items | Language | On-disk path |
|---|---|---|---|
| `chabad-timeline-compact.json` | 3,716 | Hebrew | `~/code/nanoclaw/groups/whatsapp_main/` |
| `chabad-history-timeline-comprehensive.md` | 4,201 | Hebrew (era + category structured) | `~/code/nanoclaw/groups/whatsapp_main/` |
| Chabadpedia knowledge graphs (rebbes, people, places, publications, organizations, concepts) | ~thousands | Hebrew | `~/code/nanoclaw/groups/whatsapp_main/chabadpedia-web/` |

The compact JSON and comprehensive markdown overlap significantly; both are kept and collapsed by the dedupe step (hash of normalized title + date).

### To extract fresh (LLM extraction, English output)

| Source | Volume | Status on disk |
|---|---|---|
| **Undaunted** (Rabbi Chaim Miller) | 1 book, partial extractions exist | Per-chapter `.txt` + `.json` extractions in `nanoclaw/groups/whatsapp_main/undaunted_*` |
| **17 Chabad Library "Misaviv L'Chassidus" history books** | 17 books, Hebrew | `~/code/nanoclaw/groups/whatsapp_main/chabad-library-clean-books/` |
| **Chabadpedia biographical pages** | ~thousands of pages | `~/code/nanoclaw/groups/whatsapp_main/chabadpedia-web/pages/` |
| **Chabadpedia images** | thumbnails per entity | linked from knowledge graphs |

The 17 history books (full set, not trimmed):

1. מאסר וגאולת אדמו"ר האמצעי (Imprisonment and Redemption of the Mitteler Rebbe)
2. תולדות אברהם חיים
3. תולדות חב"ד בארץ הקודש (Chabad in the Holy Land)
4. תולדות חב"ד ברוסיה הצארית (Chabad in Tsarist Russia)
5. תולדות חב"ד בפולין, ליטא ולטביא (Chabad in Poland, Lithuania, Latvia)
6. זכרון לבני ישראל
7. למען ידעו בנים יוולדו
8. זכרונותי (Memoirs)
9. ליובאוויטש (Lubavitch)
10. מבית הגנזים (From the Archives)
11. תערוכות הספריה (Library Exhibitions)
12. יומן השליחות המיוחדת (Special Mission Diary)
13. עבודת הקודש (Holy Work)
14. בכל ביתי נאמן הוא
15. אדמו"רי חב"ד ויהדות בוכרה (Chabad Rebbes and Bukharian Jewry)
16. אדמו"רי חב"ד ויהדות אוסטריה (Chabad Rebbes and Austrian Jewry)
17. אדמו"רי חב"ד ויהדות גרמניה (Chabad Rebbes and German Jewry)

### Explicitly excluded (v1)

- `chabad-history-timeline.md` (53 auto-generated events from a hardcoded "known_events" table + early Undaunted extractions). Superseded by re-ingestion.
- `haerchim-teerav` (Hemshech Te'erav is a chassidic discourse corpus, not a history source).
- `vertlach-wiki` anecdotes (10,179 items, mostly undated). Deferred to v1.5 with a date-extraction pass.

## Data Model

```ts
type EventLevel = "macro" | "meso" | "micro";

type EventRecord = {
  id: string;                      // hash of normalized title + date
  level: EventLevel;
  date: {
    y: number;
    m?: number;
    d?: number;
    precision: "year" | "month" | "day";
  };
  hebrew_date?: {                  // when known
    y: number;
    m?: string;
    d?: number;
  };
  title_en: string;
  summary_en: string;              // 1–2 sentence card text
  story_path: string;              // relative path to stories/<id>.md (lazy-loaded)
  category:
    | "rebbe"
    | "publication"
    | "conflict"
    | "education"
    | "organization"
    | "location"
    | "calendar"
    | "general";
  rebbe?:
    | "besht"
    | "magid"
    | "alter"
    | "mitteler"
    | "tzemach-tzedek"
    | "maharash"
    | "rashab"
    | "rayatz"
    | "rebbe";
  era?: string;                    // derived
  photo?: { url: string; credit: string; caption?: string };
  sources: Array<{ name: string; url?: string; page?: number }>;
  related?: string[];              // ids of related events
};
```

`events.json` is `EventRecord[]` with `story_path` referencing `public/stories/<id>.md`. The full story body is **not** embedded in `events.json` — it's lazy-fetched by the side panel to keep the initial payload small.

### Level assignment

Two-pass:

1. **Heuristic pass** assigns initial level based on event content:
   - **macro** — Rebbe lifecycle events (birth, passing, leadership start), foundational publications (Tanya, Torah Or, Likkutei Torah), major arrests/exiles, founding events (Tomchei Tmimim, KGB resistance).
   - **meso** — Yeshiva foundings, dated sichos / maamarim with public significance, named correspondence, war/persecution episodes, family events of central figures, named regional milestones.
   - **micro** — Everything else with a date: individual letters, yahrzeits of non-central figures, individual anecdotes, calendar dates of secondary significance.

2. **Manual override file** (`ingest/level_overrides.yaml`) lets the maintainer pin specific event IDs to a specific level. Re-running the pipeline preserves overrides.

Expected counts after dedupe: ~50–80 macro, ~400–800 meso, ~3,000–6,000 micro.

## Ingestion Pipeline

Python, run offline, five idempotent passes. Each pass is incremental and resumable (skip-if-cached per source chunk).

### Pass 1 — Consolidate

- Load `chabad-timeline-compact.json`, `chabad-history-timeline-comprehensive.md`, Chabadpedia knowledge graphs.
- Normalize into `EventRecord` shape (with `title_en` still empty for Hebrew sources at this stage).
- Dedupe by `id = hash(normalized_title + date_string)`.
- **Output:** `ingest/intermediate/01_consolidated.json` (~4,000–5,000 Hebrew events).

### Pass 2 — Extract from books

- Chunk each book by chapter or by ~6k-token windows.
- LLM prompt per chunk: *"Extract every dated historical event. For each: title (≤ 90 chars), date as best resolvable (year required, month/day if stated), category, 1-sentence summary, and a 2-4 sentence story paragraph. JSON list output."*
- Books processed:
  - *Undaunted* (English — direct extraction, no translation needed)
  - 17 Chabad Library history books (Hebrew — extraction in Hebrew, English title/summary alongside)
  - Chabadpedia biographical pages (Hebrew — same)
- Concurrency cap: ~20 parallel API calls.
- Per-chunk results cached to `ingest/cache/<source>/<chunk_hash>.json`.
- **Output:** `ingest/intermediate/02_extracted.json`.

### Pass 3 — Translate

- For events still missing `title_en` / `summary_en`, batch-translate from Hebrew with a fixed glossary (Rebbe names, common terms, place names).
- Glossary file: `ingest/glossary.yaml`. Locked vocabulary — the LLM is instructed to use exactly these renderings (e.g., "Alter Rebbe" not "Old Rebbe").
- **Output:** `ingest/intermediate/03_translated.json`.

### Pass 4 — Level + photo + cross-reference

- Apply level heuristic (see Data Model).
- Apply `level_overrides.yaml`.
- For each event, attempt to attach a `photo` from the Chabadpedia knowledge graph when the event references a person/place/publication entity.
- Build `related[]` by Jaccard similarity on entity-mention sets within ±20 years.
- **Output:** `ingest/intermediate/04_enriched.json`.

### Pass 5 — Emit

- Write `public/events.json` (compact — drops `story_en` body, keeps `story_path`).
- Write `public/stories/<id>.md` (one file per event).
- Copy/optimize photos into `public/photos/<id>.webp`.
- Run post-emit linter (see Testing).
- **Output:** ready-to-serve `public/`.

### Manual review checkpoint

Between Pass 4 and Pass 5, the pipeline emits `ingest/review.html` listing all macro-level events with title, date, summary, and an inline "approve / edit level / drop" UI. Maintainer reviews macro events for accuracy before Pass 5 emits the final artifacts. Meso/micro are not reviewed manually in v1 (scale prohibits it).

### Cost & runtime estimates

- LLM extraction over Undaunted + 17 books + Chabadpedia bios: ~$80–150 (Claude Sonnet 4.6, with caching). ~12–24 hours wall-clock with concurrency.
- Translation: ~$15–30. ~2–4 hours.
- Total ingestion budget: **~$100–200, ~1–2 days wall-clock**.

## Web App

### Stack

- **Vanilla TypeScript** (no React/Vue framework)
- **Vite** build
- **vis-timeline** (`vis-timeline/standalone` — single bundle, includes vis-data)
- **Lunr.js** — client-side full-text search index, built at build time from `events.json`
- **marked** (or `markdown-it`) — render `story_path` md → HTML in the side panel
- **Tailwind CSS** — utility styling (or hand-rolled CSS; will decide during implementation, low-risk either way)

### Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Search ─────────]   [Rebbe ▾] [Category ▾] [Level ▾]   [About ⓘ] │
├─────────────────────────────────────────────────────────────────────┤
│ Besht       │█████│                                                 │
│ Magid       │     │██│                                              │
│ Alter Rebbe │     │  │█████│   ●●●● ●●  ●●●                         │
│ Mitteler    │     │  │     │██│  ●●●                                │
│ Tz. Tzedek  │     │  │     │  │████  ●●●●●●●                        │
│ ... (groups = horizontal lanes, one per Rebbe + "general")          │
│                                                                     │
│           [hover → tooltip]    [click → side panel slides in]       │
├─────────────────────────────────────────────────────────────────────┤
│  1700        1800        1900        2000     [zoom ─ ─ ─ ─ ─ +]    │
└─────────────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
                              Side panel (40% width, slides from right):
                              ┌─────────────────────────────────────┐
                              │  Event title                  [×]   │
                              │  16 Tishrei 5640 / Oct 3, 1879      │
                              │  ┌──────────┐                       │
                              │  │  photo   │  Summary line         │
                              │  └──────────┘                       │
                              │  Full story body (md → HTML)        │
                              │  ...                                │
                              │                                     │
                              │  Sources:                           │
                              │  - Undaunted, p. 47                 │
                              │  - Chabadpedia: Rebbetzin Shterna   │
                              │                                     │
                              │  Related events:                    │
                              │  - Rayatz born (1880)               │
                              │  - First arrest of Yosef Yitzchak   │
                              └─────────────────────────────────────┘
```

### Zoom → level mapping

vis-timeline exposes a zoom-level value (millisecond range visible). We bin that to:

| Zoom range visible | Show |
|---|---|
| > 100 years | macro only; meso/micro clustered into numeric badges |
| 30–100 years | macro + meso; micro clustered |
| < 30 years | macro + meso + micro (all individually visible) |

CSS classes `level-macro`, `level-meso`, `level-micro` style differently (size, color, photo thumbnail visibility).

### Groups (horizontal lanes)

One group per Rebbe (`besht`, `magid`, `alter`, `mitteler`, `tzemach-tzedek`, `maharash`, `rashab`, `rayatz`, `rebbe`) plus a `general` lane for events not tied to a single Rebbe (e.g., dated yahrzeits of figures outside the dynasty, contemporary movements). The group strip auto-scrolls when there are too many lanes for the viewport height.

### Search & filters

- **Search** — Lunr index over `title_en + summary_en`. Hit results are highlighted on the timeline; non-matching events fade to ~20% opacity but remain visible (so context isn't lost).
- **Rebbe filter** — Show/hide entire groups.
- **Category filter** — Multi-select chips. Same fade-vs-hide behavior as search.
- **Level filter** — Override the zoom-based level visibility (force "show all micro" or "macro only").

### Side panel

- Slides in from right on event click, 40% width on desktop, full-width sheet on mobile.
- Fetches `stories/<id>.md` lazily on open, caches in-memory.
- Photo lazy-loaded (`loading="lazy"`).
- Related events render as clickable cards that open that event's panel.
- Close button + ESC + click-outside all dismiss.
- Deep linking is **deferred to v1.5** (route `/event/<id>` opens the panel pre-loaded).

## Hosting

- **Repo:** `github.com/zmabraham/master-timeline-chabad`
- **Branch:** `main` for source, `gh-pages` deployment via GitHub Actions
- **Build output:** `dist/` (built by Vite) → deployed to `gh-pages`
- **Pages limits:** GitHub Pages has a 1 GB repo / 100 GB/month bandwidth limit. `events.json` at ~5,000 events fits comfortably (estimated ~2 MB compressed). Photos at WebP @ 800px max-width should keep `photos/` under ~100 MB. If we approach limits, we move photos to a GitHub Release asset and lazy-fetch from there.

## v1 Scope

**In v1:**

- All ingestion passes 1–5 complete against:
  - Existing consolidated data (compact JSON + comprehensive markdown + Chabadpedia KGs)
  - *Undaunted* full extraction
  - All 17 Chabad Library history books
  - Chabadpedia biographical pages
- vis-timeline rendering with macro/meso/micro level switching by zoom
- Groups per Rebbe + "general" lane
- Click → side-panel story view (md → HTML)
- Lunr full-text search
- Faceted filters (Rebbe, Category, Level)
- Photos for all macro events + best-effort for meso/micro from Chabadpedia
- GitHub Pages deployed
- README documenting how to extend the corpus (add a new source, re-run ingestion)
- `methodology.md` describing how levels were assigned

**Deferred to v1.5:**

- D3 era-ribbon overlay (Wellcome-style polished macro view above the timeline)
- vertlach-wiki anecdote pass (10,179 items, mostly undated — needs date-extraction LLM pass)
- Deep links (`/event/<id>`)
- Edit-this-event link → GitHub PR workflow
- Hebrew toggle (UI strings + show original Hebrew title/story alongside English)
- Mobile-optimized timeline (vis-timeline's default mobile experience is functional but not great)

## Testing

### Ingestion pipeline

- **Schema validation** — Pydantic `EventRecord` model validates every emit. Pipeline fails loudly if a record violates schema.
- **Golden-file tests** — A fixed 50-event sample drawn from the existing data exercises each pass (consolidate, dedupe, normalize, level-assign). Output is diffed against committed golden JSON.
- **Idempotency test** — Re-running each pass against the previous pass's output must produce identical bytes (modulo cache hits).
- **Sampling review** — After Pass 4, the pipeline emits a 100-event random sample report for manual sanity-check before macro-event review.

### Web app

- **Playwright smoke test:**
  1. Load page
  2. Wait for timeline render (assert ≥ macro events visible)
  3. Type a known search term, assert hit highlights
  4. Click a known macro event, assert side panel opens with story body
  5. Toggle a Rebbe filter off, assert that Rebbe's group hides
  6. Close panel via ESC, assert dismissed
- **Bundle-size budget** — fail CI if `dist/` exceeds 500 KB gzipped (excluding photos and stories).

### Data quality (post-emit linter)

- Every event has `date.y`.
- Every macro event has a `photo`.
- No duplicate `id`s.
- No orphan `related[]` ids (every referenced id exists).
- No event with `level == macro` and `category == "general"` (suspicious — flag for review).
- All `story_path` files exist on disk.
- All `photo.url` paths resolve.

## Project Structure

```
master-timeline-chabad/
├── README.md
├── .gitignore
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-05-20-chabad-history-timeline-design.md   ← this file
│       └── plans/
│           └── (implementation plan goes here next)
├── ingest/
│   ├── pyproject.toml
│   ├── glossary.yaml
│   ├── level_overrides.yaml
│   ├── sources.yaml            # paths to all source files
│   ├── pipeline/
│   │   ├── pass1_consolidate.py
│   │   ├── pass2_extract.py
│   │   ├── pass3_translate.py
│   │   ├── pass4_enrich.py
│   │   └── pass5_emit.py
│   ├── tests/
│   │   ├── test_consolidate.py
│   │   ├── test_dedupe.py
│   │   └── fixtures/
│   ├── intermediate/           # gitignored
│   ├── cache/                  # gitignored
│   └── review.html             # generated; gitignored
├── web/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.ts
│   │   ├── timeline.ts         # vis-timeline setup + zoom→level
│   │   ├── search.ts           # Lunr integration
│   │   ├── filters.ts
│   │   ├── panel.ts            # side-panel rendering
│   │   ├── data.ts             # events.json loader + lazy story fetch
│   │   └── styles.css
│   └── tests/
│       └── smoke.spec.ts       # Playwright
└── public/                     # build artifacts (committed to gh-pages, not main)
    ├── events.json
    ├── stories/
    └── photos/
```

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| LLM extraction quality on Hebrew chassidic prose is uneven | Per-chunk caching means we can re-prompt with improved instructions without re-paying for everything. Glossary lock keeps proper-noun rendering consistent. |
| 4,000–5,000 events overwhelm the macro view visually | Zoom-based level filtering + clustering. Macro view shows only ~50–80 events. |
| GitHub Pages bandwidth limits at scale | events.json compact; stories lazy; photos in GitHub Release if needed; fallback to Cloudflare Pages (free tier is generous). |
| vis-timeline aesthetic feels too library-rendered | v1.5 D3 era-ribbon overlay solves this additively without rewriting the engine. |
| Manual review of all macro events is still a chunk of work | Estimated 50–80 macro events × ~1 minute each = 1–1.5 hours. Acceptable for a one-time review. |

## Open Questions (none blocking)

- Glossary content for proper-noun renderings — will be drafted at the start of implementation by sampling existing English Chabad sources (Sichos in English, Kehot publications). Not a design-time decision.
- Photo licensing for Chabadpedia images — Chabadpedia content is CC-BY-SA; we credit and link back. Will note in `methodology.md`.

---

End of design spec.
