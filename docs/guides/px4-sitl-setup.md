---
title: PX4 SITL Setup
description: How to run PX4 v1.16 multi-drone SITL with Gazebo Harmonic, MicroXRCE-DDS, and ROS2
tags:
  - guide
  - px4
  - sitl
  - gazebo
  - ros2
---
# PX4 SITL Setup

This guide covers setting up PX4 v1.16 SITL with Gazebo Harmonic for multi-drone simulation with ROS2.

## Why PX4 over ArduPilot?

We initially chose ArduPilot but switched to PX4 on Day 1 (2026-11-19) because:

- ArduPilot multi-instance SITL was unstable — instances crashed and interfered with each other
- PX4 provides native ROS2 integration via MicroXRCE-DDS (no ros_gz_bridge needed for command/control)
- PX4 multi-drone Gazebo spawning is reliable with proper env vars

See [System Overview](../architecture/system-overview.md) for the full architecture.

## Prerequisites

- Ubuntu 22.04
- Gazebo Harmonic (installed with PX4 dependencies)
- ROS2 Humble
- MicroXRCE-DDS Agent

## Install PX4

```bash
cd ~
git clone --recursive https://github.com/PX4/PX4-Autopilot.git
cd PX4-Autopilot
bash Tools/setup/ubuntu.sh
make px4_sitl gz_x500
```

The first `make` takes ~20 minutes. It builds PX4 SITL and downloads Gazebo models.

## Install MicroXRCE-DDS Agent

```bash
cd ~
git clone https://github.com/eProsima/Micro-XRCE-DDS-Agent.git
cd Micro-XRCE-DDS-Agent
mkdir build && cd build
cmake ..
make -j$(nproc)
sudo make install
sudo ldconfig
```

## Build px4_msgs for ROS2

```bash
mkdir -p ~/drone-vla/ros2_ws/src
cd ~/drone-vla/ros2_ws/src
git clone -b release/1.16 https://github.com/PX4/px4_msgs.git
cd ~/drone-vla/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select px4_msgs
```

## Launch 3-Drone Swarm

Use the provided start script:

```bash
bash ~/drone-vla/scripts/start_px4_swarm.sh
```

Or manually:

### Drone 1 (starts Gazebo)

```bash
cd ~/PX4-Autopilot
PX4_SYS_AUTOSTART=4001 PX4_SIM_MODEL=gz_x500 \
    ./build/px4_sitl_default/bin/px4 -i 1
```

Wait 20 seconds for Gazebo to load.

### Drones 2 and 3

```bash
# Drone 2 (3m offset on Y axis)
PX4_GZ_STANDALONE=1 PX4_SYS_AUTOSTART=4001 \
    PX4_GZ_MODEL_NAME=x500_2 \
    ./build/px4_sitl_default/bin/px4 -i 2

# Drone 3 (6m offset)
PX4_GZ_STANDALONE=1 PX4_SYS_AUTOSTART=4001 \
    PX4_GZ_MODEL_NAME=x500_3 \
    ./build/px4_sitl_default/bin/px4 -i 3
```

**Critical:** Drones 2+ need `PX4_GZ_STANDALONE=1` so they connect to the existing Gazebo instance instead of starting a new one. `PX4_GZ_MODEL_NAME` must be unique per drone.

### MicroXRCE-DDS Agent

```bash
MicroXRCEAgent udp4 -p 8888
```

### Disable preflight checks (SITL)

```bash
python3 ~/drone-vla/scripts/set_px4_params.py
```

This sets `COM_RCL_EXCEPT=4`, `CBRK_SUPPLY_CHK=894281`, `SYS_HAS_MAG=0`, and `SDLOG_MODE=-1` (disables logging to prevent disk fill).

## ROS2 Topics

Each drone publishes/subscribes under its namespace `/px4_N/`:

| Topic | Direction | Purpose |
|-------|-----------|----------|
| `/px4_N/fmu/in/offboard_control_mode` | Subscribe | Enable offboard position control |
| `/px4_N/fmu/in/trajectory_setpoint` | Subscribe | Position/velocity targets |
| `/px4_N/fmu/in/vehicle_command` | Subscribe | Arm, mode change, land commands |
| `/px4_N/fmu/out/vehicle_status_v1` | Publish | Arming state, nav state, preflight status |
| `/px4_N/fmu/out/vehicle_local_position` | Publish | EKF position estimate (NED frame) |

## Known Gotchas

These cost hours to debug — save yourself the pain:

### 1. Topic name: `vehicle_status_v1` not `vehicle_status`

PX4 v1.16 renamed the status topic. The message type is still `px4_msgs/msg/VehicleStatus` but the topic name changed. Subscribing to the old name silently fails — no error, just no data.

### 2. Force-arm required in SITL

`pre_flight_checks_pass` is always `false` in SITL even after disabling check params. Use force-arm by setting `param2=21196.0` in the `VEHICLE_CMD_COMPONENT_ARM_DISARM` command.

### 3. Integer params via pymavlink need byte encoding

PX4 integer params (like `COM_RCL_EXCEPT`) must be sent as INT32 bytes reinterpreted as float:

```python
import struct
def int_as_float(val):
    return struct.unpack('f', struct.pack('I', int(val)))[0]
```

Sending raw `float(val)` with `MAV_PARAM_TYPE_REAL32` stores garbage.

### 4. PX4 SITL writes .ulg logs continuously

3 idle drones can fill 27+ GB in hours. Set `SDLOG_MODE=-1` via the param setter. Also: killing processes is the only way to free disk from open file descriptors on deleted files.

### 5. 8-second gap between drone spawns

Gazebo needs time to instantiate each model. Spawning too fast causes model collisions or PX4 connection failures.

## Run the Swarm Test

```bash
source /opt/ros/humble/setup.bash
source ~/drone-vla/ros2_ws/install/setup.bash
python3 ~/drone-vla/scripts/test_px4_ros2_swarm.py
```

This arms all 3 drones, takes off to 20m, flies a triangle formation (30m spacing), holds for 10s, and lands. Expected runtime: ~70 seconds.

## Always Kill When Done

```bash
pkill -f "px4.*-i [0-9]"
pkill -f "gz sim"
pkill -f MicroXRCEAgent
```

Leaving PX4 running eats disk (flight logs) and CPU (~200% per instance).