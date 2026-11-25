"""Central ROS2 node managing the PX4 drone swarm.

Responsibilities:
- Creates PX4Drone controllers for each drone instance
- Runs collision avoidance checks every tick
- Aggregates telemetry and feeds FleetManager
- Executes waypoint sequences with altitude deconfliction
"""

from __future__ import annotations

import logging
import math
import time
from enum import Enum
from typing import Optional

import rclpy
from rclpy.node import Node

from drone_vla.flight.px4_drone import PX4Drone
from drone_vla.flight.collision_avoidance import CAConfig, CollisionAvoidance
from drone_vla.flight.geo import gps_to_ned

logger = logging.getLogger(__name__)


class SwarmState(str, Enum):
    INITIALIZING = "initializing"
    PREFLIGHT = "preflight"
    ARMING = "arming"
    ARMED = "armed"
    IN_FLIGHT = "in_flight"
    LANDING = "landing"
    LANDED = "landed"


class DroneTask:
    """A waypoint sequence assigned to one drone."""

    def __init__(self, drone_id: int, waypoints: list[tuple[float, float, float]]):
        self.drone_id = drone_id
        self.waypoints = waypoints
        self.current_index = 0
        self.complete = False

    @property
    def current_target(self) -> tuple[float, float, float] | None:
        if self.current_index < len(self.waypoints):
            return self.waypoints[self.current_index]
        return None

    def advance(self) -> bool:
        self.current_index += 1
        if self.current_index >= len(self.waypoints):
            self.complete = True
            return False
        return True


class SwarmManager(Node):
    def __init__(
        self,
        num_drones: int = 3,
        ca_config: CAConfig | None = None,
        tick_rate_hz: float = 10.0,
        home_lat: float = 47.397742,
        home_lon: float = 8.545594,
    ):
        super().__init__("swarm_manager")
        self.drones: list[PX4Drone] = [
            PX4Drone(self, i) for i in range(1, num_drones + 1)
        ]
        self.ca = CollisionAvoidance(ca_config)
        self.state = SwarmState.INITIALIZING
        self._state_start = time.time()
        self._tasks: dict[int, DroneTask] = {}
        self._tick_count = 0
        self._armed_sent = False
        self.home_lat = home_lat
        self.home_lon = home_lon

        self._timer = self.create_timer(1.0 / tick_rate_hz, self._tick)
        self.get_logger().info(
            f"SwarmManager started: {num_drones} drones, "
            f"CA layers at {self.ca.config.altitude_base_m}m "
            f"+ {self.ca.config.altitude_layer_m}m/drone"
        )

    def _elapsed(self) -> float:
        return time.time() - self._state_start

    def _set_state(self, state: SwarmState):
        self.state = state
        self._state_start = time.time()
        self.get_logger().info(f"Swarm state -> {state.value}")

    def _tick(self):
        self._tick_count += 1

        for d in self.drones:
            d.publish_offboard_mode()

        self.ca.check_separations(self.drones)

        if self.state == SwarmState.INITIALIZING:
            self._handle_init()
        elif self.state == SwarmState.PREFLIGHT:
            self._handle_preflight()
        elif self.state == SwarmState.ARMING:
            self._handle_arming()
        elif self.state == SwarmState.ARMED:
            self._handle_armed()
        elif self.state == SwarmState.IN_FLIGHT:
            self._handle_in_flight()
        elif self.state == SwarmState.LANDING:
            self._handle_landing()

    def _handle_init(self):
        for d in self.drones:
            z = self.ca.assigned_altitude_ned(d.id)
            d.publish_trajectory(0.0, 0.0, z)
        if self._elapsed() > 2.0:
            self._set_state(SwarmState.PREFLIGHT)

    def _handle_preflight(self):
        for d in self.drones:
            z = self.ca.assigned_altitude_ned(d.id)
            d.publish_trajectory(0.0, 0.0, z)

        if self._tick_count % 20 == 0:
            for d in self.drones:
                self.get_logger().info(
                    f"[Drone {d.id}] armed={d.is_armed} offboard={d.is_offboard} "
                    f"pos_valid={d.pos.valid}"
                )

        if self._elapsed() > 2.0 and not self._armed_sent:
            for d in self.drones:
                d.set_offboard_mode()
                d.arm(force=True)
            self._armed_sent = True
            self._set_state(SwarmState.ARMING)

    def _handle_arming(self):
        for d in self.drones:
            z = self.ca.assigned_altitude_ned(d.id)
            d.publish_trajectory(0.0, 0.0, z)

        if all(d.is_armed for d in self.drones):
            self.get_logger().info("All drones armed")
            self._set_state(SwarmState.ARMED)
        elif self._elapsed() > 3.0:
            for d in self.drones:
                if not d.is_armed:
                    d.set_offboard_mode()
                    d.arm(force=True)
            self._state_start = time.time()

    def _handle_armed(self):
        for d in self.drones:
            z = self.ca.assigned_altitude_ned(d.id)
            d.publish_trajectory(0.0, 0.0, z)
        if self._elapsed() > 1.0:
            self._set_state(SwarmState.IN_FLIGHT)

    def _handle_in_flight(self):
        for d in self.drones:
            task = self._tasks.get(d.id)
            if task and not task.complete:
                target = task.current_target
                if target:
                    x, y, z = self.ca.deconflict_target(d.id, *target)
                    x, y, z = self.ca.apply_avoidance_to_target(d.id, x, y, z)
                    yaw = math.atan2(y - d.pos.y, x - d.pos.x)
                    d.publish_trajectory(x, y, z, yaw)

                    if d.at_target(tolerance_m=2.0):
                        if not task.advance():
                            self.get_logger().info(
                                f"Drone {d.id} completed waypoint sequence"
                            )
                else:
                    d.publish_current_target()
            else:
                z = self.ca.assigned_altitude_ned(d.id)
                d.publish_trajectory(0.0, 0.0, z)

    def _handle_landing(self):
        if self._elapsed() < 0.5:
            for d in self.drones:
                d.command_land()
        if self._elapsed() > 20.0:
            self._set_state(SwarmState.LANDED)

    def assign_task(self, drone_id: int, waypoints: list[tuple[float, float, float]]):
        deconflicted = [
            self.ca.deconflict_target(drone_id, x, y, z)
            for x, y, z in waypoints
        ]
        self._tasks[drone_id] = DroneTask(drone_id, deconflicted)
        self.get_logger().info(
            f"Drone {drone_id}: assigned {len(waypoints)} waypoints "
            f"(altitude layer: {-self.ca.assigned_altitude_ned(drone_id):.0f}m AGL)"
        )

    def assign_gps_waypoints(
        self, drone_id: int, gps_waypoints: list[tuple[float, float, float]]
    ):
        """Assign GPS waypoints (lat, lon, alt_agl_m) — converted to NED internally."""
        ned_waypoints = [
            gps_to_ned(lat, lon, alt, self.home_lat, self.home_lon)
            for lat, lon, alt in gps_waypoints
        ]
        self.assign_task(drone_id, ned_waypoints)

    def assign_formation(self, positions: dict[int, tuple[float, float, float]]):
        for drone_id, (x, y, z) in positions.items():
            self.assign_task(drone_id, [(x, y, z)])

    def command_takeoff(self):
        if self.state in (SwarmState.INITIALIZING, SwarmState.PREFLIGHT):
            self._set_state(SwarmState.PREFLIGHT)
        elif self.state == SwarmState.ARMED:
            self._set_state(SwarmState.IN_FLIGHT)

    def command_land(self, drone_ids: list[int] | None = None):
        if drone_ids is None:
            self._tasks.clear()
            self._set_state(SwarmState.LANDING)
        else:
            for did in drone_ids:
                self._tasks.pop(did, None)
                drone = next((d for d in self.drones if d.id == did), None)
                if drone:
                    drone.command_land()

    def command_hold(self):
        for d in self.drones:
            if d.pos.valid:
                z = self.ca.assigned_altitude_ned(d.id)
                d.publish_trajectory(d.pos.x, d.pos.y, z)
        self._tasks.clear()

    def get_telemetry(self) -> list[dict]:
        result = []
        for d in self.drones:
            task = self._tasks.get(d.id)
            result.append({
                "drone_id": d.id,
                "armed": d.is_armed,
                "offboard": d.is_offboard,
                "x": d.pos.x,
                "y": d.pos.y,
                "z": d.pos.z,
                "alt_agl_m": d.altitude_agl,
                "lat": d.pos.lat,
                "lon": d.pos.lon,
                "vx": d.pos.vx,
                "vy": d.pos.vy,
                "heading_rad": d.pos.heading_rad,
                "assigned_alt_m": -self.ca.assigned_altitude_ned(d.id),
                "task_active": task is not None and not task.complete if task else False,
                "task_wp": f"{task.current_index}/{len(task.waypoints)}" if task else "—",
            })
        return result

    def get_proximity_alerts(self) -> list[dict]:
        return [
            {
                "drone_a": a.drone_a,
                "drone_b": a.drone_b,
                "distance_m": round(a.distance_m, 1),
                "critical": a.is_critical,
            }
            for a in self.ca.alerts
        ]
