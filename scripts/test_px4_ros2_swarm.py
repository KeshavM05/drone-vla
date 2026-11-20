"""PX4 swarm test via ROS2: arm, takeoff, triangle formation, land — 3 drones."""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from px4_msgs.msg import (
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleCommand,
    VehicleStatus,
    VehicleLocalPosition,
)
import time
import math


QOS_PROFILE = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)


class DroneController:
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
        self.status_sub = node.create_subscription(
            VehicleStatus, f"{ns}/fmu/out/vehicle_status_v1", self._status_cb, QOS_PROFILE
        )
        self.local_pos_sub = node.create_subscription(
            VehicleLocalPosition,
            f"{ns}/fmu/out/vehicle_local_position",
            self._local_pos_cb,
            QOS_PROFILE,
        )
        self.nav_state = 0
        self.arming_state = 0
        self.local_pos = None

    def _status_cb(self, msg):
        self.nav_state = msg.nav_state
        self.arming_state = msg.arming_state

    def _local_pos_cb(self, msg):
        self.local_pos = msg

    def send_offboard_mode(self):
        msg = OffboardControlMode()
        msg.position = True
        msg.velocity = False
        msg.acceleration = False
        msg.attitude = False
        msg.body_rate = False
        msg.timestamp = int(self.node.get_clock().now().nanoseconds / 1000)
        self.offboard_pub.publish(msg)

    def send_trajectory(self, x: float, y: float, z: float, yaw: float = float("nan")):
        msg = TrajectorySetpoint()
        msg.position = [x, y, z]
        msg.yaw = yaw
        msg.timestamp = int(self.node.get_clock().now().nanoseconds / 1000)
        self.trajectory_pub.publish(msg)

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
        msg.timestamp = int(self.node.get_clock().now().nanoseconds / 1000)
        self.command_pub.publish(msg)

    def arm(self, force=True):
        self.send_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1.0, 21196.0 if force else 0.0)

    def disarm(self):
        self.send_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 0.0)

    def set_offboard_mode(self):
        self.send_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1.0, 6.0)

    def land(self):
        self.send_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)

    @property
    def is_armed(self):
        return self.arming_state == VehicleStatus.ARMING_STATE_ARMED

    @property
    def is_offboard(self):
        return self.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD


class SwarmTestNode(Node):
    def __init__(self):
        super().__init__("swarm_test")
        self.drones = [DroneController(self, i) for i in range(1, 4)]
        self.timer = self.create_timer(0.1, self.timer_callback)
        self.phase = "init"
        self.phase_start = time.time()
        self.offboard_counter = 0
        self.get_logger().info("Swarm test node started — 3 drones")

    def elapsed(self):
        return time.time() - self.phase_start

    def set_phase(self, phase: str):
        self.phase = phase
        self.phase_start = time.time()
        self.get_logger().info(f"=== Phase: {phase} ===")

    def timer_callback(self):
        for d in self.drones:
            d.send_offboard_mode()

        if self.phase == "init":
            if self.elapsed() > 2.0:
                for d in self.drones:
                    d.send_trajectory(0.0, 0.0, -5.0)
                self.set_phase("preflight")

        elif self.phase == "preflight":
            for d in self.drones:
                d.send_trajectory(0.0, 0.0, -5.0)
            self.offboard_counter += 1
            if self.offboard_counter == 10:
                for d in self.drones:
                    self.get_logger().info(
                        f"[Drone {d.id}] Status: arming_state={d.arming_state}, nav_state={d.nav_state}, has_pos={d.local_pos is not None}"
                    )
            if self.offboard_counter > 20:
                for d in self.drones:
                    d.set_offboard_mode()
                    d.arm(force=True)
                    self.get_logger().info(f"[Drone {d.id}] Force-arm + offboard sent")
                self.set_phase("arming")

        elif self.phase == "arming":
            for d in self.drones:
                d.send_trajectory(0.0, 0.0, -5.0)
            all_armed = all(d.is_armed for d in self.drones)
            if all_armed:
                self.get_logger().info("All drones armed!")
                self.set_phase("takeoff")
            elif self.elapsed() > 3.0:
                for d in self.drones:
                    if not d.is_armed:
                        d.set_offboard_mode()
                        d.arm(force=True)
                        self.get_logger().info(
                            f"[Drone {d.id}] Retry force-arm (arming_state={d.arming_state}, nav_state={d.nav_state})"
                        )
                self.phase_start = time.time()

        elif self.phase == "takeoff":
            for d in self.drones:
                d.send_trajectory(0.0, 0.0, -20.0)
            if self.elapsed() > 15.0:
                self.get_logger().info("Takeoff complete, moving to formation")
                self.set_phase("formation")

        elif self.phase == "formation":
            targets = [
                (30.0, 0.0, -20.0, 0.0),
                (-15.0, 25.0, -20.0, 2.094),
                (-15.0, -25.0, -20.0, 4.189),
            ]
            for d, (x, y, z, yaw) in zip(self.drones, targets):
                d.send_trajectory(x, y, z, yaw)
            if self.elapsed() > 15.0:
                for d in self.drones:
                    if d.local_pos:
                        self.get_logger().info(
                            f"[Drone {d.id}] Pos: x={d.local_pos.x:.1f} "
                            f"y={d.local_pos.y:.1f} z={d.local_pos.z:.1f}"
                        )
                self.set_phase("hold")

        elif self.phase == "hold":
            targets = [
                (30.0, 0.0, -20.0, 0.0),
                (-15.0, 25.0, -20.0, 2.094),
                (-15.0, -25.0, -20.0, 4.189),
            ]
            for d, (x, y, z, yaw) in zip(self.drones, targets):
                d.send_trajectory(x, y, z, yaw)
            if self.elapsed() > 10.0:
                self.get_logger().info("Formation hold complete, landing")
                self.set_phase("landing")

        elif self.phase == "landing":
            for d in self.drones:
                d.land()
            if self.elapsed() > 15.0:
                self.get_logger().info("Swarm test complete!")
                self.set_phase("done")

        elif self.phase == "done":
            self.timer.cancel()
            raise SystemExit(0)


def main():
    rclpy.init()
    node = SwarmTestNode()
    try:
        rclpy.spin(node)
    except SystemExit:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
