"""Strongly-typed loader for sources.yaml."""

from pathlib import Path

import yaml
from pydantic import BaseModel


class ExistingExtractions(BaseModel):
    compact_json: Path
    comprehensive_md: Path
    chabadpedia_kg_dir: Path


class BooksToExtract(BaseModel):
    undaunted_dir: Path
    undaunted_chapters_glob: str
    chabad_library_dir: Path
    chabad_library_history_book_ids: list[str]


class ChabadpediaPages(BaseModel):
    dir: Path


class PhotoSources(BaseModel):
    knowledge_graph_files: list[dict[str, Path]]


class OutputPaths(BaseModel):
    intermediate_dir: Path
    cache_dir: Path
    public_dir: Path
    glossary_path: Path
    significance_overrides_path: Path


class Config(BaseModel):
    existing_extractions: ExistingExtractions
    books_to_extract: BooksToExtract
    chabadpedia_pages: ChabadpediaPages
    photos: PhotoSources
    output: OutputPaths


def load_config(path: Path = Path("sources.yaml")) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Config.model_validate(raw)
