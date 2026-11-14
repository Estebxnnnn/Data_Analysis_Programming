# Test fixtures

Recorded responses used by the tests. **Only real responses captured from the
sources go here** (plus the documented empty NHC feed). Each fixture keeps its
sidecar `.meta.json` (URL, UTC time, status, headers, SHA-256) written by
`tcmon.http_client.PoliteClient.fetch_to_file`.

| File | Origin | Purpose |
| --- | --- | --- |
| `nhc_current_storms_empty.json` | Documented valid response when no storm is active (NHC Tropical Cyclone Status JSON File Reference) | Empty-feed handling |
| `nhc_current_storms_20261114.json` | Real response, 2026-11-14 18:32 UTC (empty feed) | Empty-feed handling |
| `ibtracs_active_20261114.csv` | Real response, 2026-11-14 18:31 UTC (139 fixes, 3 storms) | Units row, blanks, provisional data |
| `gdacs_tc_current_20261114.json` | Real response, 2026-11-14 18:32 UTC (3 features) | km/h severity, UTC times, peak wind |
| `nhc_current_storms_<storm>.json` | *to be recorded during an active Atlantic/EPac storm* | Live-storm replay off-season |

The Atlantic and Eastern Pacific seasons end on 30 November: keep every feed
recorded during a live storm, so that tests and demos can replay it later.
