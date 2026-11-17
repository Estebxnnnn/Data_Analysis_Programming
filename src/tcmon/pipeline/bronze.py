"""Bronze layer: extract, validate (basic schema check) and persist raw JSON.

Each source is first downloaded byte-for-byte into datalake_bronze/_staging/
(with the HTTP metadata of the request), then validated, then wrapped in a JSON
envelope and written as <source>_YYYYMMDD_HHMMSS.json. Records are kept as the
source published them: IBTrACS values stay text (including the single-space
blanks), GDACS features stay unchanged GeoJSON.
"""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ..http_client import PoliteClient
from ..sources import gdacs, ibtracs
from . import paths

log = logging.getLogger(__name__)

IBTRACS_SOURCE = "ibtracs_active"
GDACS_SOURCE = "gdacs_tc"
GDACS_WINDOW_DAYS = 7          # same window as the IBTrACS ACTIVE subset
GDACS_MAX_PAGES = 10

IBTRACS_REQUIRED = ["SID", "SEASON", "BASIN", "NAME", "ISO_TIME", "LAT", "LON", "TRACK_TYPE",
                    "USA_WIND", "WMO_WIND", "USA_PRES", "WMO_PRES"]
GDACS_REQUIRED = ["eventtype", "eventid", "episodeid", "fromdate", "todate", "datemodified",
                  "alertlevel", "severitydata"]


def _client() -> PoliteClient:
    return PoliteClient(min_interval=1.0, timeout=90, max_retries=3)


# ----------------------------------------------------------------- extract
def extract_ibtracs_active(run_ts: str) -> dict:
    """Download the IBTrACS ACTIVE CSV (file over HTTPS) into the staging area."""
    paths.ensure_layout()
    dest = paths.staging_dir() / f"{IBTRACS_SOURCE}_{run_ts}.csv"
    res = _client().fetch_to_file(ibtracs.url_for("ACTIVE"), dest)
    if res.status != 200 or not res.path:
        raise RuntimeError(f"IBTrACS ACTIVE download failed: HTTP {res.status} ({res.url})")
    log.info("IBTrACS ACTIVE: HTTP %s, %s bytes, Last-Modified=%s", res.status, res.size_bytes,
             res.headers.get("Last-Modified"))
    return {"source": IBTRACS_SOURCE, "staged": [res.path], "http": [res.to_dict()]}


def extract_gdacs(run_ts: str, run_day: date | None = None) -> dict:
    """Query the GDACS event API for tropical cyclones of the last 7 days (all pages)."""
    paths.ensure_layout()
    run_day = run_day or datetime.now(timezone.utc).date()
    start = run_day - timedelta(days=GDACS_WINDOW_DAYS)
    staged, http = [], []
    for page in range(1, GDACS_MAX_PAGES + 1):
        dest = paths.staging_dir() / f"{GDACS_SOURCE}_{run_ts}_p{page:02d}.json"
        res = _client().fetch_to_file(gdacs.SEARCH_URL, dest, params=gdacs.search_params(start, run_day, page))
        http.append(res.to_dict())
        if res.status == 204:                      # documented end of results (Workshop 1)
            log.info("GDACS page %s: HTTP 204, end of results", page)
            for f in (Path(res.path or dest), Path(str(res.path or dest) + ".meta.json")):
                f.unlink(missing_ok=True)
            break
        if res.status != 200 or not res.path:
            raise RuntimeError(f"GDACS request failed: HTTP {res.status} ({res.url})")
        staged.append(res.path)
        n = len(gdacs.load_features(res.path))
        log.info("GDACS page %s: HTTP 200, %s features", page, n)
        if n < 100:                                # page size is 100: a short page is the last one
            break
    return {"source": GDACS_SOURCE, "staged": staged, "http": http,
            "window": {"fromdate": start.isoformat(), "todate": run_day.isoformat()}}


# ---------------------------------------------------------------- validate
def _ibtracs_rows(path: str) -> tuple[list[dict], dict | None, list[str]]:
    text = Path(path).read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    units = None
    if rows and not _looks_like_time(rows[0].get("ISO_TIME", "")):   # line 2 = units row (Workshop 1, DQ2)
        units, rows = rows[0], rows[1:]
    return rows, units, reader.fieldnames or []


def _looks_like_time(value: str) -> bool:
    try:
        datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False


def validate(extracted: dict) -> dict:
    """Basic schema check. Raises ValueError so that an invalid batch is never persisted."""
    source = extracted["source"]
    report = {"source": source, "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if source == IBTRACS_SOURCE:
        rows, units, header = _ibtracs_rows(extracted["staged"][0])
        missing = [c for c in IBTRACS_REQUIRED if c not in header]
        bad_time = sum(not _looks_like_time(r.get("ISO_TIME", "")) for r in rows)
        bad_pos = sum(not (r.get("LAT", "").strip() and r.get("LON", "").strip()) for r in rows)
        report.update(columns=len(header), records=len(rows), units_row=units is not None,
                      missing_fields=missing, invalid_time=bad_time, missing_position=bad_pos)
    else:
        feats = [f for p in extracted["staged"] for f in gdacs.load_features(p)]
        missing = sorted({k for f in feats for k in GDACS_REQUIRED if k not in f.get("properties", {})})
        not_point = sum((f.get("geometry") or {}).get("type") != "Point" for f in feats)
        report.update(records=len(feats), missing_fields=missing, non_point_geometry=not_point)
    report["passed"] = not report["missing_fields"]
    if not report["passed"]:
        raise ValueError(f"{source}: schema check failed, missing fields {report['missing_fields']}")
    if report["records"] == 0:
        log.warning("%s: valid response with 0 records (no active storms)", source)
    log.info("Validation %s: %s", source, report)
    return report


# ----------------------------------------------------------------- persist
def persist(extracted: dict, report: dict, run_ts: str) -> str:
    """Write <source>_YYYYMMDD_HHMMSS.json (atomic) and remove the staged files."""
    source = extracted["source"]
    if source == IBTRACS_SOURCE:
        rows, units, header = _ibtracs_rows(extracted["staged"][0])
        payload = {"format": "csv_rows", "columns": header, "units_row": units, "records": rows}
    else:
        feats = [f for p in extracted["staged"] for f in gdacs.load_features(p)]
        payload = {"format": "geojson_features", "window": extracted.get("window"), "records": feats}
    envelope = {
        "source": source,
        "run_ts": run_ts,
        "ingested_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "http": extracted["http"],
        "validation": report,
        "record_count": len(payload["records"]),
        **payload,
    }
    out = paths.atomic_write_json(paths.bronze_file(source, run_ts), envelope)
    for p in extracted["staged"]:
        for f in (Path(p), Path(str(p) + ".meta.json")):
            f.unlink(missing_ok=True)
    log.info("Bronze file written: %s (%s records)", out.name, envelope["record_count"])
    return out.name


def signal_silver(run_ts: str, bronze_files: list[str]) -> str | None:
    """Write the run manifest LAST: its arrival tells the Silver FileSensor that the batch is complete."""
    files = [f for f in bronze_files if f]
    if not files:
        log.warning("No Bronze file was written in run %s; nothing to signal", run_ts)
        return None
    manifest = {"run_ts": run_ts, "bronze_files": files,
                "written_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    out = paths.atomic_write_json(paths.bronze_manifest(run_ts), manifest)
    log.info("Run manifest written: %s -> %s", out.name, files)
    return out.name


def load_envelope(name: str) -> dict:
    return json.loads((paths.bronze_dir() / name).read_text(encoding="utf-8"))
