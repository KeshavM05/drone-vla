"""Path planner — Voronoi spatial decomposition and waypoint generation for swarm coordination."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np
from scipy.spatial import Voronoi

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


def plan_area_search(
    polygon: list[GeoPoint],
    num_drones: int,
    altitude_m: float,
    overlap_pct: float = 20.0,
) -> list[list[Waypoint]]:
    """Decompose a search polygon into Voronoi cells and generate sweep paths per drone."""
    if num_drones < 1 or len(polygon) < 3:
        return []

    pts = np.array([[p.lat, p.lon] for p in polygon])
    centroid = pts.mean(axis=0)

    angles = np.linspace(0, 2 * math.pi, num_drones, endpoint=False)
    spread = np.max(np.ptp(pts, axis=0)) * 0.3
    seeds = np.array([
        [centroid[0] + spread * math.cos(a), centroid[1] + spread * math.sin(a)]
        for a in angles
    ])

    if num_drones >= 3:
        far = 10.0
        mirror_pts = np.vstack([
            seeds,
            seeds + [far, 0], seeds - [far, 0],
            seeds + [0, far], seeds - [0, far],
        ])
        vor = Voronoi(mirror_pts)
    else:
        vor = None

    all_paths: list[list[Waypoint]] = []
    for i in range(num_drones):
        if vor and i < len(vor.point_region):
            region_idx = vor.point_region[i]
            region_verts = vor.regions[region_idx]
            if -1 not in region_verts and region_verts:
                cell = vor.vertices[region_verts]
                path = _lawnmower_sweep(cell, altitude_m, overlap_pct)
                all_paths.append(path)
                continue

        sector_angle_start = (2 * math.pi / num_drones) * i
        sector_angle_end = sector_angle_start + (2 * math.pi / num_drones)
        center = GeoPoint(lat=float(centroid[0]), lon=float(centroid[1]))
        path = _sector_sweep(center, spread * 111_000, sector_angle_start, sector_angle_end,
                             altitude_m)
        all_paths.append(path)

    return all_paths


def _lawnmower_sweep(
    cell_vertices: np.ndarray,
    altitude_m: float,
    overlap_pct: float,
) -> list[Waypoint]:
    """Generate a boustrophedon (lawnmower) sweep pattern within a convex cell."""
    min_lat, min_lon = cell_vertices.min(axis=0)
    max_lat, max_lon = cell_vertices.max(axis=0)

    lane_width_deg = (1.0 - overlap_pct / 100.0) * 0.0001
    if lane_width_deg <= 0:
        lane_width_deg = 0.00005

    waypoints: list[Waypoint] = []
    lon = min_lon
    forward = True
    while lon <= max_lon:
        if forward:
            waypoints.append(Waypoint(lat=float(min_lat), lon=float(lon), alt_m=altitude_m))
            waypoints.append(Waypoint(lat=float(max_lat), lon=float(lon), alt_m=altitude_m))
        else:
            waypoints.append(Waypoint(lat=float(max_lat), lon=float(lon), alt_m=altitude_m))
            waypoints.append(Waypoint(lat=float(min_lat), lon=float(lon), alt_m=altitude_m))
        forward = not forward
        lon += lane_width_deg

    return waypoints


def _sector_sweep(
    center: GeoPoint,
    radius_m: float,
    angle_start: float,
    angle_end: float,
    altitude_m: float,
    num_rings: int = 4,
) -> list[Waypoint]:
    """Generate an arc-based sweep for a sector of the search area."""
    waypoints: list[Waypoint] = []
    for ring in range(1, num_rings + 1):
        r = radius_m * ring / num_rings
        steps = max(4, int(8 * ring / num_rings))
        for j in range(steps + 1):
            angle = angle_start + (angle_end - angle_start) * j / steps
            dx = r * math.cos(angle)
            dy = r * math.sin(angle)
            pt = _offset_meters(center, dx, dy)
            waypoints.append(Waypoint(lat=pt.lat, lon=pt.lon, alt_m=altitude_m))
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
