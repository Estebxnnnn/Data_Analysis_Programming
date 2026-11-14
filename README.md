# TC-Analog Monitor

**Multi-source ingestion and analysis system for global tropical-cyclone monitoring.**
Data Analysis Programming · Semester 2026-II · Universidad Distrital Francisco José de Caldas ·
Instructor: Eng. Carlos Andrés Sierra, M.Sc.

## Hazard
Tropical cyclones (tropical depressions, tropical storms, hurricanes/typhoons/cyclones), **global scope**,
historical window **1980–present**. Severity = maximum sustained wind in **knots** (secondary: minimum central
pressure in hPa). Team output: **comparison of the current storm with similar historical storms** (Storm Analog
Similarity, SAS). The system monitors and compares; it does **not** forecast.

## Team 4
| Student ID | Name |
| --- | --- |
| 20222020108 | Omar Peña |
| 20222020134 | Rosa López |
| 20222020139 | Brayan Ramírez |

## Sources
| ID | Role | Source | Format | Watermark |
| --- | --- | --- | --- | --- |
| S1 | Historical | [IBTrACS v04r01](https://www.ncei.noaa.gov/node/1660) `since1980` (NOAA NCEI) | CSV | ETag / Last-Modified |
| S2 | Historical | GDACS tropical-cyclone events, archive 2015–present (`gdacsapi` SEARCH) | GeoJSON | last completed month |
| S3 | Incremental | IBTrACS v04r01 `ACTIVE` (storms active in the last 7 days) | CSV | ETag / Last-Modified |
| S4 | Incremental | GDACS tropical-cyclone events, last 7 days | GeoJSON | `datemodified` |
| S5 | Optional | NHC [`CurrentStorms.json`](https://www.nhc.noaa.gov/CurrentStorms.json) (Atlantic, E/C Pacific) | JSON | `lastUpdate` |

Full details, licenses and attribution: [`config/sources.yaml`](config/sources.yaml).

**Attribution.** IBTrACS: Knapp et al. (2010), *BAMS* 91, 363–376, doi:10.1175/2009BAMS2755.1; Gahtan et al. (2024),
IBTrACS v04r01, NOAA NCEI, doi:10.25921/82ty-9e16. GDACS: Global Disaster Alert and Coordination System, a cooperation
framework of the UN and the European Commission. NHC: NOAA National Hurricane Center.

## Repository structure
```
.
├── ingest.py                 # CLI entry point (stub): --mode historical | incremental
├── config/sources.yaml       # one entry per source: URL, format, schedule, watermark, license
├── src/tcmon/                # ingestion package
│   ├── http_client.py        # polite client: UA, throttling, retries, conditional GET, raw + .meta.json
│   ├── sources/              # ibtracs.py, gdacs.py, nhc.py
│   ├── normalization/        # units.py, canonical.py (canonical event model)
│   └── storage/              # landing zone paths (DB writer in Workshop 2)
├── data/raw/                 # raw landing zone (git-ignored)
├── sql/001_schema_draft.sql  # schema draft (common + domain tables)
├── dashboard/app.py          # Plotly Dash stub (localhost:8050)
├── tests/                    # pytest; tests/fixtures/ = recorded responses
├── notebooks/01_source_profiling.ipynb
├── docs/architecture.md      # architecture overview + diagram
├── docs/report/              # Workshop 1 report: IEEE-format PDF + LaTeX source
├── workshop_1/               # mapping, ER diagram, ingestion contract, samples, evidence, tools
├── .env.example
└── requirements.txt
```

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                     # set TCMON_USER_AGENT with a contact e-mail
python -m pytest -q                      # 28 tests, offline (incl. recorded real responses)
python ingest.py --list-sources
python ingest.py --mode historical --dry-run
python workshop_1/tools/collect_samples.py   # real queries -> workshop_1/samples, data/raw
jupyter notebook notebooks/01_source_profiling.ipynb
python dashboard/app.py                  # http://localhost:8050 (stub)
```

## Status
| Workshop | Scope | Status |
| --- | --- | --- |
| 1 | Hazard definition, four sources validated, profiling, canonical mapping, ingestion contract, project definition | done — evidence captured 14 Nov 2026 (`workshop_1/evidence/`) |
| 2 | Docker stack, database schema, historical ingestion with validation and quarantine | planned |
| 3 | Incremental ingestion, watermarks, scheduling, change detection, cross-source event identification | planned |
| 4 | Temporal and geographic analysis, SAS indicator, dashboard | planned |
