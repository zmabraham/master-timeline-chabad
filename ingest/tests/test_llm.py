import asyncio
from pathlib import Path

from timeline_ingest.llm import LLMClient


async def test_cache_hit_skips_call(tmp_path: Path, monkeypatch):
    calls = {"n": 0}

    async def fake_call(client, *, system, user, model):
        calls["n"] += 1
        return f"response-{calls['n']}"

    client = LLMClient(cache_dir=tmp_path, _call=fake_call)
    resp1 = await client.complete(system="sys", user="hello", model="claude-haiku-4-5-20251001")
    resp2 = await client.complete(system="sys", user="hello", model="claude-haiku-4-5-20251001")
    assert resp1 == resp2 == "response-1"
    assert calls["n"] == 1


async def test_different_payload_misses_cache(tmp_path: Path):
    calls = {"n": 0}

    async def fake_call(client, *, system, user, model):
        calls["n"] += 1
        return f"response-{calls['n']}"

    client = LLMClient(cache_dir=tmp_path, _call=fake_call)
    await client.complete(system="sys", user="hello", model="m")
    await client.complete(system="sys", user="hi", model="m")
    assert calls["n"] == 2
