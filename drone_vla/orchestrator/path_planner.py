"""Path planner — Voronoi spatial decomposition and waypoint generation for swarm coordination."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

from drone_vla.nlp.schemas import FormationType, GeoPoint, MissionCommand

logger = logging.getLogger(__name__)

EARTH_RADIUS_M = 6_371_000


@dataclass
class Waypoint:
    lat: float
    lon: float
    alt_m: float
    speed_ms: float | None = None
    loiter_s: float | None = None
    heading_deg: float | None = None


def _haversine(p1: GeoPoint, p2: GeoPoint) -> float:
    lat1, lat2 = math.radians(p1.lat), math.radians(p2.lat)
    dlat = lat2 - lat1
    dlon = math.radians(p2.lon - p1.lon)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _offset_meters(origin: GeoPoint, dx_m: float, dy_m: float) -> GeoPoint:
    """Offset a GPS point by meters (dx=east, dy=north)."""
    dlat = dy_m / EARTH_RADIUS_M * (180 / math.pi)
    dlon = dx_m / (EARTH_RADIUS_M * math.cos(math.radians(origin.lat))) * (180 / math.pi)
    return GeoPoint(lat=origin.lat + dlat, lon=origin.lon + dlon)


DEFAULT_LANE_WIDTH_M = 15.0
M_PER_DEG_LAT = 111_320.0


def plan_area_search(
    polygon: list[GeoPoint],
    num_drones: int,
    altitude_m: float,
    overlap_pct: float = 20.0,
) -> list[list[Waypoint]]:
    """Generate efficient lawnmower sweep paths over a search polygon.

    For multi-drone: splits the polygon into horizontal strips (one per drone).
    Each drone sweeps its strip with a boustrophedon pattern.
    """
    if num_drones < 1 or len(polygon) < 3:
        return []

    pts = np.array([[p.lat, p.lon] for p in polygon])
    min_lat, min_lon = pts.min(axis=0)
    max_lat, max_lon = pts.max(axis=0)

    lane_width_m = DEFAULT_LANE_WIDTH_M * (1.0 - overlap_pct / 100.0)
    lane_width_m = max(lane_width_m, 5.0)
    centroid_lat = (min_lat + max_lat) / 2
    m_per_deg_lon = M_PER_DEG_LAT * math.cos(math.radians(centroid_lat))

    strip_height_lat = (max_lat - min_lat) / num_drones

    all_paths: list[list[Waypoint]] = []
    for i in range(num_drones):
        strip_min_lat = min_lat + i * strip_height_lat
        strip_max_lat = strip_min_lat + strip_height_lat
        path = _lawnmower_sweep_meters(
            strip_min_lat, strip_max_lat, min_lon, max_lon,
            lane_width_m, m_per_deg_lon, altitude_m,
        )
        all_paths.append(path)

    return all_paths


def _lawnmower_sweep_meters(
    min_lat: float, max_lat: float,
    min_lon: float, max_lon: float,
    lane_width_m: float,
    m_per_deg_lon: float,
    altitude_m: float,
) -> list[Waypoint]:
    """Generate a boustrophedon sweep with lane width in meters."""
    lane_width_lon = lane_width_m / m_per_deg_lon

    waypoints: list[Waypoint] = []
    lon = min_lon
    forward = True
    while lon <= max_lon + lane_width_lon * 0.5:
        clamped_lon = min(lon, max_lon)
        if forward:
            waypoints.append(Waypoint(lat=min_lat, lon=clamped_lon, alt_m=altitude_m))
            waypoints.append(Waypoint(lat=max_lat, lon=clamped_lon, alt_m=altitude_m))
        else:
            waypoints.append(Waypoint(lat=max_lat, lon=clamped_lon, alt_m=altitude_m))
            waypoints.append(Waypoint(lat=min_lat, lon=clamped_lon, alt_m=altitude_m))
        forward = not forward
        lon += lane_width_lon

    return waypoints


def plan_formation(
    center: GeoPoint,
    formation: FormationType,
    num_drones: int,
    spacing_m: float = 10.0,
    altitude_m: float = 20.0,
    heading_deg: float = 0.0,
) -> list[Waypoint]:
    """Compute position waypoints for each drone in a formation."""
    positions: list[Waypoint] = []
    heading_rad = math.radians(heading_deg)

    match formation:
        case FormationType.LINE:
            for i in range(num_drones):
                offset = (i - (num_drones - 1) / 2) * spacing_m
                dx = offset * math.cos(heading_rad + math.pi / 2)
                dy = offset * math.sin(heading_rad + math.pi / 2)
                pt = _offset_meters(center, dx, dy)
                positions.append(Waypoint(lat=pt.lat, lon=pt.lon, alt_m=altitude_m,
                                          heading_deg=heading_deg))

        case FormationType.TRIANGLE:
            if num_drones >= 1:
                pt = _offset_meters(center, 0, spacing_m)
                positions.append(Waypoint(lat=pt.lat, lon=pt.lon, alt_m=altitude_m,
                                          heading_deg=heading_deg))
            if num_drones >= 2:
                pt = _offset_meters(center, -spacing_m * 0.866, -spacing_m * 0.5)
                positions.append(Waypoint(lat=pt.lat, lon=pt.lon, alt_m=altitude_m,
                                          heading_deg=heading_deg))
            if num_drones >= 3:
                pt = _offset_meters(center, spacing_m * 0.866, -spacing_m * 0.5)
                positions.append(Waypoint(lat=pt.lat, lon=pt.lon, alt_m=altitude_m,
                                          heading_deg=heading_deg))
            for i in range(3, num_drones):
                angle = 2 * math.pi * i / num_drones
                dx = spacing_m * 1.5 * math.cos(angle)
                dy = spacing_m * 1.5 * math.sin(angle)
                pt = _offset_meters(center, dx, dy)
                positions.append(Waypoint(lat=pt.lat, lon=pt.lon, alt_m=altitude_m,
                                          heading_deg=heading_deg))

        case FormationType.CIRCLE:
            for i in range(num_drones):
                angle = 2 * math.pi * i / num_drones
                dx = spacing_m * math.cos(angle)
                dy = spacing_m * math.sin(angle)
                pt = _offset_meters(center, dx, dy)
                positions.append(Waypoint(lat=pt.lat, lon=pt.lon, alt_m=altitude_m,
                                          heading_deg=heading_deg))

        case FormationType.V_SHAPE:
            if num_drones >= 1:
                positions.append(Waypoint(lat=center.lat, lon=center.lon, alt_m=altitude_m,
                                          heading_deg=heading_deg))
            for i in range(1, num_drones):
                side = 1 if i % 2 == 1 else -1
                row = (i + 1) // 2
                dx = side * row * spacing_m * math.cos(heading_rad + math.pi / 2)
                dy_fwd = -row * spacing_m * math.sin(math.radians(30))
                dy = dy_fwd * math.sin(heading_rad)
                dx_total = dx + dy_fwd * math.cos(heading_rad)
                pt = _offset_meters(center, dx_total, dy)
                positions.append(Waypoint(lat=pt.lat, lon=pt.lon, alt_m=altitude_m,
                                          heading_deg=heading_deg))

        case FormationType.DIAMOND | FormationType.GRID:
            side = math.ceil(math.sqrt(num_drones))
            for i in range(num_drones):
                row, col = divmod(i, side)
                dx = (col - (side - 1) / 2) * spacing_m
                dy = (row - (side - 1) / 2) * spacing_m
                pt = _offset_meters(center, dx, dy)
                positions.append(Waypoint(lat=pt.lat, lon=pt.lon, alt_m=altitude_m,
                                          heading_deg=heading_deg))

    return positions


def plan_orbit(
    center: GeoPoint,
    radius_m: float,
    altitude_m: float,
    num_drones: int,
    clockwise: bool = True,
    num_waypoints: int = 12,
) -> list[list[Waypoint]]:
    """Generate circular orbit paths staggered across drones."""
    paths: list[list[Waypoint]] = []
    direction = -1 if clockwise else 1

    for i in range(num_drones):
        phase_offset = 2 * math.pi * i / num_drones
        drone_wps: list[Waypoint] = []
        for j in range(num_waypoints + 1):
            angle = phase_offset + direction * 2 * math.pi * j / num_waypoints
            dx = radius_m * math.cos(angle)
            dy = radius_m * math.sin(angle)
            pt = _offset_meters(center, dx, dy)
            drone_wps.append(Waypoint(lat=pt.lat, lon=pt.lon, alt_m=altitude_m))
        paths.append(drone_wps)

    return paths


def plan_perimeter_patrol(
    polygon: list[GeoPoint],
    num_drones: int,
    altitude_m: float,
    clockwise: bool = True,
) -> list[list[Waypoint]]:
    """Divide a perimeter into segments, one per drone, for continuous patrol."""
    n = len(polygon)
    if n < 3 or num_drones < 1:
        return []

    edges: list[tuple[GeoPoint, GeoPoint]] = []
    for i in range(n):
        edges.append((polygon[i], polygon[(i + 1) % n]))
    if not clockwise:
        edges.reverse()

    total_dist = sum(_haversine(a, b) for a, b in edges)
    segment_dist = total_dist / num_drones

    paths: list[list[Waypoint]] = []
    current_path: list[Waypoint] = []
    accumulated = 0.0

    for a, b in edges:
        d = _haversine(a, b)
        current_path.append(Waypoint(lat=a.lat, lon=a.lon, alt_m=altitude_m))
        accumulated += d

        while accumulated >= segment_dist and len(paths) < num_drones - 1:
            current_path.append(Waypoint(lat=b.lat, lon=b.lon, alt_m=altitude_m))
            paths.append(current_path)
            current_path = [Waypoint(lat=b.lat, lon=b.lon, alt_m=altitude_m)]
            accumulated -= segment_dist

    current_path.append(Waypoint(lat=edges[-1][1].lat, lon=edges[-1][1].lon, alt_m=altitude_m))
    paths.append(current_path)

    return paths
