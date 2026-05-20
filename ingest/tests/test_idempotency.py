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
            significance_overrides_path=tmp_path / "l.yaml"),
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
    cfg.output.significance_overrides_path.write_text("overrides: {}\n", encoding="utf-8")
    payload = [{
        "id": "abc", "significance": 25,
        "date": {"y": 1812, "precision": "year"},
        "title_en": "Alter Rebbe passes away",
        "summary_en": "",
        "story_body": None,
        "story_path": "stories/abc.md",
        "categories": ["rebbe"],
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
        "id": "abc", "significance": 85,
        "date": {"y": 1812, "precision": "year"},
        "title_en": "Alter Rebbe passes",
        "summary_en": "Summary.",
        "story_body": "Full story text.",
        "story_path": "stories/abc.md",
        "categories": ["rebbe"],
        "sources": [{"name": "t"}], "related": [],
    }]
    (cfg.output.intermediate_dir / "04_enriched.json").write_text(json.dumps(payload))
    out_a = run_pass5(cfg)
    bytes_a = out_a.read_bytes()
    out_b = run_pass5(cfg)
    bytes_b = out_b.read_bytes()
    assert bytes_a == bytes_b
