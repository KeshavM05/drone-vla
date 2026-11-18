---
title: "Week 1: Foundation"
description: Detailed breakdown of environment setup and SITL validation tasks for Days 1-7
tags:
  - plan
  - week-1
  - foundation
---
# Week 1: Foundation (Nov 18-24)

Parent: [Master Plan](./master-plan.md)

## Goal

ArduPilot SITL + Gazebo running with 3 drones controllable via Python scripts.

## Day 1 (Mon 11/18): ArduPilot SITL Single Instance

### Tasks

1. **Choose install method:**
   - Docker (recommended for Windows): `docker pull ardupilot/ardupilot-dev-ros`
   - WSL2 native: clone ArduPilot, run `install-prereqs-ubuntu.sh`
   - Decision criteria: Docker is simpler; native gives faster iteration

2. **Boot single ArduCopter SITL:**
   ```bash
   sim_vehicle.py -v ArduCopter -l 47.397742,8.545594,488,0 --out=udp:127.0.0.1:14550
   ```

3. **Verify MAVProxy console:**
   - `arm throttle`
   - `mode GUIDED`
   - `takeoff 20`

### Done When
- `sim_vehicle.py` starts without errors
- MAVProxy console shows telemetry
- Manual takeoff command works

### Potential Blockers
- Windows Docker networking (use `host.docker.internal`)
- WSL2 GUI forwarding for Gazebo (install VcXsrv or use WSLg)
- ArduPilot build dependencies on WSL2

## Day 2 (Tue 11/19): Multi-Instance SITL + Gazebo

### Tasks

1. **Launch 3 SITL instances on separate ports:**
   ```bash
   sim_vehicle.py -v ArduCopter --instance 0 -l 47.397742,8.545594,488,0 --out=udp:127.0.0.1:14550
   sim_vehicle.py -v ArduCopter --instance 1 -l 47.397842,8.545694,488,0 --out=udp:127.0.0.1:14560
   sim_vehicle.py -v ArduCopter --instance 2 -l 47.397942,8.545794,488,0 --out=udp:127.0.0.1:14570
   ```

2. **Install Gazebo Harmonic** and the ArduPilot Gazebo plugin

3. **Verify all 3 drones appear in Gazebo world**

### Done When
- 3 separate SITL processes running
- All 3 visible in Gazebo
- Each responds independently to MAVProxy commands

## Day 3 (Wed 11/20): MAVSDK-Python Connection

### Tasks

1. Install MAVSDK: `pip install mavsdk`

2. Write `scripts/test_connect.py` that:
   - Connects to all 3 instances concurrently with asyncio
   - Arms all 3
   - Takes off all 3 to 20m

3. Validate all 3 drones take off simultaneously in Gazebo

### Done When
- Python script connects to 3 SITL instances
- All 3 arm and take off programmatically

## Day 4 (Thu 11/21): Waypoint Navigation

### Tasks

1. Write `scripts/test_waypoints.py` that:
   - Sends each drone to a different GPS waypoint
   - Implements position convergence check (within 2m)
   - Tests sequential waypoint following

2. Test formation: send all 3 to triangle positions

3. Measure latency from command to convergence

### Done When
- Drones navigate to commanded GPS coordinates
- Position error < 2m
- Triangle formation holds visually

## Day 5 (Fri 11/22): Telemetry Streaming

### Tasks

1. Write `scripts/test_telemetry.py` that:
   - Subscribes to position, battery, heading for all 3
   - Prints formatted table at 1Hz
   - Detects drone going offline

2. Validate `MAVLinkBridge` streams from SITL correctly

### Done When
- Terminal shows real-time telemetry from all 3
- Heartbeat timeout detection works

## Day 6 (Sat 11/23): Checkpoint 1

1. Record screen (OBS or similar)
2. Show: 3 drones in Gazebo, Python takeoff, triangle formation, live telemetry
3. Share with accountability partner

## Day 7 (Sun 11/24): Buffer

Catch up on anything that slipped. If on track, rest.