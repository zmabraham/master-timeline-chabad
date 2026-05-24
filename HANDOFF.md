# Resume / Handoff — Master Timeline Chabad

A fresh Claude Code session should read this file first to pick up exactly where the last one left off.

---

## Current state (as of 2026-05-24)

**Plan 1 (ingestion) is COMPLETE.** All 27 tasks done. The pipeline ran end-to-end and produced:

- `public/events.json` — **8,159 events** (post-cleanup), 1500–2026, sorted chronologically
- `public/stories/<id>.md` — 8,159 markdown files (one per event)
- `public/photos/` — empty (Pass 4 KG entity match didn't link any photo URLs; deferred to v1.5)

Significance distribution: 694 macro (≥80) / 3,195 meso (40–79) / 4,270 micro (<40).

**Plan 2 (web app) is WRITTEN and APPROVED.** 10 tasks, ready to execute.

**Next step:** execute Plan 2.

---

## Repo state

- **Repo:** `/home/chassidusaicon/code/master-timeline-chabad`
- **GitHub:** [github.com/zmabraham/master-timeline-chabad](https://github.com/zmabraham/master-timeline-chabad) (private)
- **Branch you're working on:** `ingest/v1` (NOT `main` — main has only design+plan docs)
- **Tests:** 75 ingestion-package tests passing — verify with `cd ingest && uv run pytest -v`

Key files for the next session:

| File | Purpose |
|---|---|
| [`docs/superpowers/specs/2026-05-20-chabad-history-timeline-design.md`](docs/superpowers/specs/2026-05-20-chabad-history-timeline-design.md) | Original design spec for everything |
| [`docs/superpowers/plans/2026-05-20-ingestion-pipeline.md`](docs/superpowers/plans/2026-05-20-ingestion-pipeline.md) | Plan 1 (done) |
| [`docs/superpowers/plans/2026-05-24-web-app.md`](docs/superpowers/plans/2026-05-24-web-app.md) | **Plan 2 — execute next** |
| [`docs/superpowers/state/ingestion-progress.md`](docs/superpowers/state/ingestion-progress.md) | Plan 1 task checkboxes (all checked) |
| `public/events.json` | The data Plan 2 will consume |
| `public/stories/*.md` | Story bodies Plan 2 will lazy-fetch |
| `scripts/clean-events.py` | The post-emit cleanup pass that brought 8,385 → 8,159 |

---

## How to resume in a fresh Claude Code session

### 1. Open Claude Code in the repo

```bash
cd ~/code/master-timeline-chabad
claude
```

### 2. Paste this prompt to the new session

> Read `HANDOFF.md` and `docs/superpowers/plans/2026-05-24-web-app.md`, then execute Plan 2 (the web app implementation plan) using the subagent-driven-development workflow. Pre-authorizations: all 10 tasks may run autonomously without checking back; surface only on BLOCKED or after 3 fix iterations.

That's it. The new session will:

1. Read this handoff to understand state
2. Read Plan 2 to know what to build
3. Dispatch implementer + reviewer subagents per task per the `subagent-driven-development` skill
4. Mark each task complete via the progress tracker
5. Commit each task; push when done

### Alternative — execute one task at a time

If you'd rather drive each task manually (more visibility, slower), use:

> Read `HANDOFF.md` and `docs/superpowers/plans/2026-05-24-web-app.md`. Start by executing only Task 1. Stop and report back when Task 1 is done.

---

## Pre-authorizations carrying forward

1. **Plan 2 tasks 1–10 may run autonomously** via subagent-driven-development. Same pattern as Plan 1.
2. **GitHub Pages deploy** (Task 10) requires you to enable Pages in the GitHub repo Settings → Pages → Source = "GitHub Actions" (one-time manual step in the UI).
3. **`gh` CLI is authenticated** as `zmabraham` with `repo` + `workflow` scopes — the next session can push and create workflows freely.

---

## Background processes — likely cleanup needed

The last session left these running. They're harmless but the new session may want to tidy up:

```bash
# Long-running processes from the Plan 1 execution (likely already finished or zombie):
pgrep -fa "timeline_ingest pass" 2>/dev/null
pgrep -fa "finish-ingest.sh"     2>/dev/null

# HTTP server + Cloudflare tunnel for snapshot downloads:
pgrep -fa "python3 -m http.server 49823" 2>/dev/null
pgrep -fa "cloudflared.*tunnel"          2>/dev/null

# Kill all of the above if any are still running:
pkill -f "timeline_ingest pass"
pkill -f "finish-ingest.sh"
pkill -f "python3 -m http.server 49823"
pkill -f "/tmp/cloudflared-new tunnel"
```

---

## If Plan 2 also gets messy

Same pattern as Plan 1's recovery: open a fresh session, paste the resume prompt. The git history has every committed step; the next session reads `git log --oneline ingest/v1` to see what's done.

---

## Open issues to be aware of

- **Photos.** Pass 4's `_build_entity_index` reads `image` field from the Chabadpedia knowledge graphs but the actual KG schema uses a different key. Result: 0/8,159 events have `photo` set. The schema field is there in events.json; Plan 2 will render `<img>` if it exists and skip if not. A separate v1.5 ticket should fix `_build_entity_index` and re-run Pass 4 + Pass 5.

- **Data quality.** The cleanup pass dropped 226 garbage events (Chabadpedia bio templates, anachronisms, calendar-label fragments, etc.). Some legitimate ones may still need manual review — Plan 2 surfaces them in the UI where the user can flag for re-scoring via `ingest/significance_overrides.yaml`.

- **Snapshot CSVs.** `snapshots/2026-05-24-events-pass2.csv` is a pre-translation snapshot for reference. Drop it from the timeline if you don't need it.
