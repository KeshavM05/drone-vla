"""ROS2 node that publishes transcribed speech as String messages."""

from __future__ import annotations

import asyncio
import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from drone_vla.config import load_config
from drone_vla.stt.whisper_engine import WhisperSTT


class STTNode(Node):
    def __init__(self):
        super().__init__("stt_node")
        self._pub = self.create_publisher(String, "operator/speech_text", 10)

        config = load_config()
        self._stt = WhisperSTT(config.stt)
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_stt, daemon=True)
        self._thread.start()
        self.get_logger().info("STT node started")

    def _run_stt(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._stream())

    async def _stream(self):
        async for text in self._stt.stream_transcriptions():
            msg = String()
            msg.data = text
            self._pub.publish(msg)
            self.get_logger().info(f"Published: {text}")

    def destroy_node(self):
        self._stt.stop()
        self._loop.call_soon_threadsafe(self._loop.stop)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = STTNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
