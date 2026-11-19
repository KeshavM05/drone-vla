"""Day 4: Send drones to waypoints and verify position convergence."""

import asyncio
import math
from mavsdk import System


async def goto_and_wait(drone: System, instance: int, lat: float, lon: float, alt: float, tolerance: float = 2.0):
    print(f"[Drone {instance}] Going to ({lat:.6f}, {lon:.6f}) at {alt:.0f}m...")
    await drone.action.goto_location(lat, lon, alt, 0.0)

    while True:
        async for pos in drone.telemetry.position():
            dlat = (pos.latitude_deg - lat) * 111320
            dlon = (pos.longitude_deg - lon) * 111320 * math.cos(math.radians(lat))
            dalt = pos.relative_altitude_m - alt
            dist = math.sqrt(dlat**2 + dlon**2 + dalt**2)
            if dist < tolerance:
                print(f"[Drone {instance}] Arrived! (error: {dist:.1f}m)")
                return
            break
        await asyncio.sleep(1)


async def connect_drone(instance: int, port: int) -> System:
    drone = System(mavsdk_server_port=50050 + instance)
    await drone.connect(system_address=f"udp://:{port}")

    async for state in drone.core.connection_state():
        if state.is_connected:
            break

    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            break

    await drone.action.arm()
    await drone.action.set_takeoff_altitude(20.0)
    await drone.action.takeoff()
    await asyncio.sleep(10)
    return drone


async def main():
    ports = [14550, 14560, 14570]
    # Kingston, Ontario area — triangle formation 30m apart
    base_lat, base_lon = 44.225, -76.495
    offset = 0.0003  # ~33m

    triangle = [
        (base_lat + offset, base_lon, 25.0),
        (base_lat - offset / 2, base_lon - offset, 25.0),
        (base_lat - offset / 2, base_lon + offset, 25.0),
    ]

    print("=" * 60)
    print("Waypoint Navigation Test — Triangle Formation")
    print("=" * 60)

    drones = await asyncio.gather(
        *[connect_drone(i, port) for i, port in enumerate(ports)]
    )
    print("\nAll drones airborne. Sending to triangle positions...\n")

    await asyncio.gather(
        *[goto_and_wait(d, i, *wp) for i, (d, wp) in enumerate(zip(drones, triangle))]
    )

    print("\nTriangle formation achieved! Holding for 10 seconds...")
    await asyncio.sleep(10)

    print("\nReturning to launch...")
    await asyncio.gather(*[d.action.return_to_launch() for d in drones])
    await asyncio.sleep(20)
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
