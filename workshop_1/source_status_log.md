# Source-Status Log

Record every change detected in a source (URL moved, new version, renamed field,
outage, license change) and report it to the professor as soon as it is detected.

| Date (UTC) | Source | Observation | Evidence (file / URL) | Impact on the project | Reported to professor |
| --- | --- | --- | --- | --- | --- |
| 2026-11-03 | all | Baseline: sources listed in the Team Project Assignment, checked by the professor on this date | TeamsDistribution.pdf | — | n/a |
| 2026-11-14 | IBTrACS since1980 | URL valid (HTTP 200); release `Last-Modified: Thu, 12 Nov 2026 10:06:32 GMT`, 145,369,034 bytes | `samples/ibtracs_since1980_head.csv.meta.json` | None | n/a |
| 2026-11-14 | IBTrACS since1980 | `TRACK_TYPE` uses `spur-merge`, `spur-split`, `spur-other`, `US-PROVISIONAL_spur` (documentation lists `spur`) | notebook §3 | Filter on "contains spur" | no (documentation detail) |
| 2026-11-14 | IBTrACS ACTIVE | URL valid; `Last-Modified: Thu, 12 Nov 2026 10:05:25 GMT`; conditional GET → 304 | `samples/polls/20261114T194133Z/ibtracs_active_conditional.csv.meta.json` | None | n/a |
| 2026-11-14 | GDACS API | End of pagination = HTTP 204 (empty body); page size 100; no ETag / Last-Modified / rate-limit headers | `evidence/access_log.csv`, `evidence/gdacs_coverage_probe.csv` | Pagination loop stops on 204; watermark = `datemodified` | n/a |
| 2026-11-14 | GDACS API | Tropical-cyclone archive empty for 1995–2005 and 2010, one event in 2008, full pages from 2015 | `evidence/gdacs_coverage_probe.csv` | GDACS used from 2015 onward | **yes — include in the Workshop 1 questions** |
| 2026-11-14 | NHC CurrentStorms.json | Valid empty feed `{"activeStorms": []}`; `Cache-Control: max-age=300` | `samples/nhc_CurrentStorms.json` | Optional source; expected off-season | n/a |
