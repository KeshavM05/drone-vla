"""Test camera bridge: subscribe to PX4 Gazebo camera, save a frame as PNG."""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
import numpy as np
import sys


class CameraTest(Node):
    def __init__(self, topic: str):
        super().__init__("camera_test")
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        self.sub = self.create_subscription(Image, topic, self.on_image, qos)
        self.frame_count = 0
        self.get_logger().info(f"Subscribed to {topic}, waiting for frames...")

    def on_image(self, msg: Image):
        self.frame_count += 1
        self.get_logger().info(
            f"Frame {self.frame_count}: {msg.width}x{msg.height} {msg.encoding}"
        )
        if self.frame_count == 5:
            arr = np.frombuffer(msg.data, dtype=np.uint8).reshape(
                msg.height, msg.width, 3
            )
            try:
                from PIL import Image as PILImage

                img = PILImage.fromarray(arr)
                out = "/tmp/drone_cam_frame.png"
                img.save(out)
                self.get_logger().info(f"Saved frame to {out}")
            except ImportError:
                out = "/tmp/drone_cam_frame.raw"
                arr.tofile(out)
                self.get_logger().info(
                    f"PIL not available, saved raw to {out} ({msg.width}x{msg.height} rgb8)"
                )
            raise SystemExit(0)


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "/camera"
    rclpy.init()
    node = CameraTest(topic)
    try:
        rclpy.spin(node)
    except SystemExit:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
