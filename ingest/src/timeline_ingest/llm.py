"""Anthropic client wrapper: per-call disk cache + concurrency cap + retries.

Caching strategy: SHA256(system + user + model) → cache key. Hits skip the API.
Misses call the API, then write the response under cache_dir/<key>.txt.

Concurrency: bounded via an asyncio.Semaphore (default 20).
"""

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from pathlib import Path

import anthropic


CallFn = Callable[["LLMClient"], Awaitable[str]]


class LLMClient:
    def __init__(
        self,
        cache_dir: Path,
        *,
        max_concurrent: int = 20,
        _call: Callable | None = None,
    ) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._sem = asyncio.Semaphore(max_concurrent)
        self._call = _call or _default_call
        self._anthropic = anthropic.AsyncAnthropic() if _call is None else None

    def _key(self, *, system: str, user: str, model: str) -> Path:
        h = hashlib.sha256(f"{model}|{system}|{user}".encode("utf-8")).hexdigest()
        return self.cache_dir / f"{h}.txt"

    async def complete(self, *, system: str, user: str, model: str) -> str:
        cache_path = self._key(system=system, user=user, model=model)
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8")
        async with self._sem:
            response = await self._call(self, system=system, user=user, model=model)
        cache_path.write_text(response, encoding="utf-8")
        return response


async def _default_call(client: LLMClient, *, system: str, user: str, model: str) -> str:
    assert client._anthropic is not None
    msg = await client._anthropic.messages.create(
        model=model,
        max_tokens=4096,
        system=[
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}},
        ],
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")
