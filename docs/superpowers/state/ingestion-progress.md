# Ingestion Pipeline — Progress Tracker

Mirror of the 27-task plan with checkboxes. Update one box per task as it lands. The next Claude Code session reads this file first to find where to resume.

Plan: [`docs/superpowers/plans/2026-05-20-ingestion-pipeline.md`](../plans/2026-05-20-ingestion-pipeline.md)

## Progress

- [x] **Task 1** — Scaffold the ingest package (commits `255ca88`, `c7740de`)
- [x] **Task 2** — EventRecord Pydantic schema (commits `11da49a`, `1226c28`, `994995a`)
- [x] **Task 3** — Stable event ID hashing (commits `47b41ed`, `47859e3`)
- [x] **Task 4** — Date normalization utility (commits `3088ece`, `db7df33`)
- [x] **Task 5** — sources.yaml + config loader (commit `c561369`)
- [x] **Task 6** — glossary.yaml + significance_overrides.yaml seeds (commit `f4a2190`)
- [x] **Task 7** — Pass 1 compact JSON loader (commit `159c0e0`)
- [x] **Task 8** — Pass 1 comprehensive markdown loader (commit `f917215`)
- [x] **Task 9** — Pass 1 merge + cross-source dedupe + writer (commit `ebaa12f`)
- [x] **Task 10** — CLI entrypoint with pass1 wired (commit `e463e95`)
- [x] **Task 11** — Smoke-test pass1 against real data (commit `6cfe085` — fixed MD loader to match both event formats; real-data count: 3,028 records, 3,023 with non-empty summary)
- [x] **Task 12** — LLM client wrapper (commit `e86166e`)
- [x] **Task 13** — Pass 2 chunker (commit `318fa3c`)
- [x] **Task 14** — Pass 2 extraction prompt + JSON parser (commit `9ca4fb0`)
- [x] **Task 15** — Pass 2 single-book extraction driver (commit `1323c8e`)
- [x] **Task 16** — Pass 2 top-level run_pass2 across all sources (commit `9d2f079`)
- [x] **Task 17** — Pass 3 translation with glossary lock (commit `8a22365`)
- [x] **Task 18** — Pass 4 significance heuristic + overrides (commit `84e34ec`)
- [x] **Task 19** — Pass 4 photo attachment from KGs (commit `f3f4274`)
- [x] **Task 20** — Pass 4 related[] via Jaccard (commit `af455cc`)
- [x] **Task 21** — Pass 4 top-level run_pass4 + CLI (commit `a6446d9`)
- [x] **Task 22** — review.html generator (commit `9e216a6`)
- [x] **Task 23** — Pass 5 emit (events.json + stories + photos) (commit `8405dbe`)
- [x] **Task 24** — Post-emit linter (commit `0edb95a`)
- [x] **Task 25** — Golden-file regression test (commit `21649f2`)
- [x] **Task 26** — Idempotency tests (commit `7d7b42a`)
- [ ] **Task 27** — Real-data full pipeline run (REQUIRES ANTHROPIC_API_KEY, $100-200, 1-2 days; HUMAN review step in the middle)

## Test status

**75 tests passing** across 18 test files. `cd ingest && uv run pytest -v` verifies.

## Conventions

- Each task gets a `feat(ingest): ...` commit when first landed; if code review finds defects, a `fix(ingest): ...` follow-up commit lands on the same branch before the task is checked off.
- Both spec-compliance AND code-quality review must approve before checking the box.
- Tasks 1-26 are pure code+tests, no external API spend.
- Task 27 is the only paid step. See [`HANDOFF.md`](../../../HANDOFF.md) for execution + cost-cap details.
