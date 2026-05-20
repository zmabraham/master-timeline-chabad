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

    ids = [r.id for r in records]
    if len(ids) != len(set(ids)):
        raise LintError(f"duplicate event ids in events.json")

    id_set = set(ids)

    for r in records:
        for rid in r.related:
            if rid not in id_set:
                raise LintError(f"orphan related id {rid!r} on event {r.id!r}")

    for r in records:
        story_file = public_dir / r.story_path
        if not story_file.exists():
            raise LintError(f"missing story file {story_file}")

    for r in records:
        if r.photo is None:
            continue
        url = r.photo.url
        if url.startswith(("http://", "https://")):
            raise LintError(f"event {r.id} photo.url is still remote ({url})")
        local = public_dir / url
        if not local.exists():
            raise LintError(f"event {r.id} photo file missing at {local}")

    for r in records:
        if r.significance >= 80 and r.categories == ["general"]:
            print(f"WARN: event {r.id} is high-significance with only category=general — review")
        if r.significance >= 80 and r.photo is None:
            print(f"WARN: event {r.id} is high-significance but has no photo — review")
