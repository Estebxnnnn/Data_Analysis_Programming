# Canonical Mapping Table — Team 4 (Tropical Cyclone Monitoring)

Every record from every source becomes one row of the canonical `event` table;
hazard-specific attributes go to the domain tables `storm`, `tc_track_fix`,
`tc_alert`, `tc_advisory` and `storm_xref`. The machine-readable version of this
table is [`mapping.csv`](mapping.csv). All rules were checked against the real
samples of 14 Nov 2026 (`notebooks/01_source_profiling.ipynb`).

## 1. Canonical event fields

| Canonical field | S1 / S3 IBTrACS (`since1980`, `ACTIVE`) | S2 / S4 GDACS TC | S5 NHC (optional) |
| --- | --- | --- | --- |
| `event_id` | `sha1("ibtracs\|SID\|ISO_TIME")` | `sha1("gdacs\|eventid\|episodeid")` | `sha1("nhc\|id\|lastUpdate")` |
| `source` | `ibtracs_since1980` / `ibtracs_active` | `gdacs_tc` | `nhc_current` |
| `event_type` | `tc_track_fix` | `tc_alert_episode` | `tc_advisory` |
| `timestamp` (UTC) | `ISO_TIME` (documented UTC) | `todate`, parsed as UTC (confirmed: 64 of 88 matched pairs at Δt = 0 h) | `lastUpdate` (ISO-8601 UTC) |
| `latitude` | `USA_LAT` ?? `LAT` | `geometry.coordinates[1]` | `latitude_numeric` |
| `longitude` | `USA_LON` ?? `LON`, normalized | `geometry.coordinates[0]`, normalized | `longitude_numeric`, normalized |
| `severity` (kt) | `USA_WIND` ?? `WMO_WIND` | `severitydata.severity` ÷ 1.852 (unit confirmed km/h; value = peak wind so far) | `intensity` |
| `raw_reference` | `<file>@<Last-Modified>#row=<n>` | `<request URL>#eventid=…&episodeid=…` | `<URL>#id=…` |

`a ?? b` = `a` when present, otherwise `b`.

## 2. Domain fields

| Source field | Domain table.field | Rule |
| --- | --- | --- |
| SEASON, NUMBER, BASIN, SUBBASIN, NAME | `storm.*` | `BASIN = "NA"` (North Atlantic) must not be parsed as missing |
| USA_ATCF_ID | `storm.atcf_ids`, `storm_xref.atcf_id` | split on `:` |
| NATURE, TRACK_TYPE | `tc_track_fix.nature`, `.track_type` | observed TRACK_TYPE: main, PROVISIONAL, US-PROVISIONAL, spur-merge, spur-split, spur-other, US-PROVISIONAL_spur; any `spur` value excluded from analogs |
| WMO_AGENCY / derived | `tc_track_fix.wmo_agency`, `.wind_avg_period` | `1-min` when USA_WIND is used |
| USA_PRES ?? WMO_PRES | `tc_track_fix.pressure_hpa` | mb = hPa |
| derived from 1-min wind | `tc_track_fix.sshs_category` | −1 TD, 0 TS, 1–5 |
| STORM_SPEED, STORM_DIR | `tc_track_fix.storm_speed_kt`, `.storm_dir_deg` | kt, degrees |
| DIST2LAND, LANDFALL | `tc_track_fix.dist2land_km`, `.landfall_km` | km |
| USA_AGENCY, USA_RECORD, USA_STATUS, IFLAG | `tc_track_fix.*` | codes kept as text |
| eventid, episodeid | `tc_alert.gdacs_eventid`, `.episodeid` | duplicate key |
| alertlevel, alertscore, episodealertlevel | `tc_alert.*` | ordered Green < Orange < Red |
| severitydata.severity | `tc_alert.peak_wind_kt` | km/h ÷ 1.852; peak wind so far, not current intensity |
| source | `tc_alert.reporting_source` | observed: JTWC, NOAA, RSMC |
| fromdate, todate, datemodified | `tc_alert.from_utc`, `.to_utc`, `.datemodified_utc` | UTC (confirmed) |
| iscurrent | `tc_alert.is_current` | `"true"/"false"` → boolean |
| classification, pressure, movementDir | `tc_advisory.*` | NHC only |
| movementSpeed | `tc_advisory.movement_speed_kt` | mph × 0.868976 |

## 3. Normalization rules

| Topic | Rule |
| --- | --- |
| Time | `TIMESTAMPTZ` in UTC; IBTrACS documented UTC; GDACS strings without offset are UTC (confirmed) |
| Coordinates | WGS84 decimal degrees; lat ∈ [−90, 90]; lon → `((lon + 180) mod 360) − 180` (IBTrACS LON reaches 266.9°, 7,639 fixes > 180); distances with haversine |
| Wind | kt. km/h ÷ 1.852 · mph × 0.868976 · m/s × 1.943844. Averaging period stored, not converted |
| Pressure | hPa (= mb) |
| Severity scales | SSHS only from 1-min winds; GDACS alert level kept as ordered category |
| Missing | units row (line 2) dropped; single-space / empty → NULL; no time or position → `rejected_record`; no wind → kept with `severity = NULL` |

The conversion code lives in `src/tcmon/normalization/units.py` and `canonical.py`
and is covered by `tests/test_units.py` and `tests/test_parsers.py`.
