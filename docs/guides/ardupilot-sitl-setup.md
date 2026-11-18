---
title: ArduPilot SITL Setup
description: How to run ArduPilot Software-in-the-Loop simulation with Gazebo and ros_gz_bridge
tags:
  - guide
  - ardupilot
  - sitl
  - gazebo
---
# ArduPilot SITL Setup

This guide covers setting up ArduPilot SITL (Software-in-the-Loop) simulation for development and testing.

## Why ArduPilot over PX4?

ArduPilot was chosen because it has a functional `ros_gz_bridge` for camera and sensor data streaming into ROS2. PX4 lacked this integration at the time of evaluation. See [System Overview](../architecture/system-overview.md) for the full architecture rationale.

## Option 1: Docker (Recommended)

The `docker-compose.yml` at the project root spins up 3 ArduPilot SITL instances + Gazebo + ros_gz_bridge.

```bash
docker compose up
```

This starts:
- `ardupilot_sitl_1` — ArduCopter instance 0 on port 5760 (MAVLink out: UDP 14550)
- `ardupilot_sitl_2` — ArduCopter instance 1 on port 5770 (MAVLink out: UDP 14560)
- `ardupilot_sitl_3` — ArduCopter instance 2 on port 5780 (MAVLink out: UDP 14570)
- `gazebo_sim` — Gazebo simulation environment
- `ros_gz_bridge` — Bridges Gazebo sensor topics to ROS2

### Verify connections

```bash
# Check SITL instances are running
docker ps

# Test MAVLink connection from host
python -c "from mavsdk import System; import asyncio; s=System(); asyncio.run(s.connect('udp://:14550'))"
```

## Option 2: Native Install (WSL2 / Linux)

For development without Docker:

### Install ArduPilot

```bash
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot
Tools/environment_install/install-prereqs-ubuntu.sh -y
. ~/.profile
```

### Run multi-instance SITL

```bash
# Terminal 1: Instance 0
sim_vehicle.py -v ArduCopter --instance 0 -l 47.397742,8.545594,488,0 --out=udp:127.0.0.1:14550

# Terminal 2: Instance 1
sim_vehicle.py -v ArduCopter --instance 1 -l 47.397842,8.545694,488,0 --out=udp:127.0.0.1:14560

# Terminal 3: Instance 2
sim_vehicle.py -v ArduCopter --instance 2 -l 47.397942,8.545794,488,0 --out=udp:127.0.0.1:14570
```

### Install Gazebo + ros_gz_bridge

For ROS2 Humble on Ubuntu 22.04:

```bash
sudo apt install ros-humble-ros-gz-bridge ros-humble-ros-gz-image ros-humble-ros-gz-sim
```

## Configuration

SITL connection settings are in `config/default.yaml`:

```yaml
simulation:
  sitl_instances: 3
  start_port: 14550
  home_lat: 47.397742
  home_lon: 8.545594
  home_alt: 488.0
```

The `MAVLinkBridge` connects to each instance at `udp://:<start_port + i*10>` where `i` is the instance index (0, 1, 2).