"""GDACS tropical-cyclone adapter (S2 historical archive, S4 incremental current).

Endpoint: https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH
Response: GeoJSON FeatureCollection, one feature per event (latest episode).
Behaviour to CONFIRM with real responses (see the profiling notebook):
* page size and how the end of the result set is signalled (empty page / 404);
* whether Green events are hidden unless alertlevel lists them explicitly;
* time zone of fromdate / todate / datemodified (strings carry no offset);
* unit of severitydata.severity for TC events.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Iterator

import pandas as pd

from ..http_client import FetchResult, PoliteClient

SEARCH_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
EVENT_DATA_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventdata"
GEOMETRY_URL = "https://www.gdacs.org/gdacsapi/api/polygons/getgeometry"
ALL_LEVELS = "green;orange;red"


def search_params(fromdate: date, todate: date, page: int = 1) -> dict:
    return {"eventlist": "TC", "fromdate": fromdate.isoformat(), "todate": todate.isoformat(),
            "alertlevel": ALL_LEVELS, "pagenumber": page}


def fetch_window(client: PoliteClient, fromdate: date, todate: date, out_dir: str | Path,
                 max_pages: int = 50) -> Iterator[FetchResult]:
    """Fetch every page of one date window; each page is saved unmodified."""
    out_dir = Path(out_dir)
    for page in range(1, max_pages + 1):
        dest = out_dir / f"gdacs_tc_{fromdate}_{todate}_p{page:02d}.json"
        res = client.fetch_to_file(SEARCH_URL, dest, params=search_params(fromdate, todate, page))
        yield res
        if res.status != 200 or not res.path:
            break  # end of results (or error) - recorded in the .meta.json
        if not load_features(res.path):
            break


def load_features(path: str | Path) -> list[dict]:
    try:
        with open(path, encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []
    return data.get("features", []) if isinstance(data, dict) else []


def features_to_frame(features: list[dict]) -> pd.DataFrame:
    """Flatten GeoJSON features: properties + point coordinates + severitydata."""
    rows = []
    for f in features:
        p = dict(f.get("properties", {}))
        geom = f.get("geometry") or {}
        coords = geom.get("coordinates") if geom.get("type") == "Point" else None
        sev = p.pop("severitydata", None) or {}
        p.pop("url", None)
        p.pop("affectedcountries", None)
        rows.append({
            **{k: v for k, v in p.items() if not isinstance(v, (dict, list))},
            "geom_type": geom.get("type"),
            "lon": coords[0] if coords else None,
            "lat": coords[1] if coords else None,
            "severity": sev.get("severity"),
            "severityunit": sev.get("severityunit"),
            "severitytext": sev.get("severitytext"),
        })
    return pd.DataFrame(rows)
