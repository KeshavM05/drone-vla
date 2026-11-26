"""Launch the Drone VLA Command Center.

Two modes:
  --live    Connect to PX4 SITL via ROS2 (requires PX4 + MicroXRCE-DDS running)
  (default) Simulated telemetry for UI development without PX4
"""

import sys
import os
import logging
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

from drone_vla.config import load_config
from drone_vla.orchestrator.fleet_manager import FleetManager, DroneStatus
from drone_vla.orchestrator.mission_executor import MissionExecutor
from drone_vla.orchestrator.path_planner import Waypoint


def discover_camera_topics(num_drones: int) -> dict[int, str]:
    """Find camera image topics from ROS2 topic list."""
    import subprocess

    result = subprocess.run(
        ["ros2", "topic", "list"], capture_output=True, text=True, timeout=5
    )
    topics = result.stdout.strip().split("\n") if result.returncode == 0 else []
    camera_topics = [t for t in topics if "imager/image" in t and "sensor_msgs" not in t]

    mapping: dict[int, str] = {}
    for topic in camera_topics:
        for drone_id in range(1, num_drones + 1):
            if f"_{drone_id}/" in topic or (drone_id == 1 and f"cam_45/" in topic):
                mapping[drone_id] = topic
                break
        else:
            if len(mapping) < num_drones:
                next_id = len(mapping) + 1
                mapping[next_id] = topic

    return mapping


def start_live_mode(config, num_drones=3, camera_topics=None):
    """Wire ROS2 SwarmManager → FleetManager → MissionExecutor → Web bridge."""
    import rclpy
    from drone_vla.flight.swarm_node import SwarmManager
    from drone_vla.flight.collision_avoidance import CAConfig
    from drone_vla.web.app import bridge
    from drone_vla.web.camera import CameraManager

    rclpy.init()

    ca_config = CAConfig(
        altitude_base_m=config.fleet.collision_avoidance.altitude_base_m,
        altitude_layer_m=config.fleet.collision_avoidance.altitude_layer_m,
        warning_distance_m=config.fleet.collision_avoidance.warning_distance_m,
        critical_distance_m=config.fleet.collision_avoidance.critical_distance_m,
    )
    swarm = SwarmManager(
        num_drones=num_drones,
        ca_config=ca_config,
        home_lat=config.simulation.home_lat,
        home_lon=config.simulation.home_lon,
    )

    fleet = FleetManager(config.fleet)
    for i in range(1, num_drones + 1):
        fleet.register_drone(i, status=DroneStatus.ARMED)

    def send_waypoints_to_swarm(drone_id, waypoints):
        """Bridge MissionExecutor waypoints → SwarmManager GPS commands."""
        if waypoints == "RTH":
            swarm.command_land()
            return
        gps_wps = [(wp.lat, wp.lon, wp.alt_m) for wp in waypoints]
        swarm.assign_gps_waypoints(drone_id, gps_wps)

    async def async_send_waypoints(drone_id, waypoints):
        send_waypoints_to_swarm(drone_id, waypoints)

    executor = MissionExecutor(fleet, async_send_waypoints)

    bridge.set_swarm_manager(swarm)
    bridge.set_executor(fleet, executor)

    cam = CameraManager()
    if not camera_topics:
        camera_topics = discover_camera_topics(num_drones)
    for drone_id, topic in camera_topics.items():
        cam.subscribe(swarm, drone_id, topic)
    bridge.set_camera_manager(cam)

    if config.detection.enabled:
        from drone_vla.cv.detector import DetectionManager
        detector = DetectionManager(
            yolo_model=config.detection.yolo_model,
            confidence=config.detection.confidence,
            inference_interval=config.detection.inference_interval,
            color_markers=config.detection.color_markers,
        )
        detector.set_camera(cam)
        detector.on_detection(
            lambda did, dets: bridge.add_log(
                "warning",
                f"DETECTION on drone {did}: "
                + ", ".join(f"{d.label} ({d.confidence:.0%})" for d in dets),
                "cv",
            )
        )
        detector.start()
        bridge.set_detector(detector)

    def spin_ros2():
        rclpy.spin(swarm)

    ros2_thread = threading.Thread(target=spin_ros2, daemon=True)
    ros2_thread.start()

    print(f"  ROS2 SwarmManager: {num_drones} drones")
    print(f"  Altitude layers: {ca_config.altitude_base_m}m + {ca_config.altitude_layer_m}m/drone")
    print(f"  Home: ({config.simulation.home_lat}, {config.simulation.home_lon})")
    if camera_topics:
        print(f"  Cameras: {list(camera_topics.keys())}")
    else:
        print(f"  Cameras: none found (start ros_gz_image bridge)")
    return swarm


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Drone VLA Command Center")
    ap.add_argument("--live", action="store_true", help="Connect to PX4 SITL via ROS2")
    ap.add_argument("--drones", type=int, default=3, help="Number of drones (default: 3)")
    ap.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    args = ap.parse_args()

    config = load_config()
    port = args.port

    print(f"\n  Drone VLA Command Center")
    print(f"  http://localhost:{port}")

    swarm = None
    if args.live:
        try:
            swarm = start_live_mode(config, args.drones)
            print(f"  Mode: LIVE (PX4 ROS2)")
        except ImportError as e:
            print(f"  WARNING: ROS2 not available ({e})")
            print(f"  Falling back to SIMULATED mode")
        except Exception as e:
            print(f"  WARNING: ROS2 init failed ({e})")
            print(f"  Falling back to SIMULATED mode")
    else:
        print(f"  Mode: SIMULATED (use --live for PX4)")

    print()

    import uvicorn
    from drone_vla.web.app import app
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
