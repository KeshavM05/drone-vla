"""Individual drone abstraction wrapping MAVSDK-Python for ArduPilot."""

from __future__ import annotations

import asyncio
import logging
from enum import Enum

from mavsdk import System
from mavsdk.action import ActionError
from mavsdk.offboard import OffboardError, PositionNedYaw

from drone_vla.orchestrator.path_planner import Waypoint

logger = logging.getLogger(__name__)


class FlightMode(str, Enum):
    IDLE = "idle"
    ARMING = "arming"
    TAKING_OFF = "taking_off"
    IN_FLIGHT = "in_flight"
    LANDING = "landing"
    RETURNING = "returning"


class Drone:
    def __init__(self, drone_id: int, system_address: str):
        self.drone_id = drone_id
        self._address = system_address
        self._system = System()
        self._mode = FlightMode.IDLE
        self._connected = False

    @property
    def mode(self) -> FlightMode:
        return self._mode

    @property
    def system(self) -> System:
        return self._system

    async def connect(self):
        logger.info("Drone %d connecting to %s", self.drone_id, self._address)
        await self._system.connect(system_address=self._address)

        async for state in self._system.core.connection_state():
            if state.is_connected:
                self._connected = True
                logger.info("Drone %d connected", self.drone_id)
                break

    async def wait_for_ready(self, timeout: float = 30.0):
        async for health in self._system.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                logger.info("Drone %d GPS and home position OK", self.drone_id)
                return
        raise TimeoutError(f"Drone {self.drone_id} not ready within {timeout}s")

    async def arm_and_takeoff(self, altitude_m: float = 20.0):
        self._mode = FlightMode.ARMING
        logger.info("Drone %d arming", self.drone_id)
        await self._system.action.arm()

        self._mode = FlightMode.TAKING_OFF
        await self._system.action.set_takeoff_altitude(altitude_m)
        await self._system.action.takeoff()
        logger.info("Drone %d taking off to %.1fm", self.drone_id, altitude_m)

        await self._wait_for_altitude(altitude_m * 0.9)
        self._mode = FlightMode.IN_FLIGHT

    async def goto_waypoint(self, wp: Waypoint):
        await self._system.action.goto_location(
            wp.lat, wp.lon, wp.alt_m, wp.heading_deg or 0.0
        )

    async def execute_waypoints(self, waypoints: list[Waypoint], acceptance_radius_m: float = 2.0):
        self._mode = FlightMode.IN_FLIGHT
        for i, wp in enumerate(waypoints):
            logger.debug("Drone %d -> WP %d/%d (%.6f, %.6f, %.1fm)",
                         self.drone_id, i + 1, len(waypoints), wp.lat, wp.lon, wp.alt_m)
            await self.goto_waypoint(wp)
            await self._wait_for_position(wp, acceptance_radius_m)
            if wp.loiter_s:
                await asyncio.sleep(wp.loiter_s)

    async def return_to_launch(self):
        self._mode = FlightMode.RETURNING
        logger.info("Drone %d returning to launch", self.drone_id)
        await self._system.action.return_to_launch()

    async def land(self):
        self._mode = FlightMode.LANDING
        logger.info("Drone %d landing", self.drone_id)
        await self._system.action.land()

    async def get_position(self) -> dict:
        async for pos in self._system.telemetry.position():
            return {
                "lat": pos.latitude_deg,
                "lon": pos.longitude_deg,
                "abs_alt_m": pos.absolute_altitude_m,
                "rel_alt_m": pos.relative_altitude_m,
            }
        return {}

    async def get_battery(self) -> float:
        async for bat in self._system.telemetry.battery():
            return bat.remaining_percent * 100.0
        return 0.0

    async def get_heading(self) -> float:
        async for heading in self._system.telemetry.heading():
            return heading.heading_deg
        return 0.0

    async def stream_telemetry(self):
        """Yield telemetry updates as dicts."""
        async for pos in self._system.telemetry.position():
            battery = await self.get_battery()
            heading = await self.get_heading()
            yield {
                "drone_id": self.drone_id,
                "lat": pos.latitude_deg,
                "lon": pos.longitude_deg,
                "alt_m": pos.relative_altitude_m,
                "heading_deg": heading,
                "battery_pct": battery,
                "mode": self._mode.value,
            }

    async def _wait_for_altitude(self, target_alt_m: float, timeout: float = 30.0):
        async for pos in self._system.telemetry.position():
            if pos.relative_altitude_m >= target_alt_m:
                return
        raise TimeoutError(f"Drone {self.drone_id} did not reach altitude {target_alt_m}m")

    async def _wait_for_position(self, wp: Waypoint, radius_m: float, timeout: float = 60.0):
        import math
        async for pos in self._system.telemetry.position():
            dlat = (pos.latitude_deg - wp.lat) * 111_320
            dlon = (pos.longitude_deg - wp.lon) * 111_320 * math.cos(math.radians(wp.lat))
            dist = math.sqrt(dlat**2 + dlon**2)
            if dist < radius_m:
                return
