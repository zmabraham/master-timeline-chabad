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
<p>Review each. Edit <code>significance_overrides.yaml</code> to re-score any event, then re-run pass4.</p>
{events}
"""


def generate_review(cfg: Config) -> Path:
    src = cfg.output.intermediate_dir / "04_enriched.json"
    rows = json.loads(src.read_text(encoding="utf-8"))
    macro = [
        EventRecord.model_validate(r)
        for r in rows
        if int(r.get("significance", 0)) >= 80
    ]
    macro.sort(key=lambda r: (r.date.y, r.date.m or 0, r.date.d or 0))

    blocks = []
    for r in macro:
        cats = ",".join(r.categories)
        blocks.append(
            "<div class='event'>"
            f"<h3>{html.escape(r.title_en)}</h3>"
            f"<div class='meta'>"
            f"{r.date.y} · id={r.id} · significance={r.significance} · categories={cats}"
            f"</div>"
            f"<p>{html.escape(r.summary_en)}</p>"
            "</div>"
        )

    out_path = cfg.output.intermediate_dir / "review.html"
    out_path.write_text(_TEMPLATE.format(n=len(macro), events="\n".join(blocks)), encoding="utf-8")
    return out_path
