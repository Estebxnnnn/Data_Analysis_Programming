"""Unit conversions and geodesy helpers. Canonical units: kt, hPa, UTC, WGS84 degrees."""
from __future__ import annotations

import math

import numpy as np

KMH_PER_KT = 1.852            # 1 kt = 1.852 km/h (exact)
KT_PER_MPH = 0.868976         # 1 mph = 0.868976 kt
KT_PER_MS = 1.943844          # 1 m/s = 1.943844 kt
EARTH_RADIUS_KM = 6371.0088   # mean Earth radius

# Saffir-Simpson Hurricane Wind Scale on 1-minute sustained winds (kt).
# -1 = tropical depression, 0 = tropical storm, 1..5 = hurricane categories.
_SSHS_LOWER_BOUNDS = [(137, 5), (113, 4), (96, 3), (83, 2), (64, 1), (34, 0)]


def kmh_to_kt(v):
    return None if v is None else v / KMH_PER_KT


def mph_to_kt(v):
    return None if v is None else v * KT_PER_MPH


def ms_to_kt(v):
    return None if v is None else v * KT_PER_MS


def normalize_lon(lon):
    """Map any longitude to [-180, 180). Works on scalars and numpy/pandas arrays."""
    return ((np.asarray(lon, dtype=float) + 180.0) % 360.0) - 180.0 if not np.isscalar(lon) \
        else ((float(lon) + 180.0) % 360.0) - 180.0


def sshs_category(wind_kt_1min):
    """Saffir-Simpson category from 1-minute wind in kt; None if unknown."""
    if wind_kt_1min is None or (isinstance(wind_kt_1min, float) and math.isnan(wind_kt_1min)):
        return None
    for bound, cat in _SSHS_LOWER_BOUNDS:
        if wind_kt_1min >= bound:
            return cat
    return -1


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km; safe across the antimeridian. Vectorized."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def heading_diff_deg(a, b):
    """Smallest absolute difference between two headings, in [0, 180]."""
    d = np.abs((np.asarray(a, dtype=float) - np.asarray(b, dtype=float)) % 360.0)
    return np.minimum(d, 360.0 - d)


def parse_hemisphere_coord(text: str | None):
    """'22.9N' -> 22.9, '79.9W' -> -79.9 (NHC string coordinates)."""
    if not text:
        return None
    text = text.strip().upper()
    sign = -1.0 if text[-1] in "SW" else 1.0
    return sign * float(text[:-1]) if text[-1] in "NSEW" else float(text)
