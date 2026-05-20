# Resume / Handoff — Master Timeline Chabad

If this Claude Code session ended abruptly, here's how the next session picks up cleanly.

## Project state

- **Repo:** `/home/chassidusaicon/code/master-timeline-chabad`
- **Branch:** `ingest/v1` (NOT `main` — main holds only design+plan docs)
- **Status file:** [`docs/superpowers/state/ingestion-progress.md`](docs/superpowers/state/ingestion-progress.md) — checkbox per task
- **Plan:** [`docs/superpowers/plans/2026-05-20-ingestion-pipeline.md`](docs/superpowers/plans/2026-05-20-ingestion-pipeline.md) — 27 tasks
- **Spec:** [`docs/superpowers/specs/2026-05-20-chabad-history-timeline-design.md`](docs/superpowers/specs/2026-05-20-chabad-history-timeline-design.md)

## Pre-authorizations granted by zmabraham (2026-05-20)

1. **Tasks 3–26 may run autonomously** via subagent-driven-development. Surface only on BLOCKED or after 3 fix iterations.
2. **Task 27 may proceed automatically** once tasks 1–26 are green. Hard spend cap: **$250**. Pause for human eyes during the macro-event review step (open `ingest/intermediate/review.html`, edit `ingest/significance_overrides.yaml`).
3. **ANTHROPIC_API_KEY** comes from the existing env var on the host machine. Verify with `printenv ANTHROPIC_API_KEY | head -c 5` before starting Task 27.

## How to resume

1. **Read the progress file:** [`docs/superpowers/state/ingestion-progress.md`](docs/superpowers/state/ingestion-progress.md) shows which tasks are done.
2. **Check git log:** `git -C /home/chassidusaicon/code/master-timeline-chabad log --oneline ingest/v1` — every completed task has a `feat(ingest):` or `fix(ingest):` commit.
3. **Verify tests still pass:** `cd ingest && uv run pytest -v`
4. **Pick up at the next pending task:** find the first unchecked task in the progress file, locate it in the plan, dispatch the implementer subagent per the `subagent-driven-development` skill template.

## Subagent-driven-development cycle (per task)

For each task: implementer → spec-compliance reviewer → code-quality reviewer → fix-loop until both approve → mark task done → next task.

Prompt templates live at: `~/.claude/plugins/cache/superpowers-marketplace/superpowers/5.0.5/skills/subagent-driven-development/`

## Task 27 execution

When tasks 1-26 are green:

```bash
cd /home/chassidusaicon/code/master-timeline-chabad/ingest

# Pre-flight checks
test -n "$ANTHROPIC_API_KEY" && echo "API key set" || echo "MISSING ANTHROPIC_API_KEY"
uv run pytest -v   # all tests must pass

# Run the pipeline
make pass1                   # seconds, $0
make pass2                   # 12-24h, $80-150  (PAUSE here if approaching $250 cap)
make pass3                   # 2-4h, $15-30
make pass4                   # <5min, $0
make review                  # opens review.html
# >>> HUMAN: open intermediate/review.html, edit significance_overrides.yaml, then:
make pass4                   # re-apply overrides
make pass5                   # 5-30min, downloads photos

cd /home/chassidusaicon/code/master-timeline-chabad
git add public/events.json public/stories/ public/photos/
git commit -m "data: ingest run $(date +%Y-%m-%d) — full corpus emit"
```

Each pass is **per-chunk cached** (`ingest/cache/<source>/<chunk_hash>.txt`), so any interruption resumes for free. Re-running the same pass twice should produce identical output (idempotency tests verify this).

## Cost cap protection

Before kicking off `make pass2`, the next session should sanity-check that the cache directory isn't already empty — if it is, the full Pass 2 spend will happen from scratch. If it's not empty, re-running pass2 will mostly hit the cache and cost very little.

```bash
du -sh ingest/cache/  # rough proxy for "how much has already been spent"
```
