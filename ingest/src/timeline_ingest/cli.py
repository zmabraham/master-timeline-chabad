"""Command-line entrypoint: `python -m timeline_ingest <pass>`."""

import argparse
import asyncio
import sys
from pathlib import Path

from timeline_ingest.config import load_config
from timeline_ingest.pass1_consolidate import consolidate
from timeline_ingest.pass2_extract import run_pass2
from timeline_ingest.pass3_translate import run_pass3
from timeline_ingest.pass4_enrich import run_pass4


def _pass2_sync(cfg):
    return asyncio.run(run_pass2(cfg))


def _pass3_sync(cfg):
    return asyncio.run(run_pass3(cfg))


PASSES = {
    "pass1": consolidate,
    "pass2": _pass2_sync,
    "pass3": _pass3_sync,
    "pass4": run_pass4,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="timeline_ingest")
    parser.add_argument(
        "pass_name",
        choices=sorted(PASSES.keys()),
        help="which pass to run",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("sources.yaml"),
        help="path to sources.yaml",
    )
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    func = PASSES[args.pass_name]
    out = func(cfg)
    print(f"OK → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
