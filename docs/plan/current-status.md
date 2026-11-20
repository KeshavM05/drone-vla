---
title: Current System Status
description: "Living snapshot: what works right now, what's wired up, what's scaffolded but not connected"
tags:
  - plan
  - status
  - snapshot
---
# Current System Status

Last updated: 2026-11-20 (Day 3, E2E verified)

## Recent Changes

- **End-to-end command pipeline wired** — NLP → FleetManager → MissionExecutor → SwarmManager
- `start_command_center.py --live` mode connects ROS2 SwarmManager with full execution
- LAND/RTH/TAKEOFF dispatch directly to SwarmManager; complex missions route through PathPlanner
- FleetManager syncs telemetry from PX4 on every tick for allocation decisions
- `altitude_agl_m` validation fixed (`ge=1.0` → `ge=0.0`) for land commands
- Flattened `src/drone_vla/` → `drone_vla/` at project root
- Nuked all ArduPilot/MAVSDK code, project fully self-contained with px4_msgs

## What Works Right Now

### Simulation
- 3-drone PX4 SITL swarm launches with one script
- Drones arm, take off, fly triangle formation, land
- 45-degree camera on drone 1, images bridge to ROS2 at 4-9 Hz
- Collision avoidance enforces altitude layers (D1=15m, D2=20m, D3=25m)

### Command Center
- Web dashboard at `http://localhost:8080`
- Two modes: `--live` (PX4 connected, commands execute) or simulated (UI dev)
- Shows 3 drone cards with live telemetry from PX4
- 2D map with drone positions, headings, velocity vectors
- NLP command input: type a sentence, Claude parses and executes it
- Voice input via browser Web Speech API
- Event log with color-coded sources

### End-to-End Pipeline (verified working)
- Type a command → Claude Haiku 4.5 parses intent → FleetManager allocates drones → PathPlanner computes waypoints → SwarmManager sends to PX4 → drones fly in Gazebo
- Tested: "fly triangle formation" → all 3 drones moved to formation positions
- Tested: "land all drones" → all 3 drones descended and landed
- LAND/RTH/TAKEOFF go directly to SwarmManager; complex missions route through MissionExecutor

### NLP Pipeline
- Claude Haiku 4.5 on AWS Bedrock
- Parses: area search, formation, orbit, patrol, RTH, takeoff, land
- Handles multi-command utterances ("drones 1+2 formation, drone 3 orbit")
- Asks for clarification when commands are ambiguous

## What's Wired (via `--live` mode)

| Component | Has Code | Wired to PX4 | Wired to Command Center |
|-----------|----------|-------------|------------------------|
| `SwarmManager` (ROS2 node) | Yes | Yes (--live) | Yes (telemetry + commands) |
| `FleetManager` (allocation) | Yes | Yes (telemetry sync) | Yes (via MissionExecutor) |
| `MissionExecutor` (plans → waypoints) | Yes | Yes (via SwarmManager) | Yes |
| `PathPlanner` (Voronoi, formations) | Yes | Yes (via MissionExecutor) | Yes |
| `IntentParser` (NLP) | Yes | Yes (parses + executes in live) | Yes |
| GPS waypoint navigation | Yes | Yes (via SwarmManager) | Yes |

## What Doesn't Exist Yet

- Camera feed in command center
- Whisper STT backend
- Geofencing
- Emergency stop
- Battery enforcement
- Object detection
- Multi-mission concurrency
- Physical drone support

## Architecture Diagram (Current State)

```mermaid
flowchart TD
    subgraph Pipeline["End-to-End Pipeline (--live mode)"]
        UI[Command Center UI] <-->|WebSocket 2Hz| Bridge[SwarmBridge]
        Bridge --> NLP[Claude Haiku via Bedrock]
        NLP -->|ParsedIntent| Bridge
        Bridge -->|LAND/RTH/TAKEOFF| Swarm[SwarmManager]
        Bridge -->|complex missions| Exec[MissionExecutor]
        Exec --> Fleet[FleetManager]
        Exec --> PP[PathPlanner]
        PP -->|Waypoints| Exec
        Exec -->|GPS waypoints| Swarm
        Swarm --> CA[Collision Avoidance]
        CA --> PX4Drone[PX4Drone x3]
        PX4Drone --> ROS2[ROS2 / MicroXRCE-DDS]
        ROS2 --> PX4[PX4 SITL]
        Swarm -->|telemetry| Fleet
        GZ[Gazebo Camera] --> ImgBridge[ros_gz_image] --> ROS2
    end

    style Pipeline fill:#1a2744
```

## Launch Commands

```bash
# Start PX4 swarm (terminal 1)
bash ~/drone-vla/scripts/start_px4_swarm.sh

# Start Command Center (terminal 2)
python3 ~/drone-vla/scripts/start_command_center.py

# Test collision avoidance (requires PX4 running)
python3 ~/drone-vla/scripts/test_collision_avoidance.py

# Test camera bridge (requires PX4 with camera running)
python3 ~/drone-vla/scripts/test_camera_bridge.py /world/default/model/x500_mono_cam_45_1/link/camera_link/sensor/imager/image
```
