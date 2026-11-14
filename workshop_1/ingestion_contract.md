# Ingestion Contract — Team 4 (validated with real responses, 14 Nov 2026)

All writes are **upserts on a stable duplicate key**, so re-running any step is
safe. Raw responses are always saved (unmodified, with a `.meta.json` sidecar)
before parsing.

| Source | Historical strategy | Incremental strategy | Watermark | Polling | Overlap window | Duplicate key |
| --- | --- | --- | --- | --- | --- | --- |
| S1 `ibtracs_since1980` | Download the 145.4 MB CSV once per release; drop the units row; chunked parse; upsert in 287 `SEASON × BASIN` partitions | Weekly conditional GET; on a new release, upsert rows whose `record_hash` changed | `ETag` + `Last-Modified` | weekly | whole file | (`SID`, `ISO_TIME`) — verified unique (0 duplicates in 312,394 fixes, spurs included) |
| S2 `gdacs_tc_archive` | Monthly windows 2015–present; request pages until HTTP 204 (empty body); one raw file per page | — (covered by S4) | last completed month | one-off (~288 requests) | adjacent windows overlap at month boundaries | (`eventid`, `episodeid`) — dedupe across windows (14 repeats in 2024) |
| S3 `ibtracs_active` | — | Conditional GET (`If-None-Match`, `If-Modified-Since`); on 200 upsert all rows; storms that leave the file are aged out, not deleted | `ETag` / `Last-Modified` (304 verified); fallback SHA-256 | every 3 h | full file (7 days) | (`SID`, `ISO_TIME`) |
| S4 `gdacs_tc_current` | — | `SEARCH` from `watermark − 72 h` to today; changed `datemodified` or content hash updates the row | max `datemodified` (GDACS sends no HTTP validators) | hourly | 72 h (CEMPAKA-26 modified 37 h after its last position) | (`eventid`, `episodeid`) |
| S5 `nhc_current_storms` (optional) | recorded feeds as fixtures | GET with `If-None-Match`; new `lastUpdate` → new row | `ETag`, then max `lastUpdate` per storm | hourly in season, never below `max-age=300` | full feed | (`id`, `lastUpdate`) |

## Revisions and deletions
- IBTrACS provisional fixes (all 139 ACTIVE fixes; 10,811 in the archive) are revised and replaced on re-analysis: detected by `record_hash` per key.
- A fix missing from a new S1 release is soft-flagged `is_withdrawn = true`, never hard-deleted.
- GDACS updates create new episodes and may touch older ones (`datemodified`): hence the 72 h overlap.
- GDACS `severity` is the storm's peak wind so far; it is stored as `tc_alert.peak_wind_kt` and never used as current intensity.

## Failure recovery (run fails halfway)
1. `ingestion_run` row opened with `status = running`; raw response saved under `data/raw/<source>/<date>/`.
2. Each partition (season × basin, month, or one poll) is its own transaction.
3. `ingestion_state` is advanced in the same transaction as the last partition, only if all partitions succeeded.
4. On failure the run is marked `failed`; the next run restarts from the unchanged watermark and re-reads the cached raw file; upserts are idempotent.
5. Invalid records go to `rejected_record` (reason + raw payload) without blocking the partition.

## Empirical update behaviour (two polls, 73 minutes apart)
| Source | Poll 1 (UTC) | Poll 2 (UTC) | Validators changed? | Added | Modified | Removed |
| --- | --- | --- | --- | --- | --- | --- |
| S3 IBTrACS ACTIVE | 2026-11-14 18:28:48 | 19:41:33 | no — conditional GET returned 304 | 0 | 0 | 0 |
| S4 GDACS TC | 18:28:48 | 19:41:33 | n/a (none sent) | 0 | 0 | 0 |
| S5 NHC | 18:28:48 | 19:41:33 | no — same ETag and body hash | 0 | 0 | 0 |

No change is consistent with the documented release schedule (ACTIVE last released Thu 12 Nov 10:05 UTC). A third poll after the Sunday release will be appended to `evidence/poll_diff.md`.
