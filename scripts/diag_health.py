"""Diagnostic: connect to SITL, check GPS/EKF/health, try to arm."""

import asyncio
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

from mavsdk import System


async def main():
    drone = System(port=50051)
    print("Connecting...")
    await drone.connect(system_address="tcpout://127.0.0.1:5760")

    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Connected!")
            break

    print("\nChecking GPS (timeout 20s)...")
    try:
        gps = await asyncio.wait_for(get_first(drone.telemetry.gps_info()), timeout=20)
        print(f"  fix={gps.fix_type}  sats={gps.num_satellites}")
    except asyncio.TimeoutError:
        print("  GPS info: TIMED OUT (no GPS data from SITL)")

    print("\nChecking position (timeout 10s)...")
    try:
        pos = await asyncio.wait_for(get_first(drone.telemetry.position()), timeout=10)
        print(f"  lat={pos.latitude_deg}  lon={pos.longitude_deg}  alt={pos.relative_altitude_m}")
    except asyncio.TimeoutError:
        print("  Position: TIMED OUT")

    print("\nHealth (5 samples, 2s apart):")
    count = 0
    async for health in drone.telemetry.health():
        print(
            f"  [{count}] gps_ok={health.is_global_position_ok}"
            f"  home_ok={health.is_home_position_ok}"
            f"  armable={health.is_armable}"
        )
        count += 1
        if count >= 5 or health.is_armable:
            break
        await asyncio.sleep(2)

    print("\nDone.")


async def get_first(async_iter):
    async for item in async_iter:
        return item


asyncio.run(main())
