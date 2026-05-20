import json
from pathlib import Path

from timeline_ingest.pass5_emit import run_pass5
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


def test_pass5_writes_events_and_stories(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.output.intermediate_dir.mkdir(parents=True)
    payload = [
        {
            "id": "abc", "significance": 85,
            "date": {"y": 1812, "precision": "year"},
            "title_en": "Alter Rebbe passes",
            "summary_en": "Summary.",
            "story_body": "Full story paragraph one. And paragraph two.",
            "story_path": "stories/abc.md",
            "categories": ["rebbe"],
            "sources": [{"name": "x"}],
            "related": [],
        },
        {
            "id": "xyz", "significance": 25,
            "date": {"y": 1813, "precision": "year"},
            "title_en": "Letter to a chossid",
            "summary_en": "Fallback summary text.",
            "story_body": None,
            "story_path": "stories/xyz.md",
            "categories": ["general"],
            "sources": [{"name": "x"}],
            "related": [],
        },
    ]
    (cfg.output.intermediate_dir / "04_enriched.json").write_text(json.dumps(payload))
    run_pass5(cfg)

    events_path = cfg.output.public_dir / "events.json"
    assert events_path.exists()
    stored = json.loads(events_path.read_text())
    assert {r["id"] for r in stored} == {"abc", "xyz"}

    story_abc = (cfg.output.public_dir / "stories" / "abc.md").read_text()
    assert "Full story paragraph one." in story_abc

    story_xyz = (cfg.output.public_dir / "stories" / "xyz.md").read_text()
    assert "Fallback summary text." in story_xyz
