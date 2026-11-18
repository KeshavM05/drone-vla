"""ROS2 node that subscribes to speech text and publishes parsed mission commands as JSON."""

from __future__ import annotations

import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from drone_vla.config import load_config
from drone_vla.nlp.intent_parser import IntentParser


class IntentParserNode(Node):
    def __init__(self):
        super().__init__("intent_parser_node")
        config = load_config()
        self._parser = IntentParser(config.llm)

        self._sub = self.create_subscription(
            String, "operator/speech_text", self._on_speech, 10
        )
        self._pub = self.create_publisher(String, "operator/mission_command", 10)
        self.get_logger().info("Intent parser node started")

    def _on_speech(self, msg: String):
        text = msg.data
        self.get_logger().info(f"Parsing: {text}")

        try:
            intent = self._parser.parse(text)
            out = String()
            out.data = intent.model_dump_json()
            self._pub.publish(out)

            for cmd in intent.commands:
                self.get_logger().info(
                    f"Command: {cmd.mission_type.value} "
                    f"(drones={cmd.assignment.drone_ids}, alt={cmd.altitude_agl_m}m)"
                )

            if intent.clarification_needed:
                self.get_logger().warn(f"Clarification needed: {intent.clarification_needed}")

        except Exception as e:
            self.get_logger().error(f"Parse failed: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = IntentParserNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
