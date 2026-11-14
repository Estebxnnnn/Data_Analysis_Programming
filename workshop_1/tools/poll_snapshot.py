#!/usr/bin/env python
"""Take one snapshot of the incremental sources (run it TWICE, >= 1 hour apart).

Saves unmodified responses under workshop_1/samples/polls/<UTC stamp>/ :
    ibtracs_active.csv, gdacs_tc_current_pNN.json, nhc_CurrentStorms.json (+ .meta.json)
The second run sends the ETag / Last-Modified of the first one, so a 304
("not modified") is itself recorded as evidence.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from tcmon.http_client import PoliteClient  # noqa: E402
from tcmon.sources import gdacs, ibtracs, nhc  # noqa: E402

POLLS = ROOT / "workshop_1" / "samples" / "polls"


def previous_validators(name: str) -> tuple[str | None, str | None]:
    snaps = sorted(p for p in POLLS.glob("*") if p.is_dir())
    for snap in reversed(snaps):
        meta = snap / f"{name}.meta.json"
        if meta.exists():
            h = json.loads(meta.read_text())["headers"]
            return h.get("ETag"), h.get("Last-Modified")
    return None, None


def main() -> None:
    now = datetime.now(timezone.utc)
    out = POLLS / now.strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True, exist_ok=True)
    client = PoliteClient(min_interval=1.0)

    etag, lm = previous_validators("ibtracs_active.csv")
    # Unconditional GET (full body for diffing) + conditional GET (validator behaviour)
    r1 = client.fetch_to_file(ibtracs.url_for("ACTIVE"), out / "ibtracs_active.csv")
    r1c = client.fetch_to_file(ibtracs.url_for("ACTIVE"), out / "ibtracs_active_conditional.csv",
                               etag=etag, last_modified=lm) if (etag or lm) else None
    print("ibtracs_active", r1.status, r1.headers.get("Last-Modified"), r1.headers.get("ETag"),
          "| conditional:", r1c.status if r1c else "n/a (first poll)")

    today = now.date()
    for res in gdacs.fetch_window(client, today - timedelta(days=7), today, out):
        print("gdacs_tc_current", res.status, res.size_bytes, Path(res.path or "").name)

    r3 = client.fetch_to_file(nhc.URL, out / "nhc_CurrentStorms.json")
    print("nhc_current_storms", r3.status, r3.size_bytes)
    print(f"snapshot saved to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
