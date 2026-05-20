.PHONY: install test lint pass1 pass2 pass3 pass4 pass5 review all clean

install:
	uv sync

test:
	uv run pytest -v

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

pass1:
	uv run python -m timeline_ingest pass1

pass2:
	uv run python -m timeline_ingest pass2

pass3:
	uv run python -m timeline_ingest pass3

pass4:
	uv run python -m timeline_ingest pass4

review:
	uv run python -m timeline_ingest review

pass5:
	uv run python -m timeline_ingest pass5

all: pass1 pass2 pass3 pass4 review pass5

clean:
	rm -rf intermediate/* cache/*
