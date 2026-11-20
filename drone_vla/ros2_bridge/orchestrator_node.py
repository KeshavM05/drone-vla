"""ROS2 node that receives parsed mission commands and orchestrates the drone fleet."""

from __future__ import annotations

import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from drone_vla.config import load_config
from drone_vla.nlp.schemas import ParsedIntent
from drone_vla.orchestrator.fleet_manager import FleetManager
from drone_vla.orchestrator.mission_executor import MissionExecutor


class OrchestratorNode(Node):
    def __init__(self):
        super().__init__("orchestrator_node")
        config = load_config()

        self._fleet = FleetManager(config.fleet)
        self._executor = MissionExecutor(self._fleet, self._dispatch_waypoints)

        self._sub = self.create_subscription(
            String, "operator/mission_command", self._on_command, 10
        )
        self._status_pub = self.create_publisher(String, "fleet/status", 10)
        self._status_timer = self.create_timer(1.0, self._publish_status)

        self.get_logger().info("Orchestrator node started (PX4 ROS2 mode)")

    async def _dispatch_waypoints(self, drone_id: int, waypoints: list):
        self.get_logger().info(f"Dispatching {len(waypoints)} waypoints to drone {drone_id}")

    def _on_command(self, msg: String):
        try:
            intent = ParsedIntent.model_validate_json(msg.data)
            for cmd in intent.commands:
                self.get_logger().info(f"Executing: {cmd.mission_type.value}")
        except Exception as e:
            self.get_logger().error(f"Command execution failed: {e}")

    def _publish_status(self):
        status = self._fleet.get_fleet_state_summary()
        msg = String()
        msg.data = json.dumps(status)
        self._status_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = OrchestratorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
