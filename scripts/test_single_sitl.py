"""Day 1: Connect to a single SITL instance — use this to validate SITL is working."""

import asyncio
from mavsdk import System


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

    print("Climbing... (waiting 10s)")
    await asyncio.sleep(10)

    async for position in drone.telemetry.position():
        print(
            f"Position — Alt: {position.relative_altitude_m:.1f}m "
            f"Lat: {position.latitude_deg:.6f} Lon: {position.longitude_deg:.6f}"
        )
        break

    async for battery in drone.telemetry.battery():
        print(f"Battery — {battery.remaining_percent * 100:.0f}% ({battery.voltage_v:.1f}V)")
        break

    print("Landing...")
    await drone.action.land()

    print("Waiting for landing... (15s)")
    await asyncio.sleep(15)
    print("Done! SITL connection validated.")


if __name__ == "__main__":
    asyncio.run(main())
