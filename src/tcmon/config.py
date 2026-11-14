"""Configuration loading: config/sources.yaml + environment variables."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

try:  # optional dependency
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UA = "TC-Analog-Monitor/0.1 (Universidad Distrital, Team 4; contact: set TCMON_USER_AGENT)"


def load_env() -> None:
    if load_dotenv is not None:
        load_dotenv(REPO_ROOT / ".env")


def load_sources(path: str | Path | None = None) -> dict[str, Any]:
    load_env()
    path = Path(path or os.getenv("TCMON_SOURCES_FILE", REPO_ROOT / "config" / "sources.yaml"))
    if not path.is_absolute():
        path = REPO_ROOT / path
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def user_agent() -> str:
    load_env()
    return os.getenv("TCMON_USER_AGENT", DEFAULT_UA)


def raw_dir() -> Path:
    load_env()
    p = Path(os.getenv("TCMON_RAW_DIR", "data/raw"))
    return p if p.is_absolute() else REPO_ROOT / p
