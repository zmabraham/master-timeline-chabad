import json
from pathlib import Path

from timeline_ingest.pass1_consolidate import consolidate
from timeline_ingest.config import Config, ExistingExtractions, BooksToExtract, ChabadpediaPages, PhotoSources, OutputPaths


def _cfg(tmp_path: Path, compact: Path, md: Path) -> Config:
    return Config(
        existing_extractions=ExistingExtractions(
            compact_json=compact,
            comprehensive_md=md,
            chabadpedia_kg_dir=tmp_path,
        ),
        books_to_extract=BooksToExtract(
            undaunted_dir=tmp_path,
            undaunted_chapters_glob="*.txt",
            chabad_library_dir=tmp_path,
            chabad_library_history_book_ids=[],
        ),
        chabadpedia_pages=ChabadpediaPages(dir=tmp_path),
        photos=PhotoSources(knowledge_graph_files=[]),
        output=OutputPaths(
            intermediate_dir=tmp_path / "intermediate",
            cache_dir=tmp_path / "cache",
            public_dir=tmp_path / "public",
            glossary_path=tmp_path / "g.yaml",
            significance_overrides_path=tmp_path / "l.yaml",
        ),
    )


def test_consolidate_merges_sources_and_writes_output(tmp_path: Path):
    fixtures = Path(__file__).parent / "fixtures"
    cfg = _cfg(tmp_path, fixtures / "compact_sample.json", fixtures / "comprehensive_sample.md")
    out_path = consolidate(cfg)
    assert out_path == tmp_path / "intermediate" / "01_consolidated.json"
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 2
    ids = {r["id"] for r in data}
    assert len(ids) == len(data)
