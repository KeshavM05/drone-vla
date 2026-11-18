"""MAVLink bridge — manages connections to multiple ArduPilot SITL instances via MAVSDK."""

from __future__ import annotations

import asyncio
import logging

from drone_vla.config import FleetConfig, SimulationConfig
from drone_vla.flight.drone import Drone
from drone_vla.orchestrator.fleet_manager import DroneStatus, FleetManager
from drone_vla.orchestrator.path_planner import Waypoint

logger = logging.getLogger(__name__)


class MAVLinkBridge:
    def __init__(
        self,
        fleet_config: FleetConfig,
        sim_config: SimulationConfig,
        fleet_manager: FleetManager,
    ):
        self._fleet_config = fleet_config
        self._sim_config = sim_config
        self._fleet_manager = fleet_manager
        self._drones: dict[int, Drone] = {}
        self._telemetry_tasks: dict[int, asyncio.Task] = {}

    async def connect_all(self):
        tasks = []
        for i in range(self._sim_config.sitl_instances):
            drone_id = i + 1
            port = self._sim_config.start_port + i * 10
            address = f"udp://:{port}"
            drone = Drone(drone_id, address)
            self._drones[drone_id] = drone
            self._fleet_manager.register_drone(
                drone_id,
                lat=self._sim_config.home_lat,
                lon=self._sim_config.home_lon,
                alt=0.0,
                status=DroneStatus.OFFLINE,
            )
            tasks.append(self._connect_drone(drone))

        await asyncio.gather(*tasks)
        logger.info("All %d drones connected", len(self._drones))

    async def _connect_drone(self, drone: Drone):
        try:
            await drone.connect()
            await drone.wait_for_ready()
            self._fleet_manager.update_telemetry(
                drone.drone_id, status=DroneStatus.IDLE
            )
            self._telemetry_tasks[drone.drone_id] = asyncio.create_task(
                self._telemetry_loop(drone)
            )
        except Exception as e:
            logger.error("Failed to connect drone %d: %s", drone.drone_id, e)

    async def _telemetry_loop(self, drone: Drone):
        try:
            async for telem in drone.stream_telemetry():
                self._fleet_manager.update_telemetry(
                    drone.drone_id,
                    lat=telem["lat"],
                    lon=telem["lon"],
                    alt_m=telem["alt_m"],
                    heading_deg=telem["heading_deg"],
                    battery_pct=telem["battery_pct"],
                )
        except Exception as e:
            logger.error("Telemetry loop error for drone %d: %s", drone.drone_id, e)
            self._fleet_manager.update_telemetry(
                drone.drone_id, status=DroneStatus.ERROR
            )

    async def send_waypoints(self, drone_id: int, waypoints: list[Waypoint] | str):
        drone = self._drones.get(drone_id)
        if not drone:
            logger.error("Unknown drone %d", drone_id)
            return

        if waypoints == "RTH":
            await drone.return_to_launch()
            return

        if isinstance(waypoints, list):
            await drone.execute_waypoints(waypoints)

    async def arm_and_takeoff_all(self, altitude_m: float = 20.0):
        tasks = [
            drone.arm_and_takeoff(altitude_m)
            for drone in self._drones.values()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def land_all(self):
        tasks = [drone.land() for drone in self._drones.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def shutdown(self):
        for task in self._telemetry_tasks.values():
            task.cancel()
        await asyncio.gather(*self._telemetry_tasks.values(), return_exceptions=True)
        logger.info("MAVLink bridge shut down")

    def get_drone(self, drone_id: int) -> Drone | None:
        return self._drones.get(drone_id)
