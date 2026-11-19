"""Day 1: Connect to ArduPilot SITL via MAVSDK, arm, and takeoff."""

import asyncio
from mavsdk import System


async def connect_and_takeoff(instance: int, port: int, altitude: float = 20.0):
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
            print(f"[Drone {instance}] GPS fix acquired")
            break

    print(f"[Drone {instance}] Arming...")
    await drone.action.arm()

    print(f"[Drone {instance}] Taking off to {altitude}m...")
    await drone.action.set_takeoff_altitude(altitude)
    await drone.action.takeoff()

    await asyncio.sleep(10)

    async for position in drone.telemetry.position():
        print(
            f"[Drone {instance}] Alt: {position.relative_altitude_m:.1f}m "
            f"Lat: {position.latitude_deg:.6f} Lon: {position.longitude_deg:.6f}"
        )
        break

    return drone


async def main():
    ports = [14550, 14560, 14570]

    print("=" * 60)
    print("ArduPilot SITL Connection Test — 3 Drones")
    print("=" * 60)

    drones = await asyncio.gather(
        *[connect_and_takeoff(i, port) for i, port in enumerate(ports)]
    )

    print("\nAll 3 drones airborne. Hovering for 15 seconds...")
    await asyncio.sleep(15)

    for i, drone in enumerate(drones):
        async for position in drone.telemetry.position():
            print(
                f"[Drone {i}] Final position — "
                f"Alt: {position.relative_altitude_m:.1f}m "
                f"Lat: {position.latitude_deg:.6f} Lon: {position.longitude_deg:.6f}"
            )
            break

    print("\nLanding all drones...")
    await asyncio.gather(*[d.action.land() for d in drones])
    await asyncio.sleep(10)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
