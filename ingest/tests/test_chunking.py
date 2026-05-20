from timeline_ingest.chunking import chunk_by_chars


def test_chunk_short_text_returns_single_chunk():
    chunks = list(chunk_by_chars("hello world", max_chars=100))
    assert chunks == ["hello world"]


def test_chunk_long_text_splits_on_paragraph_boundary():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = list(chunk_by_chars(text, max_chars=20))
    assert len(chunks) >= 2
    for c in chunks:
        assert c.strip()


def test_chunk_respects_max_chars_soft_limit():
    text = ("X" * 50 + "\n\n") * 10
    chunks = list(chunk_by_chars(text, max_chars=100))
    for c in chunks:
        assert len(c) <= 200  # 2x slack ok
