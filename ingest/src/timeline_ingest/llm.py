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

# When `claude --print` errors with a rate-limit / usage-limit signal, sleep
# this long before retrying. Max's window is 5 hours; we conservatively wait
# 90 minutes so we don't burn through quota in a tight retry loop, and we
# don't park forever in case the limit was a transient blip.
_CLI_RATELIMIT_SLEEP_S = 90 * 60
# Cap retries on persistent rate limits — eventually surface the failure
# rather than spinning silently for days.
_CLI_RATELIMIT_MAX_RETRIES = 6


def _is_rate_limit_error(envelope: dict, stderr_text: str = "") -> bool:
    """Best-effort detection of rate-limit / usage-cap signals from claude --print."""
    signal = " ".join(
        str(envelope.get(k, "")) for k in ("result", "api_error_status", "stop_reason")
    ) + " " + stderr_text
    s = signal.lower()
    return any(needle in s for needle in (
        "rate limit", "rate-limit", "rate_limit",
        "usage limit", "usage_limit",
        "429", "quota", "too many requests",
        "session limit", "5-hour", "five-hour",
    ))


async def _cli_call(client: LLMClient, *, system: str, user: str, model: str) -> str:
    """Call `claude --print`. Bills against Max subscription.

    Combines the (system, user) pair into a single prompt because the CLI
    doesn't expose a separate system slot the way the SDK does. The model
    argument is informational only — Claude Code picks the model itself.

    On rate-limit errors, sleeps `_CLI_RATELIMIT_SLEEP_S` and retries.
    Non-rate-limit errors raise immediately. Caches are written only on success
    (handled by LLMClient.complete), so retries don't double-write.
    """
    prompt = f"{system}\n\n---\n\n{user}"
    last_err: str | None = None

    for attempt in range(_CLI_RATELIMIT_MAX_RETRIES + 1):
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
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")

        # Non-JSON stdout: treat as transient infra issue, retry if rate-limit-flavored.
        try:
            envelope = json.loads(stdout_bytes)
        except json.JSONDecodeError:
            envelope = {"is_error": True, "result": stdout_bytes[:500].decode("utf-8", errors="replace")}

        if proc.returncode != 0 or envelope.get("is_error"):
            last_err = f"rc={proc.returncode} result={envelope.get('result', '<none>')!r} stderr={stderr_text[:200]!r}"
            if _is_rate_limit_error(envelope, stderr_text):
                if attempt < _CLI_RATELIMIT_MAX_RETRIES:
                    print(
                        f"[llm] rate-limit hit (attempt {attempt + 1}/"
                        f"{_CLI_RATELIMIT_MAX_RETRIES + 1}); sleeping "
                        f"{_CLI_RATELIMIT_SLEEP_S}s then retrying. signal={last_err[:200]}",
                        flush=True,
                    )
                    await asyncio.sleep(_CLI_RATELIMIT_SLEEP_S)
                    continue
            # Non-rate-limit error, or out of retries: raise.
            raise RuntimeError(f"claude failed: {last_err}")

        result = envelope.get("result")
        if not isinstance(result, str):
            raise RuntimeError(f"claude envelope missing string result: {envelope!r}")
        return result

    # Exhausted retries — last_err set above.
    raise RuntimeError(f"claude failed after {_CLI_RATELIMIT_MAX_RETRIES + 1} attempts: {last_err}")
