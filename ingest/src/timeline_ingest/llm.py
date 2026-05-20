"""LLM client wrapper: per-call disk cache + concurrency cap.

Default backend is the Claude Code CLI (`claude --print`), which bills against
the user's Max subscription instead of a standalone Anthropic API key. The
underlying model is whatever Claude Code's runtime picks (typically Opus 4.7).

If `ANTHROPIC_API_KEY` is set in the environment, the Anthropic Python SDK is
used directly instead — faster per call, but bills the API account.

Caching strategy: SHA256(system + user + model) → cache key. Hits skip the LLM.
Misses call the LLM, then write the response under cache_dir/<key>.txt.

Concurrency: bounded via an asyncio.Semaphore. Default lower for CLI backend
(process spawn overhead + Max subscription rate limits make ~5 a saner cap).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from collections.abc import Callable
from pathlib import Path


def _has_api_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


class LLMClient:
    def __init__(
        self,
        cache_dir: Path,
        *,
        max_concurrent: int | None = None,
        _call: Callable | None = None,
        backend: str | None = None,
    ) -> None:
        """`backend`: "sdk" (Anthropic API key required), "cli" (claude --print, uses Max),
        or None (auto-select: sdk if ANTHROPIC_API_KEY is set, else cli)."""
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if backend is None:
            backend = "sdk" if _has_api_key() else "cli"
        self.backend = backend

        if max_concurrent is None:
            max_concurrent = 20 if backend == "sdk" else 5
        self._sem = asyncio.Semaphore(max_concurrent)

        # Test-injection: caller may supply their own _call.
        if _call is not None:
            self._call = _call
            self._anthropic = None
            return

        if backend == "sdk":
            import anthropic
            self._anthropic = anthropic.AsyncAnthropic()
            self._call = _sdk_call
        elif backend == "cli":
            self._anthropic = None
            self._call = _cli_call
        else:
            raise ValueError(f"unknown backend {backend!r}")

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


async def _sdk_call(client: LLMClient, *, system: str, user: str, model: str) -> str:
    """Direct Anthropic API call. Requires ANTHROPIC_API_KEY."""
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


_CLI_MAX_BUDGET_USD = 5.0  # per-call belt-and-suspenders cap


async def _cli_call(client: LLMClient, *, system: str, user: str, model: str) -> str:
    """Call `claude --print`. Bills against Max subscription.

    Combines the (system, user) pair into a single prompt because the CLI
    doesn't expose a separate system slot the way the SDK does. The model
    argument is informational only — Claude Code picks the model itself.
    """
    prompt = f"{system}\n\n---\n\n{user}"

    proc = await asyncio.create_subprocess_exec(
        "claude",
        "--print",
        "--output-format", "json",
        "--no-session-persistence",
        "--max-budget-usd", str(_CLI_MAX_BUDGET_USD),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await proc.communicate(prompt.encode("utf-8"))
    if proc.returncode != 0:
        raise RuntimeError(
            f"claude exited {proc.returncode}: {stderr_bytes.decode('utf-8', errors='replace')[:500]}"
        )

    try:
        envelope = json.loads(stdout_bytes)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"claude returned non-JSON: {e}; first 500 bytes: {stdout_bytes[:500]!r}"
        )

    if envelope.get("is_error"):
        raise RuntimeError(
            f"claude reported error: {envelope.get('result', '<no result>')!r}"
        )

    result = envelope.get("result")
    if not isinstance(result, str):
        raise RuntimeError(f"claude envelope missing string result: {envelope!r}")
    return result
