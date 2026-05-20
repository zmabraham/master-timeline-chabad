from pathlib import Path

from timeline_ingest.config import load_config


def test_load_config_returns_sources(tmp_path: Path):
    yml = tmp_path / "sources.yaml"
    yml.write_text(
        "existing_extractions:\n"
        "  compact_json: /a\n"
        "  comprehensive_md: /b\n"
        "  chabadpedia_kg_dir: /c\n"
        "books_to_extract:\n"
        "  undaunted_dir: /u\n"
        "  undaunted_chapters_glob: 'foo*.txt'\n"
        "  chabad_library_dir: /cl\n"
        "  chabad_library_history_book_ids: ['1']\n"
        "chabadpedia_pages:\n"
        "  dir: /cp\n"
        "photos:\n"
        "  knowledge_graph_files: []\n"
        "output:\n"
        "  intermediate_dir: intermediate\n"
        "  cache_dir: cache\n"
        "  public_dir: ../public\n"
        "  glossary_path: glossary.yaml\n"
        "  significance_overrides_path: significance_overrides.yaml\n"
    )
    cfg = load_config(yml)
    assert cfg.existing_extractions.compact_json == Path("/a")
    assert cfg.books_to_extract.chabad_library_history_book_ids == ["1"]
    assert cfg.output.intermediate_dir == Path("intermediate")
