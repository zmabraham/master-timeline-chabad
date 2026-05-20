"""Split long texts into ~max_chars chunks at paragraph boundaries."""

from collections.abc import Iterator


def chunk_by_chars(text: str, *, max_chars: int = 24000) -> Iterator[str]:
    """Yield chunks of approximately max_chars, splitting at \\n\\n boundaries."""
    paragraphs = text.split("\n\n")
    buf: list[str] = []
    buf_len = 0
    for p in paragraphs:
        if buf and buf_len + len(p) > max_chars:
            yield "\n\n".join(buf)
            buf = [p]
            buf_len = len(p)
        else:
            buf.append(p)
            buf_len += len(p) + 2
    if buf:
        yield "\n\n".join(buf)
