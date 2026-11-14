"""Mapping from each source to the canonical event model.

Canonical event columns (common technical contract):
    event_id, source, event_type, timestamp, latitude, longitude, severity, raw_reference
Domain columns are returned alongside, prefixed by nothing; the storage layer
splits them into tc_track_fix / tc_alert / tc_advisory.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from .units import KMH_PER_KT, mph_to_kt, normalize_lon, sshs_category

CANONICAL = ["event_id", "source", "event_type", "timestamp", "latitude", "longitude",
             "severity", "raw_reference"]


def make_event_id(*parts) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def record_hash(row: pd.Series) -> str:
    return hashlib.sha256(row.to_json(date_format="iso").encode("utf-8")).hexdigest()


# --------------------------------------------------------------------- IBTrACS
def ibtracs_to_events(df: pd.DataFrame, source: str, raw_ref: str) -> pd.DataFrame:
    """df = output of sources.ibtracs.read_csv (typed). One event per fix."""
    use_usa = df["USA_WIND"].notna() if "USA_WIND" in df else pd.Series(False, index=df.index)
    lat = df["USA_LAT"].where(df["USA_LAT"].notna(), df["LAT"]) if "USA_LAT" in df else df["LAT"]
    lon = df["USA_LON"].where(df["USA_LON"].notna(), df["LON"]) if "USA_LON" in df else df["LON"]
    severity = df["USA_WIND"].where(use_usa, df.get("WMO_WIND"))
    out = pd.DataFrame({
        "event_id": [make_event_id("ibtracs", s, t) for s, t in zip(df["SID"], df["ISO_TIME"])],
        "source": source,
        "event_type": "tc_track_fix",
        "timestamp": df["ISO_TIME"],
        "latitude": lat,
        "longitude": normalize_lon(lon.to_numpy()),
        "severity": severity,
        "raw_reference": [f"{raw_ref}#row={i}" for i in df.index],
        # domain attributes
        "is_spur": df["TRACK_TYPE"].astype(str).str.contains("spur", case=False),
        "is_provisional": df["TRACK_TYPE"].astype(str).str.contains("PROVISIONAL"),
        "sid": df["SID"], "season": df.get("SEASON"), "basin": df.get("BASIN"),
        "name": df.get("NAME"), "nature": df.get("NATURE"), "track_type": df.get("TRACK_TYPE"),
        "wind_avg_period": np.where(use_usa, "1-min", "agency (WMO_AGENCY)"),
        "wmo_agency": df.get("WMO_AGENCY"),
        "pressure_hpa": df["USA_PRES"].where(df["USA_PRES"].notna(), df.get("WMO_PRES"))
        if "USA_PRES" in df else df.get("WMO_PRES"),
        "sshs_category": [sshs_category(v) if u else None for v, u in zip(severity, use_usa)],
        "storm_speed_kt": df.get("STORM_SPEED"), "storm_dir_deg": df.get("STORM_DIR"),
        "dist2land_km": df.get("DIST2LAND"), "usa_atcf_id": df.get("USA_ATCF_ID"),
    })
    return out


# ----------------------------------------------------------------------- GDACS
def gdacs_to_events(frame: pd.DataFrame, raw_ref: str,
                     assume_utc: bool = True) -> pd.DataFrame:
    """frame = sources.gdacs.features_to_frame(...). One event per (eventid, episodeid).

    Workshop 1 findings (14 Nov 2026):
    * timestamps carry no offset but are UTC (64 of 88 matched IBTrACS pairs at dt = 0 h);
    * severitydata.severity is in km/h and equals the storm's PEAK wind so far,
      not the intensity at `todate` -> stored as peak_wind_kt;
    * monthly windows repeat storms that cross a month boundary -> drop duplicates.
    """
    frame = frame.drop_duplicates(subset=["eventid", "episodeid"]).reset_index(drop=True)
    ts = pd.to_datetime(frame.get("todate"), errors="coerce")
    ts = ts.dt.tz_localize("UTC") if assume_utc else ts
    unit = frame.get("severityunit", pd.Series(index=frame.index, dtype=object)).astype(str).str.lower()
    sev = pd.to_numeric(frame.get("severity"), errors="coerce")
    sev_kt = np.where(unit.str.contains("km/h"), sev / KMH_PER_KT,
                      np.where(unit.str.contains("kt|knot"), sev, np.nan))
    return pd.DataFrame({
        "event_id": [make_event_id("gdacs", e, p) for e, p in zip(frame["eventid"], frame["episodeid"])],
        "source": "gdacs_tc",
        "event_type": "tc_alert_episode",
        "timestamp": ts,
        "latitude": pd.to_numeric(frame["lat"], errors="coerce"),
        "longitude": normalize_lon(pd.to_numeric(frame["lon"], errors="coerce").to_numpy()),
        "severity": sev_kt,
        "raw_reference": [f"{raw_ref}#eventid={e}&episodeid={p}"
                          for e, p in zip(frame["eventid"], frame["episodeid"])],
        "gdacs_eventid": frame["eventid"], "episodeid": frame["episodeid"],
        "name": frame.get("name", frame.get("eventname")),
        "alertlevel": frame.get("alertlevel"), "alertscore": frame.get("alertscore"),
        "is_current": frame.get("iscurrent"), "datemodified": frame.get("datemodified"),
        "peak_wind_kt": sev_kt, "reporting_source": frame.get("source"),
        "severity_raw": sev, "severity_unit_raw": frame.get("severityunit"),
    })


# ------------------------------------------------------------------------- NHC
def nhc_to_events(frame: pd.DataFrame, raw_ref: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=CANONICAL)
    return pd.DataFrame({
        "event_id": [make_event_id("nhc", i, t) for i, t in zip(frame["id"], frame["lastUpdate"])],
        "source": "nhc_current",
        "event_type": "tc_advisory",
        "timestamp": pd.to_datetime(frame["lastUpdate"], utc=True, errors="coerce"),
        "latitude": pd.to_numeric(frame["latitude_numeric"], errors="coerce"),
        "longitude": normalize_lon(pd.to_numeric(frame["longitude_numeric"], errors="coerce").to_numpy()),
        "severity": pd.to_numeric(frame["intensity"], errors="coerce"),
        "raw_reference": [f"{raw_ref}#id={i}" for i in frame["id"]],
        "nhc_id": frame["id"], "classification": frame["classification"],
        "pressure_hpa": pd.to_numeric(frame["pressure"], errors="coerce"),
        "movement_dir_deg": pd.to_numeric(frame["movementDir"], errors="coerce"),
        "movement_speed_kt": [mph_to_kt(v) if pd.notna(v) else None
                              for v in pd.to_numeric(frame["movementSpeed"], errors="coerce")],
    })
