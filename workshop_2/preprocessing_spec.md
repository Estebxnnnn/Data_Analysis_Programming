# Silver Preprocessing Specification (Workshop 2)

Bronze (raw JSON) → Silver (typed, cleaned, deduplicated Parquet). Every rule is
grounded in the Workshop 1 profiling of the real samples collected on
14 Nov 2026 (data-quality problems DQ1–DQ8 of the Workshop 1 report). The
implementation is `src/tcmon/pipeline/silver.py`; tests on the recorded
responses are in `tests/test_pipeline.py`.

Processing order: **conform → types → nulls → text → outliers → deduplication → schema → Parquet**.

## 1. Conformance to one row per observation
| Source | Row | Reused mapping (Workshop 1) |
| --- | --- | --- |
| IBTrACS ACTIVE (`ibtracs_active_*.json`) | one track fix | `canonical.ibtracs_to_events`: USA_* preferred over WMO_*, longitude normalized |
| GDACS (`gdacs_tc_*.json`) | one alert episode (`eventid`, `episodeid`) | `canonical.gdacs_to_events`: km/h → kt, UTC times |

GDACS `severity` is stored as **`peak_wind_kt`**, never as current wind: in Workshop 1 it matched the
IBTrACS *peak* of the active storms (CEMPAKA 95 vs 93 kt) and not the current intensity (64 kt).

## 2. Null handling
| Field | Observed in Workshop 1 | Strategy |
| --- | --- | --- |
| `event_id`, `timestamp_utc`, `latitude`, `longitude` | 0 invalid values, but mandatory for any analysis | **Drop** the row and quarantine it in `datalake_silver/_rejected/` |
| `wind_kt` | `WMO_WIND` 62.8 % missing in the archive sample and 100 % in ACTIVE; `USA_WIND` 0 % missing in ACTIVE | **Coalesce** `USA_WIND` → `WMO_WIND`; if both missing keep NULL and **flag** `wind_missing`. No mean/median imputation: it would invent storm intensities |
| `pressure_hpa` | `WMO_PRES` 59.0 % missing | **Coalesce** `USA_PRES` → `WMO_PRES`; otherwise NULL |
| `storm_speed_kt`, `storm_dir_deg` | provided by IBTrACS, can be blank | **Impute by derivation** from consecutive fixes of the same storm (haversine distance / time, initial bearing); **flag** `motion_derived` |
| `storm_name` | 38,257 archive fixes named `UNNAMED`; GDACS codes such as `02-20262027-27` or `FIVE-24` | NULL + **flag** `is_unnamed` |
| `basin` | GDACS publishes no basin | **Sentinel** `UN` (not reported) |
| `nature` | — | **Sentinel** `NR` (IBTrACS code for "not reported") |
| `wind_avg_period` | 12,690 archive fixes have only 10-min agency winds (DQ1) | `1-min`, `10-min agency` or **sentinel** `unknown` |
| `sshs_category` | Saffir–Simpson is defined on 1-min winds | NULL unless `wind_avg_period = 1-min` |
| GDACS fields on IBTrACS rows and vice versa | structural | NULL (not applicable) |

Mode imputation is not used: categorical fields are identifiers or codes whose most frequent value carries no information about a specific storm.

## 3. Data-type normalization (target schema)
| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `event_id` | string | yes | SHA-1 of source, native storm id and time (IBTrACS) or event and episode (GDACS) |
| `source` | category | yes | ibtracs_active | gdacs_tc |
| `event_type` | category | yes | tc_track_fix | tc_alert_episode |
| `storm_id` | string | yes | IBTrACS SID or GDACS eventid |
| `storm_name` | string | no | Normalized storm name (upper case, no prefix or year suffix); NULL if unnamed |
| `storm_name_raw` | string | no | Name exactly as published by the source |
| `is_unnamed` | bool | yes | True for placeholders (UNNAMED, NOT_NAMED, numeric codes, spelled numbers) |
| `basin` | category | yes | IBTrACS basin code (NA, EP, WP, NI, SI, SP, SA); UN = not reported (GDACS) |
| `timestamp_utc` | timestamp | yes | Observation time in UTC |
| `latitude` | float | yes | Degrees north, WGS84, in [-90, 90] |
| `longitude` | float | yes | Degrees east, WGS84, normalized to [-180, 180) |
| `wind_kt` | float | no | Current maximum sustained wind (kt): USA_WIND, else WMO_WIND; IBTrACS only |
| `wind_avg_period` | category | yes | 1-min | 10-min agency | unknown |
| `sshs_category` | int8 | no | Saffir-Simpson category (-1 TD, 0 TS, 1-5) from 1-min wind |
| `pressure_hpa` | float | no | Minimum central pressure (hPa): USA_PRES, else WMO_PRES |
| `peak_wind_kt` | float | no | GDACS severity converted from km/h; peak wind of the storm so far |
| `nature` | category | no | DS, TS, ET, SS, MX; NR = not reported |
| `track_type` | category | no | main, PROVISIONAL, spur-* ... |
| `is_provisional` | bool | yes | Track still provisional (will be revised) |
| `is_spur` | bool | yes | Spur track (excluded from analogs) |
| `storm_speed_kt` | float | no | Translation speed (kt) |
| `storm_dir_deg` | float | no | Translation direction (degrees) |
| `motion_derived` | bool | yes | Speed/direction derived from consecutive fixes because the source left them empty |
| `dist2land_km` | float | no | Distance to land (km) |
| `alert_level` | category | no | Green < Orange < Red |
| `alert_score` | float | no | GDACS alert score |
| `is_current` | bool | no | GDACS iscurrent flag |
| `gdacs_episode_id` | int64 | no | GDACS episode number |
| `date_modified_utc` | timestamp | no | GDACS datemodified (UTC) |
| `wind_iqr_outlier` | bool | yes | wind_kt outside [Q1 - 1.5 IQR, Q3 + 1.5 IQR] of the batch (flag only) |
| `speed_zscore_outlier` | bool | yes | |z| > 3 for storm_speed_kt within the batch (flag only) |
| `qc_flags` | string | yes | Semicolon-separated quality notes; empty string when none |
| `record_hash` | string | yes | SHA-256 of the business columns, used for cross-batch deduplication |
| `is_revision` | bool | yes | Same event_id already in an earlier Silver file with different values |
| `bronze_file` | string | yes | Bronze JSON file the row comes from |
| `bronze_sha256` | string | yes | SHA-256 of the raw HTTP response stored in that Bronze file |
| `silver_run_ts` | string | yes | Silver run timestamp (YYYYMMDD_HHMMSS, UTC), as in the file name |
| `processed_at_utc` | timestamp | yes | Processing time (UTC) |

Strings are dictionary-encoded in Parquet for `category` fields and come back as Pandas `category`.
Timestamps are `timestamp[us, UTC]`; nullable integers and booleans use Arrow nulls.

## 4. Text preprocessing
The sources carry no free text (names are identifiers, GDACS `severitytext` is a fixed template), so the
NLP steps that destroy identifiers (stop-word removal, tokenization) are **not applied**. The storm-name
normalization applied is:
1. Unicode NFKD and removal of accents (`Peñà` → `PENA`);
2. upper case and trimming;
3. removal of the GDACS prefix (`Tropical Cyclone`, `Tropical Storm`, ...) and year suffix (`-26`);
4. removal of punctuation except hyphens; collapse of repeated spaces;
5. detection of placeholders (`UNNAMED`, `NOT_NAMED`, numeric codes, spelled numbers) → `is_unnamed`.

Result on the recorded data: `Tropical Cyclone CEMPAKA-26` (GDACS) and `CEMPAKA` (IBTrACS) both become
`CEMPAKA`, which makes the two sources joinable by name in the Gold layer.

## 5. Outlier detection and handling
| Method | Field | Rule | Action | Justification |
| --- | --- | --- | --- | --- |
| Physical plausibility | `wind_kt`, `peak_wind_kt` | outside [0, 200] kt | value → NULL, flag `<field>_out_of_range` | Workshop 1 maximum: 185 kt (archive) and 155 kt (GDACS, MILTON) |
| Physical plausibility | `pressure_hpa` | outside [850, 1050] hPa | value → NULL, flag | IBTrACS documented valid range |
| Physical plausibility | `storm_speed_kt`, `storm_dir_deg`, `dist2land_km` | outside [0, 70] kt, [0, 360]°, [0, 5000] km | value → NULL, flag | impossible values |
| IQR (k = 1.5) | `wind_kt` | outside [Q1 − 1.5 IQR, Q3 + 1.5 IQR] of the batch | **flag only** `wind_iqr_outlier` | intense storms are rare but real: removing them would remove exactly the events the system monitors |
| Z-score | `storm_speed_kt` | \|z\| > 3 within the batch | **flag only** `speed_zscore_outlier` | fast motion occurs during extratropical transition |

## 6. Deduplication
| Level | Key | Rule | Workshop 1 evidence |
| --- | --- | --- | --- |
| Within a GDACS response | (`eventid`, `episodeid`) | keep one | 14 repeats in 2024 from overlapping windows (DQ8) |
| Within a Silver batch | `event_id` | keep the last occurrence | — |
| Across batches | (`event_id`, `record_hash`) | drop rows already present in an earlier Silver file | hourly polls return identical ACTIVE content between releases (two polls, 0 changes) |
| Revisions | `event_id` seen before with a different `record_hash` | **keep**, flag `is_revision` | all ACTIVE fixes are `PROVISIONAL` and are revised (DQ4) |

`record_hash` is the SHA-256 of the business columns (lineage and processing columns excluded), so the
same observation always produces the same hash.

## 7. Schema enforcement
The explicit Arrow schema (section 3) is applied with `pyarrow.Table.from_pandas(..., schema=...)`. Missing
columns are added as NULL; required columns must have no NULLs, otherwise the task fails and no file is
written (the write is atomic: temporary file, then rename).

## 8. Traceability and idempotency
- File name: `tropical_cyclones_YYYYMMDD_HHMMSS.parquet`, timestamp of the Silver run (UTC logical date).
- Row level: `bronze_file`, `bronze_sha256`, `silver_run_ts`, `processed_at_utc`.
- File level: Parquet metadata key `tcmon_lineage` (Bronze files, row counts, dedup statistics) and one line per file in `datalake_silver/_manifest.jsonl`.
- Claimed Bronze manifests stay in `datalake_bronze/_claimed/<silver_ts>/`, so a re-run of the same Silver run reprocesses exactly the same files and rewrites the same Parquet file.
