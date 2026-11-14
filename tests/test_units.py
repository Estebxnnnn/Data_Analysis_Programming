import math

import pytest

from tcmon.normalization import units as u


def test_speed_conversions():
    assert u.kmh_to_kt(185.2) == pytest.approx(100.0)
    assert u.mph_to_kt(100) == pytest.approx(86.8976)
    assert u.ms_to_kt(10) == pytest.approx(19.43844)


@pytest.mark.parametrize("lon,expected", [(0, 0), (180, -180), (190, -170), (-190, 170), (359.5, -0.5)])
def test_normalize_lon(lon, expected):
    assert u.normalize_lon(lon) == pytest.approx(expected)


@pytest.mark.parametrize("kt,cat", [(20, -1), (34, 0), (63, 0), (64, 1), (83, 2), (96, 3), (113, 4), (137, 5)])
def test_sshs_boundaries(kt, cat):
    assert u.sshs_category(kt) == cat


def test_sshs_missing():
    assert u.sshs_category(None) is None
    assert u.sshs_category(float("nan")) is None


def test_haversine_antimeridian():
    # 1 degree of longitude on the equator across 180 deg is ~111 km, not ~40,000 km
    assert u.haversine_km(0, 179.5, 0, -179.5) == pytest.approx(111.2, rel=0.01)


def test_heading_diff():
    assert u.heading_diff_deg(350, 10) == pytest.approx(20)
    assert u.heading_diff_deg(90, 270) == pytest.approx(180)


def test_parse_hemisphere_coord():
    assert u.parse_hemisphere_coord("22.9N") == pytest.approx(22.9)
    assert u.parse_hemisphere_coord("79.9W") == pytest.approx(-79.9)
    assert u.parse_hemisphere_coord(None) is None
