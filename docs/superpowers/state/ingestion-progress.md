# Ingestion Pipeline — Progress Tracker

Mirror of the 27-task plan with checkboxes. Update one box per task as it lands. The next Claude Code session reads this file first to find where to resume.

Plan: [`docs/superpowers/plans/2026-05-20-ingestion-pipeline.md`](../plans/2026-05-20-ingestion-pipeline.md)

## Progress

- [x] **Task 1** — Scaffold the ingest package (commits `255ca88`, `c7740de`)
- [x] **Task 2** — EventRecord Pydantic schema (commits `11da49a`, `1226c28`)
- [x] **Task 3** — Stable event ID hashing (commits `47b41ed`, `47859e3`)
- [ ] **Task 4** — Date normalization utility
- [ ] **Task 5** — sources.yaml + config loader
- [ ] **Task 6** — glossary.yaml + significance_overrides.yaml seeds
- [ ] **Task 7** — Pass 1 compact JSON loader
- [ ] **Task 8** — Pass 1 comprehensive markdown loader
- [ ] **Task 9** — Pass 1 merge + cross-source dedupe + writer
- [ ] **Task 10** — CLI entrypoint with pass1 wired
- [ ] **Task 11** — Smoke-test pass1 against real data
- [ ] **Task 12** — LLM client wrapper (caching + concurrency)
- [ ] **Task 13** — Pass 2 chunker
- [ ] **Task 14** — Pass 2 extraction prompt + JSON parser
- [ ] **Task 15** — Pass 2 single-book extraction driver
- [ ] **Task 16** — Pass 2 top-level run_pass2 across all sources
- [ ] **Task 17** — Pass 3 translation with glossary lock
- [ ] **Task 18** — Pass 4 significance heuristic + overrides
- [ ] **Task 19** — Pass 4 photo attachment from KGs
- [ ] **Task 20** — Pass 4 related[] via Jaccard
- [ ] **Task 21** — Pass 4 top-level run_pass4 + CLI
- [ ] **Task 22** — review.html generator
- [ ] **Task 23** — Pass 5 emit (events.json + stories + photos)
- [ ] **Task 24** — Post-emit linter
- [ ] **Task 25** — Golden-file regression test
- [ ] **Task 26** — Idempotency tests
- [ ] **Task 27** — Real-data full pipeline run (REQUIRES ANTHROPIC_API_KEY, $100-200, 1-2 days)

## Conventions

- Each task gets a `feat(ingest): ...` commit when first landed; if code review finds defects, a `fix(ingest): ...` follow-up commit lands on the same branch before the task is checked off.
- Both spec-compliance AND code-quality review must approve before checking the box.
- Tasks 1-26 are pure code+tests, no external API spend.
- Task 27 is the only paid step. See [`HANDOFF.md`](../../../HANDOFF.md) for execution + cost-cap details.
