import json
from pathlib import Path

from timeline_ingest.pass4_enrich import run_pass4
from timeline_ingest.config import Config, ExistingExtractions, BooksToExtract, ChabadpediaPages, PhotoSources, OutputPaths
from timeline_ingest.schema import EventRecord, EventDate, EventSource


def _cfg(tmp_path: Path) -> Config:
    return Config(
        existing_extractions=ExistingExtractions(
            compact_json=tmp_path / "x", comprehensive_md=tmp_path / "y", chabadpedia_kg_dir=tmp_path),
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


def test_run_pass4_emits_enriched(tmp_path: Path):
    cfg = _cfg(tmp_path)
    cfg.output.intermediate_dir.mkdir(parents=True)
    rec = EventRecord(
        id="abc", significance=0,
        date=EventDate(y=1812, precision="year"),
        title_en="Alter Rebbe passes away", summary_en="",
        story_path="stories/abc.md", categories=["rebbe"],
        sources=[EventSource(name="t")],
    )
    p3 = cfg.output.intermediate_dir / "03_translated.json"
    p3.write_text(json.dumps([rec.model_dump(mode="json")]), encoding="utf-8")
    cfg.output.significance_overrides_path.write_text("overrides: {}\n", encoding="utf-8")

    out = run_pass4(cfg)
    assert out == cfg.output.intermediate_dir / "04_enriched.json"
    data = json.loads(out.read_text())
    assert data[0]["significance"] >= 80
