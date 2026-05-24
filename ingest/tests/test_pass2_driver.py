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


async def fake_call_with_day_no_month(client, *, system, user, model):
    # Real-world regression: the LLM sometimes returns day without month
    # ({"year":1950,"month":null,"day":10}). The schema's inverse-precision
    # validator rejects that — _row_to_record must normalize it down.
    return '[{"title": "Event with day but no month", "year": 1950, "month": null, "day": 10, "categories": ["rebbe"], "summary": "s", "story": "x"}]'


async def test_extract_book_handles_day_without_month(tmp_path: Path):
    book_path = tmp_path / "book.txt"
    book_path.write_text("text.", encoding="utf-8")
    client = LLMClient(cache_dir=tmp_path / "cache", _call=fake_call_with_day_no_month)
    records = await extract_book(client, book_path, source_name="Book")
    assert len(records) == 1
    r = records[0]
    assert r.date.y == 1950
    assert r.date.precision == "year"  # day dropped because month is missing
    assert r.date.m is None
    assert r.date.d is None


async def fake_call_with_invalid_month(client, *, system, user, model):
    # LLM occasionally returns month=0 or month=13.
    return '[{"title": "Bad month", "year": 1880, "month": 13, "day": 5, "categories": ["general"], "summary": "s", "story": "x"}]'


async def test_extract_book_handles_invalid_month(tmp_path: Path):
    book_path = tmp_path / "book.txt"
    book_path.write_text("text.", encoding="utf-8")
    client = LLMClient(cache_dir=tmp_path / "cache", _call=fake_call_with_invalid_month)
    records = await extract_book(client, book_path, source_name="Book")
    assert len(records) == 1
    assert records[0].date.precision == "year"
    assert records[0].date.m is None and records[0].date.d is None
