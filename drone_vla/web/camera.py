"""Camera manager — subscribes to ROS2 image topics, serves JPEG frames for web streaming."""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

TARGET_W = 480
TARGET_H = 360
MIN_INTERVAL = 0.25


class CameraManager:
    """Thread-safe store of latest JPEG frame per drone, filled by ROS2 callbacks."""

    def __init__(self, jpeg_quality: int = 50):
        self._frames: dict[int, bytes] = {}
        self._raw_frames: dict[int, np.ndarray] = {}
        self._lock = threading.Lock()
        self._quality = jpeg_quality
        self._last_encode: dict[int, float] = {}
        self._subs: list = []

    def subscribe(self, node, drone_id: int, topic: str):
        from sensor_msgs.msg import Image
        from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        sub = node.create_subscription(
            Image, topic, lambda msg, did=drone_id: self._on_image(did, msg), qos
        )
        self._subs.append(sub)
        logger.info("Camera %d subscribed: %s", drone_id, topic)

    def _on_image(self, drone_id: int, msg):
        now = time.monotonic()
        last = self._last_encode.get(drone_id, 0.0)
        if now - last < MIN_INTERVAL:
            return
        try:
            arr = np.frombuffer(msg.data, dtype=np.uint8).reshape(
                msg.height, msg.width, 3
            )
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            if bgr.shape[1] > TARGET_W:
                bgr = cv2.resize(bgr, (TARGET_W, TARGET_H), interpolation=cv2.INTER_AREA)
            ok, buf = cv2.imencode(
                ".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, self._quality]
            )
            if ok:
                with self._lock:
                    self._frames[drone_id] = buf.tobytes()
                    self._raw_frames[drone_id] = bgr
                self._last_encode[drone_id] = now
        except Exception as e:
            logger.debug("Frame encode error drone %d: %s", drone_id, e)

    def get_frame(self, drone_id: int) -> Optional[bytes]:
        with self._lock:
            return self._frames.get(drone_id)

    def get_raw_frame(self, drone_id: int) -> Optional[np.ndarray]:
        with self._lock:
            f = self._raw_frames.get(drone_id)
            return f.copy() if f is not None else None

    def get_active_cameras(self) -> list[int]:
        with self._lock:
            return sorted(self._frames.keys())
