"""Tests on REAL responses recorded on 14 Nov 2026 (Workshop 1 evidence)."""
from pathlib import Path

import pandas as pd
import pytest

from tcmon.normalization import canonical
from tcmon.sources import gdacs, ibtracs, nhc

FIX = Path(__file__).parent / "fixtures"


def test_ibtracs_active_recorded():
    df = ibtracs.read_csv(FIX / "ibtracs_active_20261114.csv")
    assert df.attrs["units_row"] is not None            # line 2 is a units row
    assert len(df) == 139 and df.SID.nunique() == 3
    assert (df.TRACK_TYPE == "PROVISIONAL").all()
    assert df.WMO_WIND.isna().all() and df.USA_WIND.notna().all()
    assert not df.duplicated(["SID", "ISO_TIME"]).any()
    ev = canonical.ibtracs_to_events(df, "ibtracs_active", "fixture")
    assert ev.severity.notna().all()                     # falls back to USA_WIND
    assert ev.longitude.between(-180, 180).all()
    assert ev.is_provisional.all()


def test_gdacs_current_recorded():
    frame = gdacs.features_to_frame(gdacs.load_features(FIX / "gdacs_tc_current_20261114.json"))
    assert len(frame) == 3
    assert set(frame.severityunit) == {"km/h"}
    ev = canonical.gdacs_to_events(frame, "fixture")
    cempaka = ev[ev.gdacs_eventid == 1001347].iloc[0]
    assert cempaka.peak_wind_kt == pytest.approx(95.0, abs=0.1)   # 175.9248 km/h
    assert str(cempaka.timestamp) == "2026-11-11 12:00:00+00:00"   # parsed as UTC


def test_gdacs_month_boundary_duplicates_are_dropped():
    frame = gdacs.features_to_frame(gdacs.load_features(FIX / "gdacs_tc_current_20261114.json"))
    doubled = pd.concat([frame, frame], ignore_index=True)
    assert len(canonical.gdacs_to_events(doubled, "fixture")) == len(frame)


def test_nhc_recorded_empty_feed():
    doc = nhc.load(FIX / "nhc_current_storms_20261114.json")
    assert doc == {"activeStorms": []}
    assert nhc.storms_to_frame(doc).empty
