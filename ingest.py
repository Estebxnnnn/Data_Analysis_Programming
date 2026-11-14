#!/usr/bin/env python
"""Command-line entry point for TC-Analog Monitor ingestion.

Workshop 1 status: STUB. The CLI contract is fixed now; the pipeline steps are
implemented in Workshop 2 (historical) and Workshop 3 (incremental).

Usage:
    python ingest.py --mode historical [--source ibtracs_since1980] [--dry-run]
    python ingest.py --mode incremental [--source gdacs_tc_current] [--dry-run]
    python ingest.py --list-sources
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tcmon.config import load_sources  # noqa: E402

PLAN = {
    "historical": [
        "open ingestion_run (status=running)",
        "download raw file / paginate date windows -> data/raw/<source>/<date>/",
        "parse + normalize to canonical event (UTC, WGS84, kt)",
        "validate; invalid rows -> rejected_record",
        "upsert per partition (SEASON x BASIN, or month) in its own transaction",
        "update ingestion_state only if every partition succeeded",
        "close ingestion_run (status=success|failed)",
    ],
    "incremental": [
        "read ingestion_state watermark (ETag/Last-Modified or datemodified)",
        "conditional GET / query from watermark minus overlap window",
        "save raw response; 304 or empty feed = success with 0 rows",
        "normalize, hash records, detect new vs modified",
        "upsert by duplicate key; flag withdrawn records (never hard-delete)",
        "advance watermark in the same transaction as the last write",
    ],
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=["historical", "incremental"])
    parser.add_argument("--source", help="source id from config/sources.yaml (default: all of that role)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan without running it")
    parser.add_argument("--list-sources", action="store_true")
    args = parser.parse_args(argv)

    cfg = load_sources()["sources"]
    if args.list_sources:
        for sid, s in cfg.items():
            print(f"{sid:22s} {s['role']:22s} {s['format']:8s} watermark={s.get('watermark')}")
        return 0
    if not args.mode:
        parser.error("--mode is required (or use --list-sources)")

    role = args.mode
    targets = [args.source] if args.source else [k for k, v in cfg.items()
                                                  if v["role"] == role and v.get("enabled", True)]
    unknown = [t for t in targets if t not in cfg]
    if unknown:
        parser.error(f"unknown source(s): {unknown}")

    print(f"[ingest] mode={role} sources={targets}")
    for step in PLAN[role]:
        print(f"  - {step}")
    if args.dry_run:
        return 0
    print("[ingest] Not implemented yet: scheduled for Workshop 2 (historical) / Workshop 3 (incremental).")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
