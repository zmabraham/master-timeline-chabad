import asyncio
import json
from pathlib import Path

from timeline_ingest.pass2_extract import run_pass2
from timeline_ingest.config import Config, ExistingExtractions, BooksToExtract, ChabadpediaPages, PhotoSources, OutputPaths


async def fake_call(client, *, system, user, model):
    suffix = abs(hash(user)) % 10_000
    return (
        f'[{{"title": "Fake event {suffix}", "year": 1800, "month": null, "day": null, '
        f'"categories": ["general"], "summary": "x", "story": "y"}}]'
    )


def _cfg(tmp_path: Path) -> Config:
    book = tmp_path / "books" / "u_chapter1.txt"
    book.parent.mkdir(parents=True, exist_ok=True)
    book.write_text("some chapter text", encoding="utf-8")

    pages_dir = tmp_path / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / "Alter_Rebbe.txt").write_text("Some bio text.", encoding="utf-8")

    return Config(
        existing_extractions=ExistingExtractions(
            compact_json=tmp_path / "x.json",
            comprehensive_md=tmp_path / "y.md",
            chabadpedia_kg_dir=tmp_path,
        ),
        books_to_extract=BooksToExtract(
            undaunted_dir=tmp_path / "books",
            undaunted_chapters_glob="u_chapter*.txt",
            chabad_library_dir=tmp_path / "lib",
            chabad_library_history_book_ids=[],
        ),
        chabadpedia_pages=ChabadpediaPages(dir=pages_dir),
        photos=PhotoSources(knowledge_graph_files=[]),
        output=OutputPaths(
            intermediate_dir=tmp_path / "intermediate",
            cache_dir=tmp_path / "cache",
            public_dir=tmp_path / "public",
            glossary_path=tmp_path / "g.yaml",
            significance_overrides_path=tmp_path / "l.yaml",
        ),
    )


async def test_run_pass2_writes_extracted(tmp_path: Path):
    cfg = _cfg(tmp_path)
    out = await run_pass2(cfg, _call_override=fake_call)
    assert out == tmp_path / "intermediate" / "02_extracted.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    sources_seen = {s["name"] for rec in data for s in rec["sources"]}
    assert any(s == "Undaunted" for s in sources_seen)
    assert any(s.startswith("Chabadpedia/") for s in sources_seen)
