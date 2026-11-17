"""Data-lake layout and file nomenclature.

Bronze : datalake_bronze/<source>_YYYYMMDD_HHMMSS.json        (raw, one file per source per run)
         datalake_bronze/_pending/bronze_run_YYYYMMDD_HHMMSS.json   (run manifest, written LAST;
                                                                     watched by the Silver FileSensor)
         datalake_bronze/_claimed/<silver_ts>/bronze_run_*.json     (manifest claimed by a Silver run)
Silver : datalake_silver/tropical_cyclones_YYYYMMDD_HHMMSS.parquet (timestamp = Silver processing run)
         datalake_silver/_rejected/tropical_cyclones_rejected_YYYYMMDD_HHMMSS.json
         datalake_silver/_manifest.jsonl                           (lineage: Silver file -> Bronze files)
Gold   : datalake_gold/ (Workshop 3)

All timestamps in file names are UTC and come from the Airflow run's logical
date, so re-running the same run rewrites the same file (idempotency).
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

TS_FORMAT = "%Y%m%d_%H%M%S"
SILVER_TOPIC = "tropical_cyclones"


def datalake_root() -> Path:
    """Root that holds the datalake_* folders (/opt/airflow inside Docker)."""
    env = os.getenv("TCMON_DATALAKE_ROOT")
    return Path(env) if env else Path(__file__).resolve().parents[3]


def bronze_dir() -> Path:
    return datalake_root() / "datalake_bronze"


def silver_dir() -> Path:
    return datalake_root() / "datalake_silver"


def gold_dir() -> Path:
    return datalake_root() / "datalake_gold"


def pending_dir() -> Path:
    return bronze_dir() / "_pending"


def claimed_dir() -> Path:
    return bronze_dir() / "_claimed"


def staging_dir() -> Path:
    return bronze_dir() / "_staging"


def ts_string(moment: datetime) -> str:
    """UTC timestamp used in every file name."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime(TS_FORMAT)


def bronze_file(source: str, run_ts: str) -> Path:
    return bronze_dir() / f"{source}_{run_ts}.json"


def bronze_manifest(run_ts: str) -> Path:
    return pending_dir() / f"bronze_run_{run_ts}.json"


def silver_file(run_ts: str) -> Path:
    return silver_dir() / f"{SILVER_TOPIC}_{run_ts}.parquet"


def rejected_file(run_ts: str) -> Path:
    return silver_dir() / "_rejected" / f"{SILVER_TOPIC}_rejected_{run_ts}.json"


def ensure_layout() -> None:
    for d in (bronze_dir(), silver_dir(), gold_dir(), pending_dir(), claimed_dir(), staging_dir(),
              silver_dir() / "_rejected"):
        d.mkdir(parents=True, exist_ok=True)


def atomic_write_bytes(path: Path, data: bytes) -> Path:
    """Write to a temporary file in the same folder, then rename: readers never see half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return path


def atomic_write_json(path: Path, obj) -> Path:
    return atomic_write_bytes(path, json.dumps(obj, indent=1, ensure_ascii=False, default=str).encode("utf-8"))
