# Raw samples (evidence)

Files here are **unmodified** responses (or a verbatim head of a large file),
each with a `.meta.json` sidecar: URL, UTC request time, HTTP status,
headers (`Last-Modified`, `ETag`, `Content-Length`, …), size and SHA-256.

Produced by:

```bash
python workshop_1/tools/collect_samples.py          # one real query per source
python workshop_1/tools/poll_snapshot.py            # incremental poll #1
# wait at least 1 hour (or until another day for slow sources)
python workshop_1/tools/poll_snapshot.py            # incremental poll #2
python workshop_1/tools/diff_snapshots.py           # -> workshop_1/evidence/poll_diff.md
```

| File | Source | Content |
| --- | --- | --- |
| `ibtracs_since1980_head.csv` | S1 | first 502 lines of the full file (header, units row if any, 500 fixes) |
| `ibtracs_active.csv` | S3 | full ACTIVE file (small) |
| `gdacs_tc_archive_gdacs_tc_<window>_p01.json` | S2 | first page of the first archive window |
| `gdacs_tc_current_*.json` | S4 | last-7-days pages |
| `nhc_CurrentStorms.json` | S5 | NHC feed (may be `{"activeStorms": []}`) |
| `polls/<UTC stamp>/` | S3, S4, S5 | the two incremental snapshots |

## Larger files (not committed)
The full `ibtracs.since1980.list.v04r01.csv` and all GDACS archive pages live in
`data/raw/<source>/<date>/` (git-ignored). Re-create them with
`python workshop_1/tools/collect_samples.py --only ibtracs_since1980 gdacs_tc_archive`.
Download them once and reuse the cache: do not re-download the archive needlessly.
