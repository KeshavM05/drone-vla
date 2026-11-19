"""Swarm test: connect to 3 SITL drones, takeoff, fly to separate positions, land."""

import asyncio
from mavsdk import System
from mavsdk.offboard import PositionNedYaw, OffboardError


async def connect_drone(instance: int, port: int) -> System:
    drone = System(mavsdk_server_port=50050 + instance)
    print(f"[Drone {instance}] Connecting on udp://:{port}...")
    await drone.connect(system_address=f"udp://:{port}")

    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"[Drone {instance}] Connected!")
            break

    print(f"[Drone {instance}] Waiting for GPS fix...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print(f"[Drone {instance}] GPS OK")
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


async def land(drone: System, instance: int):
    print(f"[Drone {instance}] Landing...")
    await drone.action.land()


async def main():
    ports = [14550, 14560, 14570]

    print("=" * 60)
    print("  Swarm Test — 3 Drones")
    print("=" * 60)

    # Connect all drones
    drones = await asyncio.gather(
        *[connect_drone(i, port) for i, port in enumerate(ports)]
    )

    # Arm and takeoff all
    print("\n--- Arming and taking off ---")
    await asyncio.gather(
        *[arm_and_takeoff(d, i) for i, d in enumerate(drones)]
    )
    print("Climbing... (15s)")
    await asyncio.sleep(15)

    # Fly to separate positions (triangle pattern)
    print("\n--- Flying to triangle formation ---")
    targets = [
        (30.0, 0.0, 20.0, 0.0),     # Drone 0: north
        (-15.0, 25.0, 20.0, 120.0),  # Drone 1: south-east
        (-15.0, -25.0, 20.0, 240.0), # Drone 2: south-west
    ]
    await asyncio.gather(
        *[fly_to_position(d, i, *t) for i, (d, t) in enumerate(zip(drones, targets))]
    )

    print("\nHolding formation for 10s...")
    await asyncio.sleep(10)

    # Land all
    print("\n--- Landing all drones ---")
    await asyncio.gather(
        *[land(d, i) for i, d in enumerate(drones)]
    )
    await asyncio.sleep(15)
    print("\nDone! Swarm test complete.")


if __name__ == "__main__":
    asyncio.run(main())
