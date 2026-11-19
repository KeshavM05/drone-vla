"""Day 2: Connect to SITL via MAVSDK, takeoff, fly a square, and land."""

import asyncio
from mavsdk import System
from mavsdk.offboard import PositionNedYaw, OffboardError


async def main():
    drone = System()

    print("Connecting to SITL on udp://:14550...")
    await drone.connect(system_address="udp://:14550")

    print("Waiting for connection...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Connected!")
            break

    print("Waiting for GPS fix...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("GPS fix OK")
            break

    print("Arming...")
    await drone.action.arm()
    print("Armed!")

    print("Taking off to 20m...")
    await drone.action.set_takeoff_altitude(20.0)
    await drone.action.takeoff()
    await asyncio.sleep(10)

    async for pos in drone.telemetry.position():
        print(f"Altitude: {pos.relative_altitude_m:.1f}m")
        break

    print("\n--- Flying a square pattern (NED offboard) ---")

    await drone.offboard.set_position_ned(PositionNedYaw(0.0, 0.0, -20.0, 0.0))

    try:
        await drone.offboard.start()
    except OffboardError as e:
        print(f"Offboard start failed: {e}")
        await drone.action.land()
        return

    waypoints = [
        PositionNedYaw(20.0, 0.0, -20.0, 0.0),
        PositionNedYaw(20.0, 20.0, -20.0, 90.0),
        PositionNedYaw(0.0, 20.0, -20.0, 180.0),
        PositionNedYaw(0.0, 0.0, -20.0, 270.0),
    ]

    for i, wp in enumerate(waypoints):
        print(f"  Waypoint {i+1}: N={wp.north_m:.0f} E={wp.east_m:.0f} heading={wp.yaw_deg:.0f}")
        await drone.offboard.set_position_ned(wp)
        await asyncio.sleep(8)

    print("Square complete!")

    await drone.offboard.stop()

    async for pos in drone.telemetry.position():
        print(
            f"Final position — Alt: {pos.relative_altitude_m:.1f}m "
            f"Lat: {pos.latitude_deg:.6f} Lon: {pos.longitude_deg:.6f}"
        )
        break

    print("Landing...")
    await drone.action.land()
    await asyncio.sleep(15)
    print("Done! MAVSDK control validated.")


if __name__ == "__main__":
    asyncio.run(main())
