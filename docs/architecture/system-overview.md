---
title: System Overview
description: 4-tier architecture from natural language input to autonomous drone flight
tags:
  - architecture
  - overview
---
# System Overview

Drone VLA is a 4-tier pipeline that translates natural language operator commands into coordinated multi-drone autonomous missions.

## Architecture Diagram

```mermaid
flowchart TD
    A["Operator Voice / Text Input"] --> B

    subgraph TIER1["Tier 1: Cognitive Tactical Parser"]
        B["Speech-to-Text\nfaster-whisper"] --> C["Intent Extraction\nClaude via AWS Bedrock"]
        C --> D["Mission Schema\nPydantic MissionCommand"]
    end

    subgraph TIER2["Tier 2: Swarm Orchestrator"]
        D --> E["Fleet Manager\nAllocation + Health"]
        E --> F["Path Planner\nVoronoi + Lawnmower"]
        F --> G["Mission Executor\nWaypoint Dispatch"]
    end

    subgraph TIER3["Tier 3: Flight Bridge"]
        G --> H["ROS2 px4_msgs\nOffboard Control"]
        H --> I["PX4 SITL v1.16\nper-drone instance"]
    end

    subgraph TIER4["Tier 4: Edge Sensing"]
        I --> J["Gazebo Harmonic\nCamera + Sensors"]
        J --> K["MicroXRCE-DDS\nROS2 Topics"]
    end

    K -.->|"Telemetry + Detections"| E
```

## Tier Breakdown

### Tier 1: Cognitive Tactical Parser

**Purpose:** Convert spoken or typed natural language into deterministic mission specifications.

| Component | Module | Role |
|-----------|--------|------|
| Speech-to-Text | `stt/whisper_engine.py` | Real-time mic transcription via faster-whisper with VAD |
| Intent Parser | `nlp/intent_parser.py` | Claude on AWS Bedrock extracts structured [MissionCommand](../api/mission-schemas.md) JSON |
| Schemas | `nlp/schemas.py` | Pydantic v2 models defining all mission types and parameters |

**Key design decision:** Claude via AWS Bedrock was chosen over local models for superior structured output reliability. Temperature is set to 0.0 for deterministic parsing.

### Tier 2: Swarm Orchestrator

**Purpose:** Allocate drones to missions, plan collision-free paths, execute with failover.

| Component | Module | Role |
|-----------|--------|------|
| Fleet Manager | `orchestrator/fleet_manager.py` | Tracks drone state, allocates by battery/availability, handles [failover](./data-flow.md) |
| Path Planner | `orchestrator/path_planner.py` | Voronoi decomposition for area search, formations, orbits, patrols |
| Mission Executor | `orchestrator/mission_executor.py` | Dispatches waypoint plans to individual drones |

**Key design decision:** Voronoi spatial decomposition ensures each drone covers a unique cell with minimal overlap. Failover is automatic — if a drone drops, the orchestrator reassigns its sector to the next available drone.

### Tier 3: Flight Bridge

**Purpose:** Abstract hardware communication. All drone control flows through ROS2 px4_msgs to PX4 via MicroXRCE-DDS.

| Component | Module | Role |
|-----------|--------|------|
| Drone Controller | `flight/drone_controller.py` | Per-drone offboard control: arm, takeoff, trajectory setpoints, land |
| ROS2 Bridge | `flight/ros2_bridge.py` | Publishes `OffboardControlMode`, `TrajectorySetpoint`, `VehicleCommand` per drone |

**Key design decision:** Switched from ArduPilot to PX4 v1.16 on Day 1 — ArduPilot multi-instance SITL was unstable. PX4 provides native ROS2 integration via MicroXRCE-DDS without needing ros_gz_bridge for command/control. See [PX4 SITL Setup](../guides/px4-sitl-setup.md) for details.

### Tier 4: Edge Sensing (Simulation)

**Purpose:** Gazebo Harmonic provides simulated cameras and sensors; MicroXRCE-DDS exposes PX4 telemetry as ROS2 topics.

| Component | Config | Role |
|-----------|--------|------|
| PX4 SITL | `scripts/start_px4_swarm.sh` | 3 simulated x500 quadcopter instances |
| Gazebo Harmonic | Started by PX4 drone 1 | Physics + rendering engine |
| MicroXRCE-DDS Agent | UDP port 8888 | Bridges PX4 uORB topics to ROS2 |

## ROS2 Integration

The standalone pipeline (`main.py`) works without ROS2. When ROS2 is available, three nodes wrap the pipeline:

1. **STT Node** (`ros2_bridge/stt_node.py`) — publishes to `operator/speech_text`
2. **Intent Node** (`ros2_bridge/intent_node.py`) — subscribes to speech, publishes to `operator/mission_command`
3. **Orchestrator Node** (`ros2_bridge/orchestrator_node.py`) — subscribes to commands, drives the fleet

This decoupled design means any component can be replaced independently (e.g., swap Claude for a local LLM by replacing only the intent node).