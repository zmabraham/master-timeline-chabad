import asyncio
from pathlib import Path

from timeline_ingest.llm import LLMClient
from timeline_ingest.pass2_extract import extract_book


async def fake_call(client, *, system, user, model):
    return '[{"title": "Test event", "year": 1812, "month": null, "day": null, "categories": ["rebbe"], "summary": "s", "story": "story body"}]'


async def test_extract_book_returns_records(tmp_path: Path):
    book_path = tmp_path / "book.txt"
    book_path.write_text("Some long text.\n\nAnother paragraph.", encoding="utf-8")
    client = LLMClient(cache_dir=tmp_path / "cache", _call=fake_call)
    records = await extract_book(client, book_path, source_name="Book")
    assert len(records) >= 1
    assert records[0].title_en == "Test event"
    assert records[0].date.y == 1812
    assert records[0].sources[0].name == "Book"
