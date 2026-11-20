"""Fleet manager — tracks drone state, allocates drones to missions, handles failover."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from drone_vla.config import FleetConfig
from drone_vla.nlp.schemas import DroneAssignment, MissionCommand

logger = logging.getLogger(__name__)


class DroneStatus(str, Enum):
    IDLE = "idle"
    ARMED = "armed"
    IN_MISSION = "in_mission"
    RETURNING = "returning"
    LANDED = "landed"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class DroneState:
    drone_id: int
    status: DroneStatus = DroneStatus.OFFLINE
    lat: float = 0.0
    lon: float = 0.0
    alt_m: float = 0.0
    heading_deg: float = 0.0
    battery_pct: float = 100.0
    speed_ms: float = 0.0
    current_mission_id: Optional[str] = None
    sensor_payload: str = "rgb"
    last_heartbeat: float = field(default_factory=time.time)

    @property
    def is_available(self) -> bool:
        return self.status in (DroneStatus.IDLE, DroneStatus.LANDED)

    @property
    def is_healthy(self) -> bool:
        age = time.time() - self.last_heartbeat
        return age < 5.0 and self.status != DroneStatus.ERROR


class FleetManager:
    def __init__(self, config: FleetConfig):
        self._config = config
        self._drones: dict[int, DroneState] = {}
        self._mission_counter = 0

    def register_drone(self, drone_id: int, **kwargs) -> DroneState:
        state = DroneState(drone_id=drone_id, **kwargs)
        self._drones[drone_id] = state
        logger.info("Registered drone %d", drone_id)
        return state

    def update_telemetry(self, drone_id: int, **kwargs):
        if drone_id not in self._drones:
            logger.warning("Telemetry for unknown drone %d", drone_id)
            return
        state = self._drones[drone_id]
        for k, v in kwargs.items():
            if hasattr(state, k):
                setattr(state, k, v)
        state.last_heartbeat = time.time()

    def get_drone(self, drone_id: int) -> DroneState | None:
        return self._drones.get(drone_id)

    @property
    def all_drones(self) -> list[DroneState]:
        return list(self._drones.values())

    @property
    def available_drones(self) -> list[DroneState]:
        return [d for d in self._drones.values() if d.is_available]

    def allocate_drones(self, command: MissionCommand) -> list[DroneState]:
        assignment = command.assignment

        if assignment.drone_ids:
            selected = [self._drones[did] for did in assignment.drone_ids if did in self._drones]
            unavailable = [d for d in selected if not d.is_available]
            if unavailable:
                logger.warning(
                    "Requested drones %s are not available",
                    [d.drone_id for d in unavailable],
                )
                selected = [d for d in selected if d.is_available]
        else:
            available = self.available_drones
            available.sort(key=lambda d: -d.battery_pct)
            needed = self._estimate_drones_needed(command)
            selected = available[:needed]

        if not selected:
            logger.error("No drones available for mission %s", command.mission_type)
            return []

        self._mission_counter += 1
        mission_id = f"M{self._mission_counter:04d}"
        for drone in selected:
            drone.status = DroneStatus.IN_MISSION
            drone.current_mission_id = mission_id

        logger.info(
            "Allocated drones %s to mission %s (%s)",
            [d.drone_id for d in selected],
            mission_id,
            command.mission_type.value,
        )
        return selected

    def release_drones(self, drone_ids: list[int]):
        for did in drone_ids:
            if did in self._drones:
                self._drones[did].status = DroneStatus.IDLE
                self._drones[did].current_mission_id = None

    def handle_failover(self, failed_drone_id: int) -> DroneState | None:
        """When a drone fails, attempt to reassign its mission sector to a backup."""
        if not self._config.failover_enabled:
            return None

        failed = self._drones.get(failed_drone_id)
        if not failed or not failed.current_mission_id:
            return None

        mission_id = failed.current_mission_id
        failed.status = DroneStatus.ERROR
        failed.current_mission_id = None

        backup = next(
            (d for d in self.available_drones if d.battery_pct >= self._config.min_battery_pct),
            None,
        )
        if backup:
            backup.status = DroneStatus.IN_MISSION
            backup.current_mission_id = mission_id
            logger.info(
                "Failover: drone %d replacing drone %d for mission %s",
                backup.drone_id, failed_drone_id, mission_id,
            )
            return backup

        logger.warning("No backup drone available for failover of drone %d", failed_drone_id)
        return None

    def check_battery_warnings(self) -> list[DroneState]:
        low = [
            d for d in self._drones.values()
            if d.battery_pct < self._config.min_battery_pct and d.status == DroneStatus.IN_MISSION
        ]
        for d in low:
            logger.warning("Drone %d battery critical: %.0f%%", d.drone_id, d.battery_pct)
        return low

    def get_fleet_state_summary(self) -> dict:
        return {
            "total": len(self._drones),
            "available": len(self.available_drones),
            "drones": [
                {
                    "id": d.drone_id,
                    "status": d.status.value,
                    "battery_pct": d.battery_pct,
                    "lat": d.lat,
                    "lon": d.lon,
                    "alt_m": d.alt_m,
                    "sensor": d.sensor_payload,
                    "mission": d.current_mission_id,
                }
                for d in self._drones.values()
            ],
        }

    @staticmethod
    def _estimate_drones_needed(command: MissionCommand) -> int:
        match command.mission_type.value:
            case "area_search":
                return 3
            case "perimeter_patrol":
                return 2
            case "formation_flight":
                return 3
            case "point_inspection":
                return 1
            case "relay_station":
                n = len(command.station_points) if command.station_points else 1
                return n
            case "return_to_home" | "takeoff" | "land":
                return 0
            case _:
                return 1
