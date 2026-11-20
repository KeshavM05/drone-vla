"""Per-drone PX4 ROS2 controller — publishes offboard commands, subscribes to telemetry."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from px4_msgs.msg import (
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleCommand,
    VehicleStatus,
    VehicleLocalPosition,
    VehicleGlobalPosition,
)

PX4_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)


@dataclass
class DronePosition:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    lat: float = 0.0
    lon: float = 0.0
    alt_m: float = 0.0
    heading_rad: float = 0.0
    valid: bool = False


class PX4Drone:
    """Manages ROS2 pub/sub for a single PX4 instance."""

    def __init__(self, node: Node, drone_id: int):
        self.node = node
        self.id = drone_id
        ns = f"/px4_{drone_id}"

        self.offboard_pub = node.create_publisher(
            OffboardControlMode, f"{ns}/fmu/in/offboard_control_mode", 10
        )
        self.trajectory_pub = node.create_publisher(
            TrajectorySetpoint, f"{ns}/fmu/in/trajectory_setpoint", 10
        )
        self.command_pub = node.create_publisher(
            VehicleCommand, f"{ns}/fmu/in/vehicle_command", 10
        )

        node.create_subscription(
            VehicleStatus, f"{ns}/fmu/out/vehicle_status_v1",
            self._on_status, PX4_QOS,
        )
        node.create_subscription(
            VehicleLocalPosition, f"{ns}/fmu/out/vehicle_local_position",
            self._on_local_pos, PX4_QOS,
        )
        node.create_subscription(
            VehicleGlobalPosition, f"{ns}/fmu/out/vehicle_global_position",
            self._on_global_pos, PX4_QOS,
        )

        self.nav_state: int = 0
        self.arming_state: int = 0
        self.pos = DronePosition()

        self._target: Optional[tuple[float, float, float]] = None
        self._target_yaw: float = float("nan")

    def _on_status(self, msg: VehicleStatus):
        self.nav_state = msg.nav_state
        self.arming_state = msg.arming_state

    def _on_local_pos(self, msg: VehicleLocalPosition):
        self.pos.x = msg.x
        self.pos.y = msg.y
        self.pos.z = msg.z
        self.pos.vx = msg.vx
        self.pos.vy = msg.vy
        self.pos.vz = msg.vz
        self.pos.heading_rad = msg.heading
        self.pos.valid = True

    def _on_global_pos(self, msg: VehicleGlobalPosition):
        self.pos.lat = msg.lat
        self.pos.lon = msg.lon
        self.pos.alt_m = msg.alt

    @property
    def is_armed(self) -> bool:
        return self.arming_state == VehicleStatus.ARMING_STATE_ARMED

    @property
    def is_offboard(self) -> bool:
        return self.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD

    @property
    def altitude_agl(self) -> float:
        return -self.pos.z if self.pos.valid else 0.0

    def _timestamp_us(self) -> int:
        return int(self.node.get_clock().now().nanoseconds / 1000)

    def publish_offboard_mode(self):
        msg = OffboardControlMode()
        msg.position = True
        msg.velocity = False
        msg.acceleration = False
        msg.attitude = False
        msg.body_rate = False
        msg.timestamp = self._timestamp_us()
        self.offboard_pub.publish(msg)

    def publish_trajectory(self, x: float, y: float, z: float, yaw: float = float("nan")):
        self._target = (x, y, z)
        self._target_yaw = yaw
        msg = TrajectorySetpoint()
        msg.position = [x, y, z]
        msg.yaw = yaw
        msg.timestamp = self._timestamp_us()
        self.trajectory_pub.publish(msg)

    def publish_current_target(self):
        if self._target is not None:
            self.publish_trajectory(*self._target, self._target_yaw)

    def send_command(self, command: int, param1: float = 0.0, param2: float = 0.0):
        msg = VehicleCommand()
        msg.param1 = param1
        msg.param2 = param2
        msg.command = command
        msg.target_system = self.id + 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1
        msg.from_external = True
        msg.timestamp = self._timestamp_us()
        self.command_pub.publish(msg)

    def arm(self, force: bool = True):
        self.send_command(
            VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM,
            1.0,
            21196.0 if force else 0.0,
        )

    def disarm(self):
        self.send_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 0.0)

    def set_offboard_mode(self):
        self.send_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1.0, 6.0)

    def command_land(self):
        self.send_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)

    def distance_to(self, other: PX4Drone) -> float:
        if not self.pos.valid or not other.pos.valid:
            return float("inf")
        dx = self.pos.x - other.pos.x
        dy = self.pos.y - other.pos.y
        dz = self.pos.z - other.pos.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def horizontal_distance_to(self, other: PX4Drone) -> float:
        if not self.pos.valid or not other.pos.valid:
            return float("inf")
        dx = self.pos.x - other.pos.x
        dy = self.pos.y - other.pos.y
        return math.sqrt(dx * dx + dy * dy)

    def distance_to_point(self, x: float, y: float, z: float) -> float:
        if not self.pos.valid:
            return float("inf")
        dx = self.pos.x - x
        dy = self.pos.y - y
        dz = self.pos.z - z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def at_target(self, tolerance_m: float = 2.0) -> bool:
        if self._target is None or not self.pos.valid:
            return False
        return self.distance_to_point(*self._target) < tolerance_m
