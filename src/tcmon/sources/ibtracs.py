"""IBTrACS v04r01 CSV adapter (S1 historical `since1980`, S3 incremental `ACTIVE`).

Column definitions: IBTrACS v04r01 column documentation (NOAA NCEI).
The parser makes no assumption about column order (columns are read by name)
and handles two documented/expected quirks that must be confirmed with the
real file in the profiling notebook:

* a second header line with units may follow the column names;
* missing values may be written as blank or whitespace-only strings.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BASE_URL = ("https://www.ncei.noaa.gov/data/"
            "international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/")
SUBSET_FILES = {
    "since1980": "ibtracs.since1980.list.v04r01.csv",
    "ACTIVE": "ibtracs.ACTIVE.list.v04r01.csv",
    "last3years": "ibtracs.last3years.list.v04r01.csv",
    "ALL": "ibtracs.ALL.list.v04r01.csv",
}

# Columns used by the project (subset of ~170 columns in the file)
USED_COLUMNS = [
    "SID", "SEASON", "NUMBER", "BASIN", "SUBBASIN", "NAME", "ISO_TIME", "NATURE",
    "LAT", "LON", "WMO_WIND", "WMO_PRES", "WMO_AGENCY", "TRACK_TYPE", "DIST2LAND",
    "LANDFALL", "IFLAG", "USA_AGENCY", "USA_ATCF_ID", "USA_LAT", "USA_LON",
    "USA_RECORD", "USA_STATUS", "USA_WIND", "USA_PRES", "USA_SSHS",
    "STORM_SPEED", "STORM_DIR",
]
NUMERIC_COLUMNS = [
    "SEASON", "NUMBER", "LAT", "LON", "WMO_WIND", "WMO_PRES", "DIST2LAND", "LANDFALL",
    "USA_LAT", "USA_LON", "USA_WIND", "USA_PRES", "USA_SSHS", "STORM_SPEED", "STORM_DIR",
]


def url_for(subset: str) -> str:
    return BASE_URL + SUBSET_FILES[subset]


def read_csv(path: str | Path, nrows: int | None = None, usecols: list[str] | None = None,
             keep_raw_text: bool = False) -> pd.DataFrame:
    """Read an IBTrACS CSV. Everything is read as text first, so quirks stay visible."""
    cols = usecols if usecols is not None else USED_COLUMNS
    header = pd.read_csv(path, nrows=0).columns
    present = [c for c in cols if c in header]
    df = pd.read_csv(path, dtype=str, keep_default_na=False, usecols=present,
                     nrows=None if nrows is None else nrows + 1, low_memory=False)
    df.attrs["units_row"] = None
    # Drop a units row if the first data row is not a real fix (ISO_TIME not a date)
    if len(df) and pd.isna(pd.to_datetime(df.loc[0, "ISO_TIME"], errors="coerce")):
        df.attrs["units_row"] = df.iloc[0].to_dict()
        df = df.iloc[1:].reset_index(drop=True)
    elif nrows is not None:
        df = df.iloc[:nrows]
    if keep_raw_text:
        return df
    return coerce_types(df)


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    blank = out.apply(lambda s: s.astype(str).str.strip() == "")
    out = out.mask(blank, np.nan)
    for c in NUMERIC_COLUMNS:
        if c in out:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    if "ISO_TIME" in out:
        out["ISO_TIME"] = pd.to_datetime(out["ISO_TIME"], format="%Y-%m-%d %H:%M:%S",
                                         errors="coerce", utc=True)
    return out
