"""Storage layer.

Workshop 1: raw landing-zone paths only.
Workshop 2: database writer (upserts into event + domain tables, ingestion_run,
ingestion_state, rejected_record) following sql/001_schema_draft.sql.
"""
from datetime import datetime, timezone
from pathlib import Path

from ..config import raw_dir


def landing_path(source_id: str, filename: str, when: datetime | None = None) -> Path:
    """data/raw/<source>/<YYYY-MM-DD>/<filename> (UTC date of the download)."""
    when = when or datetime.now(timezone.utc)
    return raw_dir() / source_id / when.strftime("%Y-%m-%d") / filename
