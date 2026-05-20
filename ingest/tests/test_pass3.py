import asyncio
import json
from pathlib import Path

from timeline_ingest.pass3_translate import translate_records, _format_glossary_block, TRANSLATION_SYSTEM_PROMPT
from timeline_ingest.schema import EventRecord, EventDate, EventSource


async def fake_call(client, *, system, user, model):
    return '[{"id": "abc", "title_en": "Alter Rebbe passes away", "summary_en": "Passing in 1812."}]'


def _rec() -> EventRecord:
    return EventRecord(
        id="abc",
        significance=25,
        date=EventDate(y=1812, precision="year"),
        title_en="",
        summary_en="נפטר אדמו\"ר הזקן",
        story_path="stories/abc.md",
        categories=["rebbe"],
        sources=[EventSource(name="x")],
    )


def test_glossary_block_format():
    block = _format_glossary_block({"rebbes": {"אדמו\"ר הזקן": "Alter Rebbe"}})
    assert "Alter Rebbe" in block
    assert "אדמו" in block


def test_translation_prompt_mentions_glossary_lock():
    assert "glossary" in TRANSLATION_SYSTEM_PROMPT.lower()


async def test_translate_fills_english_fields(tmp_path: Path):
    from timeline_ingest.llm import LLMClient
    client = LLMClient(cache_dir=tmp_path, _call=fake_call)
    records = [_rec()]
    glossary = {"rebbes": {"אדמו\"ר הזקן": "Alter Rebbe"}}
    translated = await translate_records(client, records, glossary=glossary)
    assert translated[0].title_en == "Alter Rebbe passes away"
    assert translated[0].summary_en == "Passing in 1812."
