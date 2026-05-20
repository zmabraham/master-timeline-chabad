from pathlib import Path

from timeline_ingest.review import generate_review
from timeline_ingest.config import Config, ExistingExtractions, BooksToExtract, ChabadpediaPages, PhotoSources, OutputPaths


def _cfg(tmp_path):
    return Config(
        existing_extractions=ExistingExtractions(
            compact_json=tmp_path, comprehensive_md=tmp_path, chabadpedia_kg_dir=tmp_path),
        books_to_extract=BooksToExtract(
            undaunted_dir=tmp_path, undaunted_chapters_glob="*.txt",
            chabad_library_dir=tmp_path, chabad_library_history_book_ids=[]),
        chabadpedia_pages=ChabadpediaPages(dir=tmp_path),
        photos=PhotoSources(knowledge_graph_files=[]),
        output=OutputPaths(
            intermediate_dir=tmp_path / "i", cache_dir=tmp_path / "c",
            public_dir=tmp_path / "p", glossary_path=tmp_path / "g",
            significance_overrides_path=tmp_path / "l"),
    )


def test_review_lists_only_macro(tmp_path: Path):
    cfg = _cfg(tmp_path)
    cfg.output.intermediate_dir.mkdir(parents=True)
    import json
    payload = [
        {"id": "m1", "significance": 85, "date": {"y": 1812, "precision": "year"},
         "title_en": "Macro one", "summary_en": "s", "story_path": "p", "categories": ["rebbe"], "sources": [{"name": "x"}], "related": []},
        {"id": "x1", "significance": 25, "date": {"y": 1800, "precision": "year"},
         "title_en": "Micro one", "summary_en": "s", "story_path": "p", "categories": ["general"], "sources": [{"name": "x"}], "related": []},
    ]
    (cfg.output.intermediate_dir / "04_enriched.json").write_text(json.dumps(payload))
    out = generate_review(cfg)
    html = out.read_text(encoding="utf-8")
    assert "Macro one" in html
    assert "Micro one" not in html
