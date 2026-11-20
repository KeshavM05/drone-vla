"""GPS/NED coordinate utilities for PX4 SITL."""

from __future__ import annotations

import math

EARTH_RADIUS_M = 6_371_000


def gps_to_ned(
    lat: float, lon: float, alt_m: float,
    home_lat: float, home_lon: float, home_alt: float = 0.0,
) -> tuple[float, float, float]:
    """Convert GPS (lat, lon, alt_agl) to NED (north, east, down) relative to home."""
    dlat = math.radians(lat - home_lat)
    dlon = math.radians(lon - home_lon)
    cos_lat = math.cos(math.radians(home_lat))

    north = dlat * EARTH_RADIUS_M
    east = dlon * EARTH_RADIUS_M * cos_lat
    down = -(alt_m - home_alt)
    return (north, east, down)


def ned_to_gps(
    north: float, east: float, down: float,
    home_lat: float, home_lon: float, home_alt: float = 0.0,
) -> tuple[float, float, float]:
    """Convert NED to GPS (lat, lon, alt_agl)."""
    cos_lat = math.cos(math.radians(home_lat))
    lat = home_lat + math.degrees(north / EARTH_RADIUS_M)
    lon = home_lon + math.degrees(east / (EARTH_RADIUS_M * cos_lat))
    alt = home_alt - down
    return (lat, lon, alt)


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in meters between two GPS points."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def offset_gps(lat: float, lon: float, north_m: float, east_m: float) -> tuple[float, float]:
    """Offset a GPS point by meters."""
    cos_lat = math.cos(math.radians(lat))
    new_lat = lat + math.degrees(north_m / EARTH_RADIUS_M)
    new_lon = lon + math.degrees(east_m / (EARTH_RADIUS_M * cos_lat))
    return (new_lat, new_lon)
