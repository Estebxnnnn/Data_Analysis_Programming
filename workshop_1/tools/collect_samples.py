#!/usr/bin/env python
"""Collect REAL raw samples from the four sources (+ optional NHC) as Workshop 1 evidence.

Every response is saved byte-for-byte with a sidecar .meta.json (URL, UTC time,
HTTP status, headers, size, SHA-256). Large files go to data/raw/ (git-ignored);
small files or a verbatim head of large files go to workshop_1/samples/.

Usage (from the repository root):
    python workshop_1/tools/collect_samples.py                    # all sources
    python workshop_1/tools/collect_samples.py --only ibtracs_active gdacs_tc_current
    python workshop_1/tools/collect_samples.py --gdacs-year 2024  # archive window
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from tcmon.http_client import PoliteClient  # noqa: E402
from tcmon.sources import gdacs, ibtracs, nhc  # noqa: E402
from tcmon.storage import landing_path  # noqa: E402

SAMPLES = ROOT / "workshop_1" / "samples"
EVIDENCE = ROOT / "workshop_1" / "evidence"
HEAD_LINES = 502  # header + possible units row + 500 records


def copy_head(src: Path, dest: Path, n_lines: int = HEAD_LINES) -> None:
    """Verbatim first n lines of a large text file (unmodified bytes)."""
    with open(src, "rb") as fi, open(dest, "wb") as fo:
        for i, line in enumerate(fi):
            if i >= n_lines:
                break
            fo.write(line)


def copy_with_meta(src: str, dest: Path) -> None:
    shutil.copyfile(src, dest)
    shutil.copyfile(src + ".meta.json", str(dest) + ".meta.json")


def run(only: list[str] | None, gdacs_year: int) -> list[dict]:
    client = PoliteClient(min_interval=1.0)
    SAMPLES.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    log = []

    def want(name):
        return not only or name in only

    if want("ibtracs_since1980"):
        dest = landing_path("ibtracs_since1980", ibtracs.SUBSET_FILES["since1980"])
        res = client.fetch_to_file(ibtracs.url_for("since1980"), dest)
        log.append({"source": "ibtracs_since1980", **res.to_dict()})
        if res.status == 200:
            copy_head(dest, SAMPLES / "ibtracs_since1980_head.csv")
            shutil.copyfile(res.meta_path, SAMPLES / "ibtracs_since1980_head.csv.meta.json")

    if want("ibtracs_active"):
        dest = landing_path("ibtracs_active", ibtracs.SUBSET_FILES["ACTIVE"])
        res = client.fetch_to_file(ibtracs.url_for("ACTIVE"), dest)
        log.append({"source": "ibtracs_active", **res.to_dict()})
        if res.status == 200:
            copy_with_meta(res.path, SAMPLES / "ibtracs_active.csv")

    if want("gdacs_tc_archive"):
        out = landing_path("gdacs_tc_archive", "")
        for month in range(1, 13):
            start = date(gdacs_year, month, 1)
            end = (date(gdacs_year + (month == 12), month % 12 + 1, 1) - timedelta(days=1))
            for res in gdacs.fetch_window(client, start, end, out):
                log.append({"source": "gdacs_tc_archive", **res.to_dict()})
        first = sorted(out.glob(f"gdacs_tc_{gdacs_year}-*_p01.json"))
        if first:
            copy_with_meta(str(first[0]), SAMPLES / f"gdacs_tc_archive_{first[0].name}")

    if want("gdacs_tc_current"):
        today = datetime.now(timezone.utc).date()
        out = landing_path("gdacs_tc_current", "")
        for res in gdacs.fetch_window(client, today - timedelta(days=7), today, out):
            log.append({"source": "gdacs_tc_current", **res.to_dict()})
            if res.status == 200 and res.path:
                copy_with_meta(res.path, SAMPLES / f"gdacs_tc_current_{Path(res.path).name}")

    if want("nhc_current_storms"):
        dest = landing_path("nhc_current_storms", "CurrentStorms.json")
        res = client.fetch_to_file(nhc.URL, dest)
        log.append({"source": "nhc_current_storms", **res.to_dict()})
        if res.status == 200:
            copy_with_meta(res.path, SAMPLES / "nhc_CurrentStorms.json")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (EVIDENCE / f"collection_log_{stamp}.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    return log


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="subset of source ids")
    ap.add_argument("--gdacs-year", type=int, default=2024)
    args = ap.parse_args()
    for entry in run(args.only, args.gdacs_year):
        print(f"{entry['source']:20s} {entry['status']}  {entry['size_bytes']:>12,d} B  "
              f"{entry['headers'].get('Last-Modified', '-'):32s} {entry['url'][:90]}")
