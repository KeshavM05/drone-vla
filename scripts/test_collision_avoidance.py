"""Test collision avoidance: arm 3 drones, fly them toward the same point, verify altitude layering and separation."""

import rclpy
import time
import sys

from drone_vla.flight.swarm_node import SwarmManager, SwarmState
from drone_vla.flight.collision_avoidance import CAConfig


def main():
    rclpy.init()

    ca_config = CAConfig(
        altitude_base_m=15.0,
        altitude_layer_m=5.0,
        warning_distance_m=10.0,
        critical_distance_m=5.0,
    )
    swarm = SwarmManager(num_drones=3, ca_config=ca_config)

    swarm.get_logger().info(
        "=== Collision Avoidance Test ===\n"
        "  Drone 1: 15m AGL\n"
        "  Drone 2: 20m AGL\n"
        "  Drone 3: 25m AGL\n"
        "Phase 1: Arm + takeoff to layered altitudes\n"
        "Phase 2: Send all 3 drones to same XY point (0,30) — altitudes must stay separated\n"
        "Phase 3: Send to converging points — test proximity alerts\n"
        "Phase 4: Land"
    )

    phase = "startup"
    phase_start = time.time()

    def elapsed():
        return time.time() - phase_start

    def set_phase(name):
        nonlocal phase, phase_start
        phase = name
        phase_start = time.time()
        swarm.get_logger().info(f">>> Test phase: {phase}")

    timer_handle = None

    def tick():
        nonlocal phase

        if phase == "startup":
            if swarm.state == SwarmState.IN_FLIGHT or elapsed() > 30.0:
                set_phase("shared_objective")
                swarm.get_logger().info(
                    "All drones flying. Sending all to same XY (0, 30) — "
                    "altitudes deconflicted by CA"
                )
                for d in swarm.drones:
                    swarm.assign_task(d.id, [(0.0, 30.0, -20.0)])

        elif phase == "shared_objective":
            if elapsed() > 15.0:
                telem = swarm.get_telemetry()
                swarm.get_logger().info("--- Telemetry at shared objective ---")
                for t in telem:
                    swarm.get_logger().info(
                        f"  Drone {t['drone_id']}: "
                        f"pos=({t['x']:.1f}, {t['y']:.1f}, {t['z']:.1f}) "
                        f"alt_agl={t['alt_agl_m']:.1f}m "
                        f"(assigned {t['assigned_alt_m']:.0f}m)"
                    )
                alerts = swarm.get_proximity_alerts()
                if alerts:
                    swarm.get_logger().info(f"  Proximity alerts: {alerts}")
                else:
                    swarm.get_logger().info(
                        "  No proximity alerts — altitude layering working"
                    )

                set_phase("converge")
                swarm.get_logger().info(
                    "Now sending drones to nearby points to test proximity monitoring"
                )
                swarm.assign_task(1, [(20.0, 0.0, -15.0)])
                swarm.assign_task(2, [(22.0, 0.0, -20.0)])
                swarm.assign_task(3, [(24.0, 0.0, -25.0)])

        elif phase == "converge":
            if elapsed() % 3.0 < 0.15:
                alerts = swarm.get_proximity_alerts()
                if alerts:
                    swarm.get_logger().info(f"Proximity alerts: {alerts}")

            if elapsed() > 15.0:
                telem = swarm.get_telemetry()
                swarm.get_logger().info("--- Telemetry at converge ---")
                for t in telem:
                    swarm.get_logger().info(
                        f"  Drone {t['drone_id']}: "
                        f"pos=({t['x']:.1f}, {t['y']:.1f}, {t['z']:.1f}) "
                        f"alt_agl={t['alt_agl_m']:.1f}m"
                    )
                set_phase("land")
                swarm.command_land()

        elif phase == "land":
            if elapsed() > 20.0:
                swarm.get_logger().info("=== Test complete ===")
                raise SystemExit(0)

    timer_handle = swarm.create_timer(0.5, tick)

    try:
        rclpy.spin(swarm)
    except SystemExit:
        pass
    finally:
        swarm.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
