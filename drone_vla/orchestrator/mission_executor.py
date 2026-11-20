"""Mission executor — translates parsed commands + path plans into drone-level flight commands."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from drone_vla.nlp.schemas import MissionCommand, MissionType
from drone_vla.orchestrator.fleet_manager import DroneState, FleetManager
from drone_vla.orchestrator.path_planner import (
    Waypoint,
    plan_area_search,
    plan_formation,
    plan_orbit,
    plan_perimeter_patrol,
)

logger = logging.getLogger(__name__)


class MissionStatus(str, Enum):
    PLANNING = "planning"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass
class ActiveMission:
    mission_id: str
    command: MissionCommand
    status: MissionStatus = MissionStatus.PLANNING
    assigned_drones: list[int] = field(default_factory=list)
    waypoint_plans: dict[int, list[Waypoint]] = field(default_factory=dict)
    progress: dict[int, int] = field(default_factory=dict)


class MissionExecutor:
    def __init__(self, fleet: FleetManager, send_waypoints_fn=None):
        self._fleet = fleet
        self._active_missions: dict[str, ActiveMission] = {}
        self._send_waypoints = send_waypoints_fn

    async def execute_command(self, command: MissionCommand) -> ActiveMission | None:
        drones = self._fleet.allocate_drones(command)
        if not drones and command.mission_type not in (
            MissionType.RETURN_TO_HOME, MissionType.LAND
        ):
            logger.error("Cannot execute: no drones allocated")
            return None

        if command.mission_type == MissionType.RETURN_TO_HOME:
            return await self._execute_rth(command)
        if command.mission_type == MissionType.TAKEOFF:
            return await self._execute_takeoff(command, drones)

        mission = ActiveMission(
            mission_id=drones[0].current_mission_id if drones else "M0000",
            command=command,
            assigned_drones=[d.drone_id for d in drones],
        )

        waypoint_plans = self._plan_waypoints(command, drones)
        mission.waypoint_plans = waypoint_plans
        mission.progress = {did: 0 for did in waypoint_plans}

        self._active_missions[mission.mission_id] = mission
        mission.status = MissionStatus.EXECUTING

        if self._send_waypoints:
            for drone_id, wps in waypoint_plans.items():
                await self._send_waypoints(drone_id, wps)

        logger.info(
            "Mission %s executing: %s with drones %s (%d waypoints each)",
            mission.mission_id,
            command.mission_type.value,
            mission.assigned_drones,
            max((len(w) for w in waypoint_plans.values()), default=0),
        )
        return mission

    def _plan_waypoints(
        self, command: MissionCommand, drones: list[DroneState]
    ) -> dict[int, list[Waypoint]]:
        alt = command.altitude_agl_m or 20.0
        n = len(drones)
        plans: dict[int, list[Waypoint]] = {}

        match command.mission_type:
            case MissionType.AREA_SEARCH:
                if command.search_polygon:
                    paths = plan_area_search(
                        command.search_polygon, n, alt, command.overlap_pct or 20.0
                    )
                    for i, drone in enumerate(drones):
                        if i < len(paths):
                            plans[drone.drone_id] = paths[i]

            case MissionType.PERIMETER_PATROL:
                if command.perimeter_polygon:
                    cw = command.direction != "counterclockwise"
                    paths = plan_perimeter_patrol(command.perimeter_polygon, n, alt, cw)
                    for i, drone in enumerate(drones):
                        if i < len(paths):
                            plans[drone.drone_id] = paths[i]

            case MissionType.FORMATION_FLIGHT:
                if command.formation_type:
                    center = command.center_point
                    if not center:
                        from drone_vla.nlp.schemas import GeoPoint
                        valid = [d for d in drones if d.lat != 0.0]
                        if valid:
                            center = GeoPoint(
                                lat=sum(d.lat for d in valid) / len(valid),
                                lon=sum(d.lon for d in valid) / len(valid),
                            )
                    if center:
                        positions = plan_formation(
                            center,
                            command.formation_type,
                            n,
                            command.spacing_m or 10.0,
                            alt,
                            command.heading_deg or 0.0,
                        )
                        for i, drone in enumerate(drones):
                            if i < len(positions):
                                plans[drone.drone_id] = [positions[i]]

            case MissionType.POINT_INSPECTION:
                if command.target_point:
                    radius = command.orbit_radius_m or 20.0
                    paths = plan_orbit(command.target_point, radius, alt, n)
                    for i, drone in enumerate(drones):
                        if i < len(paths):
                            plans[drone.drone_id] = paths[i]

            case MissionType.RELAY_STATION:
                if command.station_points:
                    for i, drone in enumerate(drones):
                        if i < len(command.station_points):
                            pt = command.station_points[i]
                            plans[drone.drone_id] = [
                                Waypoint(lat=pt.lat, lon=pt.lon, alt_m=alt)
                            ]

        return plans

    async def _execute_rth(self, command: MissionCommand) -> ActiveMission:
        target_ids = command.assignment.drone_ids
        if not target_ids:
            target_ids = [
                d.drone_id for d in self._fleet.all_drones
                if d.status.value == "in_mission"
            ]

        mission = ActiveMission(
            mission_id="RTH",
            command=command,
            assigned_drones=target_ids,
            status=MissionStatus.EXECUTING,
        )

        if self._send_waypoints:
            for did in target_ids:
                await self._send_waypoints(did, "RTH")

        logger.info("RTH commanded for drones %s", target_ids)
        return mission

    async def _execute_takeoff(
        self, command: MissionCommand, drones: list[DroneState]
    ) -> ActiveMission:
        alt = command.altitude_agl_m or 20.0
        mission = ActiveMission(
            mission_id=drones[0].current_mission_id if drones else "TAKEOFF",
            command=command,
            assigned_drones=[d.drone_id for d in drones],
            status=MissionStatus.EXECUTING,
        )

        if self._send_waypoints:
            for d in drones:
                wp = Waypoint(lat=d.lat, lon=d.lon, alt_m=alt)
                await self._send_waypoints(d.drone_id, [wp])

        logger.info("Takeoff to %.0fm for drones %s", alt, mission.assigned_drones)
        return mission

    def abort_mission(self, mission_id: str):
        mission = self._active_missions.get(mission_id)
        if mission:
            mission.status = MissionStatus.ABORTED
            self._fleet.release_drones(mission.assigned_drones)
            logger.info("Mission %s aborted", mission_id)

    def get_active_missions(self) -> list[ActiveMission]:
        return [m for m in self._active_missions.values()
                if m.status == MissionStatus.EXECUTING]
