#!/usr/bin/env python
"""Compare two poll snapshots and write workshop_1/evidence/poll_diff.md.

Usage:
    python workshop_1/tools/diff_snapshots.py                 # two most recent snapshots
    python workshop_1/tools/diff_snapshots.py OLD_DIR NEW_DIR
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from tcmon.sources import gdacs, ibtracs, nhc  # noqa: E402

POLLS = ROOT / "workshop_1" / "samples" / "polls"
OUT = ROOT / "workshop_1" / "evidence" / "poll_diff.md"


def _meta(snap: Path, name: str) -> dict:
    p = snap / f"{name}.meta.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _row_hashes(df: pd.DataFrame, key: list[str]) -> dict:
    if df.empty:
        return {}
    out = {}
    for rec in df.to_dict(orient="records"):
        vals = ["" if v is None or (isinstance(v, float) and v != v) else str(v) for v in rec.values()]
        out[tuple(str(rec[k]) for k in key)] = hashlib.sha256("|".join(vals).encode()).hexdigest()
    return out


def _compare(old: dict, new: dict) -> tuple[int, int, int, list]:
    added = [k for k in new if k not in old]
    removed = [k for k in old if k not in new]
    modified = [k for k in new if k in old and new[k] != old[k]]
    return len(added), len(modified), len(removed), (added + modified + removed)[:5]


def load_ibtracs(snap):
    p = snap / "ibtracs_active.csv"
    return ibtracs.read_csv(p, usecols=list(pd.read_csv(p, nrows=0).columns), keep_raw_text=True) \
        if p.exists() else pd.DataFrame()


def load_gdacs(snap):
    feats = [f for p in sorted(snap.glob("gdacs_tc_*_p*.json")) for f in gdacs.load_features(p)]
    return gdacs.features_to_frame(feats)


def load_nhc(snap):
    p = snap / "nhc_CurrentStorms.json"
    return nhc.storms_to_frame(nhc.load(p)) if p.exists() else pd.DataFrame()


def main(argv):
    snaps = [Path(a) for a in argv] if len(argv) == 2 else sorted(p for p in POLLS.glob("*") if p.is_dir())[-2:]
    if len(snaps) != 2:
        sys.exit("Need two snapshots: run poll_snapshot.py twice, >= 1 hour apart.")
    old, new = snaps
    rows = []
    specs = [
        ("S3 IBTrACS ACTIVE", "ibtracs_active.csv", load_ibtracs, ["SID", "ISO_TIME"]),
        ("S4 GDACS TC", None, load_gdacs, ["eventid", "episodeid"]),
        ("S5 NHC (optional)", "nhc_CurrentStorms.json", load_nhc, ["id"]),
    ]
    for label, metafile, loader, key in specs:
        mo, mn = (_meta(old, metafile), _meta(new, metafile)) if metafile else ({}, {})
        validators = "n/a"
        if mo and mn:
            ho, hn = mo.get("headers", {}), mn.get("headers", {})
            validators = "yes" if (ho.get("ETag"), ho.get("Last-Modified")) != \
                (hn.get("ETag"), hn.get("Last-Modified")) else "no"
            validators += "; body hash " + ("changed" if mo.get("sha256") != mn.get("sha256") else "same")
        a, m, r, examples = _compare(_row_hashes(loader(old), key), _row_hashes(loader(new), key))
        rows.append(f"| {label} | {old.name} | {new.name} | {validators} | {a} | {m} | {r} | "
                    f"{'; '.join(map(str, examples)) or 'no change'} |")
    md = ["# Poll comparison (generated)", "",
          "| Source | Poll 1 (UTC) | Poll 2 (UTC) | HTTP validators changed? | Added | Modified | Removed | Example keys |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |", *rows, ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main(sys.argv[1:])
