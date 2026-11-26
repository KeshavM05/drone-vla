"""YOLO + color-marker detection pipeline for drone camera feeds."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

COLOR_RANGES: dict[str, tuple[np.ndarray, np.ndarray]] = {
    "orange": (np.array([5, 120, 120]), np.array([25, 255, 255])),
    "red_lo": (np.array([0, 120, 120]), np.array([5, 255, 255])),
    "red_hi": (np.array([170, 120, 120]), np.array([180, 255, 255])),
    "yellow": (np.array([22, 120, 120]), np.array([38, 255, 255])),
    "blue": (np.array([100, 120, 80]), np.array([130, 255, 255])),
}

MIN_MARKER_AREA = 300
MORPH_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

BOX_COLORS = {
    "yolo": (0, 255, 0),
    "color": (0, 165, 255),
}


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]
    source: str

    @property
    def center_px(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "confidence": round(self.confidence, 2),
            "bbox": list(self.bbox),
            "center_px": list(self.center_px),
            "source": self.source,
        }


class DetectionManager:
    """Runs YOLO + color detection on camera frames in a background thread."""

    def __init__(
        self,
        yolo_model: str = "yolov8n.pt",
        confidence: float = 0.4,
        inference_interval: float = 0.2,
        color_markers: bool = True,
    ):
        self._yolo_model_name = yolo_model
        self._confidence = confidence
        self._interval = inference_interval
        self._color_markers = color_markers

        self._model = None
        self._camera = None
        self._annotated_frames: dict[int, bytes] = {}
        self._detections: dict[int, list[Detection]] = {}
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[int, list[Detection]], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def set_camera(self, cam):
        self._camera = cam

    def on_detection(self, callback: Callable[[int, list[Detection]], None]):
        self._callbacks.append(callback)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("DetectionManager started (model=%s, interval=%.1fs)",
                     self._yolo_model_name, self._interval)

    def stop(self):
        self._running = False

    def _load_model(self):
        try:
            from ultralytics import YOLO
            self._model = YOLO(self._yolo_model_name)
            logger.info("YOLO model loaded: %s", self._yolo_model_name)
        except Exception as e:
            logger.error("Failed to load YOLO model: %s", e)

    def _loop(self):
        self._load_model()
        while self._running:
            if not self._camera:
                time.sleep(1)
                continue

            cameras = self._camera.get_active_cameras()
            for drone_id in cameras:
                raw = self._camera.get_raw_frame(drone_id)
                if raw is None:
                    continue

                dets: list[Detection] = []

                if self._model:
                    dets.extend(self._run_yolo(raw))

                if self._color_markers:
                    dets.extend(self._detect_colors(raw))

                annotated = self._draw(raw.copy(), dets)
                _, buf = cv2.imencode(
                    ".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 70]
                )

                with self._lock:
                    prev = self._detections.get(drone_id, [])
                    self._detections[drone_id] = dets
                    if buf is not None:
                        self._annotated_frames[drone_id] = buf.tobytes()

                if dets and not prev:
                    self._fire_callbacks(drone_id, dets)

            time.sleep(self._interval)

    def _run_yolo(self, frame: np.ndarray) -> list[Detection]:
        results = self._model(frame, verbose=False, conf=self._confidence)
        dets = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                label = self._model.names[cls_id]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
                dets.append(Detection(label, conf, (x1, y1, x2, y2), "yolo"))
        return dets

    def _detect_colors(self, frame: np.ndarray) -> list[Detection]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        dets = []
        seen_labels: dict[str, float] = {}

        for name, (lo, hi) in COLOR_RANGES.items():
            display = name.split("_")[0]
            mask = cv2.inRange(hsv, lo, hi)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, MORPH_KERNEL)
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            for c in contours:
                area = cv2.contourArea(c)
                if area < MIN_MARKER_AREA:
                    continue
                x, y, w, h = cv2.boundingRect(c)
                conf = min(area / 2000.0, 0.99)
                label = f"{display}_marker"
                if label in seen_labels and conf <= seen_labels[label]:
                    continue
                seen_labels[label] = conf
                dets.append(Detection(label, conf, (x, y, x + w, y + h), "color"))

        return dets

    def _draw(self, frame: np.ndarray, dets: list[Detection]) -> np.ndarray:
        for d in dets:
            x1, y1, x2, y2 = d.bbox
            color = BOX_COLORS.get(d.source, (0, 255, 0))
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"{d.label} {d.confidence:.0%}"
            (tw, th), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(
                frame, label, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1,
            )
        return frame

    def _fire_callbacks(self, drone_id: int, dets: list[Detection]):
        for cb in self._callbacks:
            try:
                cb(drone_id, dets)
            except Exception as e:
                logger.debug("Detection callback error: %s", e)

    def get_annotated_frame(self, drone_id: int) -> Optional[bytes]:
        with self._lock:
            return self._annotated_frames.get(drone_id)

    def get_detections(self, drone_id: int) -> list[Detection]:
        with self._lock:
            return list(self._detections.get(drone_id, []))
