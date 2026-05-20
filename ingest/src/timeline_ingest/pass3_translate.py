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
