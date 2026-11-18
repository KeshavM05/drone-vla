"""Tests for the path planner module."""

import math

from drone_vla.nlp.schemas import FormationType, GeoPoint
from drone_vla.orchestrator.path_planner import (
    _haversine,
    _offset_meters,
    plan_area_search,
    plan_formation,
    plan_orbit,
    plan_perimeter_patrol,
)


def _square_polygon(center_lat=47.397, center_lon=8.545, size_deg=0.001):
    half = size_deg / 2
    return [
        GeoPoint(lat=center_lat - half, lon=center_lon - half),
        GeoPoint(lat=center_lat + half, lon=center_lon - half),
        GeoPoint(lat=center_lat + half, lon=center_lon + half),
        GeoPoint(lat=center_lat - half, lon=center_lon + half),
    ]


def test_haversine_zero():
    p = GeoPoint(lat=47.0, lon=8.0)
    assert _haversine(p, p) == 0.0


def test_haversine_known_distance():
    p1 = GeoPoint(lat=47.0, lon=8.0)
    p2 = GeoPoint(lat=47.001, lon=8.0)
    dist = _haversine(p1, p2)
    assert 100 < dist < 120


def test_offset_meters_north():
    origin = GeoPoint(lat=47.0, lon=8.0)
    shifted = _offset_meters(origin, dx_m=0, dy_m=100)
    assert shifted.lat > origin.lat
    assert abs(shifted.lon - origin.lon) < 1e-10


def test_area_search_generates_paths():
    polygon = _square_polygon()
    paths = plan_area_search(polygon, num_drones=3, altitude_m=20.0)
    assert len(paths) == 3
    for path in paths:
        assert len(path) > 0
        for wp in path:
            assert wp.alt_m == 20.0


def test_area_search_single_drone():
    polygon = _square_polygon()
    paths = plan_area_search(polygon, num_drones=1, altitude_m=30.0)
    assert len(paths) == 1
    assert len(paths[0]) > 0


def test_formation_triangle():
    center = GeoPoint(lat=47.397, lon=8.545)
    positions = plan_formation(center, FormationType.TRIANGLE, 3, spacing_m=10.0, altitude_m=20.0)
    assert len(positions) == 3
    for wp in positions:
        assert wp.alt_m == 20.0


def test_formation_line():
    center = GeoPoint(lat=47.397, lon=8.545)
    positions = plan_formation(center, FormationType.LINE, 5, spacing_m=8.0)
    assert len(positions) == 5


def test_formation_circle():
    center = GeoPoint(lat=47.397, lon=8.545)
    positions = plan_formation(center, FormationType.CIRCLE, 4, spacing_m=15.0)
    assert len(positions) == 4
    for wp in positions:
        dist = _haversine(center, GeoPoint(lat=wp.lat, lon=wp.lon))
        assert 10 < dist < 25


def test_orbit_generates_paths():
    center = GeoPoint(lat=47.397, lon=8.545)
    paths = plan_orbit(center, radius_m=30.0, altitude_m=25.0, num_drones=2)
    assert len(paths) == 2
    for path in paths:
        assert len(path) == 13  # 12 waypoints + closing point


def test_perimeter_patrol():
    polygon = _square_polygon()
    paths = plan_perimeter_patrol(polygon, num_drones=2, altitude_m=15.0)
    assert len(paths) == 2
    for path in paths:
        assert len(path) >= 2
        for wp in path:
            assert wp.alt_m == 15.0
