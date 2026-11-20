"""PX4 swarm test: connect to 3 PX4 SITL drones via UDP, takeoff, fly triangle, land."""

import asyncio
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

from mavsdk import System
from mavsdk.offboard import PositionNedYaw, OffboardError

DRONES = [
    {"instance": 1, "udp_port": 14541, "grpc_port": 50051},
    {"instance": 2, "udp_port": 14542, "grpc_port": 50052},
    {"instance": 3, "udp_port": 14543, "grpc_port": 50053},
]


async def connect_drone(cfg: dict) -> System:
    i = cfg["instance"]
    drone = System(port=cfg["grpc_port"])
    addr = f"udp://:{cfg['udp_port']}"
    print(f"[Drone {i}] Connecting on {addr}...")
    await drone.connect(system_address=addr)

    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"[Drone {i}] Connected!")
            break

    print(f"[Drone {i}] Waiting for GPS fix...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print(f"[Drone {i}] GPS OK")
            break

    return drone


async def arm_and_takeoff(drone: System, instance: int, altitude: float = 20.0):
    print(f"[Drone {instance}] Arming...")
    await drone.action.arm()
    print(f"[Drone {instance}] Taking off to {altitude}m...")
    await drone.action.set_takeoff_altitude(altitude)
    await drone.action.takeoff()


async def fly_to_position(drone: System, instance: int, north: float, east: float, alt: float, yaw: float):
    await drone.offboard.set_position_ned(PositionNedYaw(0.0, 0.0, -alt, 0.0))
    try:
        await drone.offboard.start()
    except OffboardError as e:
        print(f"[Drone {instance}] Offboard failed: {e}")
        return

    print(f"[Drone {instance}] Flying to N={north:.0f} E={east:.0f}...")
    await drone.offboard.set_position_ned(PositionNedYaw(north, east, -alt, yaw))
    await asyncio.sleep(12)

    async for pos in drone.telemetry.position():
        print(
            f"[Drone {instance}] Position — Alt: {pos.relative_altitude_m:.1f}m "
            f"Lat: {pos.latitude_deg:.6f} Lon: {pos.longitude_deg:.6f}"
        )
        break

    await drone.offboard.stop()


async def main():
    print("=" * 60)
    print("  PX4 Swarm Test — 3 Drones")
    print("=" * 60)

    drones = []
    for cfg in DRONES:
        d = await connect_drone(cfg)
        drones.append((cfg["instance"], d))

    print("\n--- Arming and taking off ---")
    await asyncio.gather(
        *[arm_and_takeoff(d, i) for i, d in drones]
    )
    print("Climbing... (15s)")
    await asyncio.sleep(15)

    print("\n--- Flying to triangle formation ---")
    targets = [
        (30.0, 0.0, 20.0, 0.0),
        (-15.0, 25.0, 20.0, 120.0),
        (-15.0, -25.0, 20.0, 240.0),
    ]
    await asyncio.gather(
        *[fly_to_position(d, i, *t) for (i, d), t in zip(drones, targets)]
    )

    print("\nHolding formation for 10s...")
    await asyncio.sleep(10)

    print("\n--- Landing all drones ---")
    await asyncio.gather(*[d.action.land() for _, d in drones])
    await asyncio.sleep(15)
    print("\nDone! PX4 Swarm test complete.")


if __name__ == "__main__":
    asyncio.run(main())
