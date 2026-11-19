"""Day 5: Stream telemetry from all 3 drones — position, battery, heading at 1Hz."""

import asyncio
from mavsdk import System


class DroneMonitor:
    def __init__(self, instance: int, port: int):
        self.instance = instance
        self.port = port
        self.drone = System(mavsdk_server_port=50050 + instance)
        self.lat = 0.0
        self.lon = 0.0
        self.alt = 0.0
        self.heading = 0.0
        self.battery_pct = 0.0
        self.battery_v = 0.0
        self.connected = False

    async def connect(self):
        await self.drone.connect(system_address=f"udp://:{self.port}")
        async for state in self.drone.core.connection_state():
            if state.is_connected:
                self.connected = True
                break

    async def stream_position(self):
        async for pos in self.drone.telemetry.position():
            self.lat = pos.latitude_deg
            self.lon = pos.longitude_deg
            self.alt = pos.relative_altitude_m

    async def stream_heading(self):
        async for heading in self.drone.telemetry.heading():
            self.heading = heading.heading_deg

    async def stream_battery(self):
        async for bat in self.drone.telemetry.battery():
            self.battery_pct = bat.remaining_percent * 100
            self.battery_v = bat.voltage_v


async def print_table(monitors: list[DroneMonitor]):
    while True:
        print("\033[2J\033[H")  # clear screen
        print(f"{'Drone':<8} {'Lat':>12} {'Lon':>12} {'Alt(m)':>8} {'Hdg':>6} {'Batt%':>7} {'Volt':>6} {'Status':<10}")
        print("-" * 80)
        for m in monitors:
            status = "CONNECTED" if m.connected else "OFFLINE"
            print(
                f"  {m.instance:<6} {m.lat:>12.6f} {m.lon:>12.6f} {m.alt:>8.1f} "
                f"{m.heading:>6.0f} {m.battery_pct:>6.0f}% {m.battery_v:>5.1f}V {status:<10}"
            )
        print(f"\n  Press Ctrl+C to stop")
        await asyncio.sleep(1)


async def main():
    ports = [14550, 14560, 14570]
    monitors = [DroneMonitor(i, port) for i, port in enumerate(ports)]

    print("Connecting to 3 SITL instances...")
    await asyncio.gather(*[m.connect() for m in monitors])
    print("All connected! Starting telemetry streams...\n")

    tasks = []
    for m in monitors:
        tasks.append(asyncio.create_task(m.stream_position()))
        tasks.append(asyncio.create_task(m.stream_heading()))
        tasks.append(asyncio.create_task(m.stream_battery()))
    tasks.append(asyncio.create_task(print_table(monitors)))

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
