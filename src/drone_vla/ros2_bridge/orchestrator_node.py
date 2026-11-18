"""ROS2 node that receives parsed mission commands and orchestrates the drone fleet."""

from __future__ import annotations

import asyncio
import json
import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from drone_vla.config import load_config
from drone_vla.flight.mavlink_bridge import MAVLinkBridge
from drone_vla.nlp.schemas import ParsedIntent
from drone_vla.orchestrator.fleet_manager import FleetManager
from drone_vla.orchestrator.mission_executor import MissionExecutor


class OrchestratorNode(Node):
    def __init__(self):
        super().__init__("orchestrator_node")
        config = load_config()

        self._fleet = FleetManager(config.fleet)
        self._bridge = MAVLinkBridge(config.fleet, config.simulation, self._fleet)
        self._executor = MissionExecutor(self._fleet, self._bridge.send_waypoints)

        self._sub = self.create_subscription(
            String, "operator/mission_command", self._on_command, 10
        )
        self._status_pub = self.create_publisher(String, "fleet/status", 10)
        self._status_timer = self.create_timer(1.0, self._publish_status)

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        asyncio.run_coroutine_threadsafe(self._bridge.connect_all(), self._loop)
        self.get_logger().info("Orchestrator node started")

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _on_command(self, msg: String):
        try:
            intent = ParsedIntent.model_validate_json(msg.data)
            for cmd in intent.commands:
                self.get_logger().info(f"Executing: {cmd.mission_type.value}")
                asyncio.run_coroutine_threadsafe(
                    self._executor.execute_command(cmd), self._loop
                )
        except Exception as e:
            self.get_logger().error(f"Command execution failed: {e}")

    def _publish_status(self):
        status = self._fleet.get_fleet_state_summary()
        msg = String()
        msg.data = json.dumps(status)
        self._status_pub.publish(msg)

    def destroy_node(self):
        asyncio.run_coroutine_threadsafe(self._bridge.shutdown(), self._loop)
        self._loop.call_soon_threadsafe(self._loop.stop)
        super().destroy_node()


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
