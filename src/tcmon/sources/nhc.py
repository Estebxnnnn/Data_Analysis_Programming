"""NHC CurrentStorms.json adapter (S5, optional - Atlantic and E/C Pacific only).

Field reference: NHC Tropical Cyclone Status JSON File Reference.
* intensity in knots, pressure in mb, movementSpeed in MPH, movementDir in degrees;
* latitude/longitude as strings ("22.9N") plus latitude_numeric/longitude_numeric;
* when no storm is active the file is {"activeStorms": []} - a VALID response.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

URL = "https://www.nhc.noaa.gov/CurrentStorms.json"
SCALAR_FIELDS = ["id", "binNumber", "name", "classification", "intensity", "pressure",
                 "latitude", "longitude", "latitude_numeric", "longitude_numeric",
                 "movementDir", "movementSpeed", "lastUpdate"]


def load(path: str | Path) -> dict:
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def storms_to_frame(doc: dict) -> pd.DataFrame:
    storms = doc.get("activeStorms") or []
    rows = []
    for s in storms:
        row = {k: s.get(k) for k in SCALAR_FIELDS}
        for prod in ("publicAdvisory", "forecastTrack", "trackCone"):
            obj = s.get(prod) or {}
            row[f"{prod}_advNum"] = obj.get("advNum")
            row[f"{prod}_url"] = obj.get("url") or obj.get("zipFile")
        rows.append(row)
    return pd.DataFrame(rows, columns=SCALAR_FIELDS + [
        f"{p}_{a}" for p in ("publicAdvisory", "forecastTrack", "trackCone") for a in ("advNum", "url")])
