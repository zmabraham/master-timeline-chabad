"""Pass 4 — assign significance score (0–100), attach photos, build related[]."""

import re
from collections.abc import Iterable

from timeline_ingest.schema import EventCategory, EventRecord

_PATTERN_SCORES: list[tuple[re.Pattern, int]] = [
    (re.compile(r"\bborn\b", re.I), 50),
    (re.compile(r"\bpasses away\b|\bpassing\b", re.I), 50),
    (re.compile(r"\bbecame? .* rebbe\b|\bbecomes? .* rebbe\b", re.I), 50),
    (re.compile(r"\barrest(ed)?\b|\bexile(d)?\b|\bredemption\b", re.I), 45),
    (re.compile(r"\btanya\b|\blikkutei torah\b|\btorah or\b", re.I), 50),
    (re.compile(r"\btomchei tmimim\b", re.I), 30),
    (re.compile(r"\byeshiva\b|\bfounded\b|\bestablished\b", re.I), 25),
    (re.compile(r"\bpogrom\b|\bwar\b", re.I), 25),
    (re.compile(r"\bmaamar\b|\bsicha\b|\bfarbrengen\b", re.I), 15),
    (re.compile(r"\bemigration\b", re.I), 15),
]

_BASE_SCORE = 20
_CATEGORY_BONUSES: dict[EventCategory, int] = {
    "rebbe": 20,
    "publication": 10,
    "conflict": 10,
    "education": 5,
    "organization": 5,
    "location": 0,
    "calendar": 0,
    "general": 0,
}
_REBBE_FIELD_BONUS = 10


def assign_significance(rec: EventRecord) -> int:
    text = f"{rec.title_en} {rec.summary_en}".lower()
    score = _BASE_SCORE
    for pat, points in _PATTERN_SCORES:
        if pat.search(text):
            score += points
    if rec.categories:
        score += max(_CATEGORY_BONUSES.get(c, 0) for c in rec.categories)
    if rec.rebbe is not None:
        score += _REBBE_FIELD_BONUS
    return max(0, min(100, score))


def apply_overrides(
    records: Iterable[EventRecord],
    overrides: dict[str, int],
) -> list[EventRecord]:
    out: list[EventRecord] = []
    for r in records:
        score = overrides.get(r.id)
        if score is None:
            score = assign_significance(r)
        out.append(r.model_copy(update={"significance": int(score)}))
    return out


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


_TOKEN_RE = re.compile(r"[\w֐-׿]+", re.UNICODE)


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text)}


def attach_photos(
    records: Iterable[EventRecord],
    *,
    entity_index: dict[str, EventPhoto],
) -> list[EventRecord]:
    """Match entity → event by full-token overlap on title+summary."""
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


import json
from pathlib import Path

import yaml

from timeline_ingest.config import Config


def run_pass4(cfg: Config) -> Path:
    p3 = cfg.output.intermediate_dir / "03_translated.json"
    rows = json.loads(p3.read_text(encoding="utf-8"))
    records = [EventRecord.model_validate(r) for r in rows]

    overrides_doc = yaml.safe_load(cfg.output.significance_overrides_path.read_text(encoding="utf-8")) or {}
    overrides = overrides_doc.get("overrides", {})

    records = apply_overrides(records, overrides)

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
