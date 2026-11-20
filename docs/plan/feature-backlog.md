---
title: Feature Backlog
description: "Complete feature list: what's built, what's in progress, and what's planned — from operator requests and technical requirements"
tags:
  - plan
  - backlog
  - features
  - requirements
---
# Feature Backlog

Everything that needs to exist in this system, organized by status. Items from operator (Keshav) requests are marked with **(K)**. Items from technical requirements are marked with **(T)**.

Last updated: 2026-11-20

## Built

| Feature | Source | Details | Commit |
|---------|--------|---------|--------|
| PX4 SITL 3-drone swarm | (T) | PX4 v1.16 + Gazebo Harmonic + MicroXRCE-DDS | Day 1 |
| ROS2 arm/takeoff/formation | (T) | Offboard mode, force-arm, triangle formation test | Day 1 |
| 45-degree camera model | (K) | No gimbal on real drone, fixed 45-deg forward-down mount | `187c1f9` |
| Camera → ROS2 bridge | (K) | `ros_gz_image` with gzharmonic packages, 1280x960 RGB @ 4-9 Hz | `187c1f9` |
| Collision avoidance | (K) | 3-layer: altitude deconfliction, separation monitoring, reactive avoidance | `b7997b6` |
| PX4 ROS2 flight layer | (T) | `px4_drone.py` + `swarm_node.py` replacing MAVSDK/ArduPilot | `b7997b6` |
| Command Center dashboard | (K) | Web UI: fleet cards, map, alerts, logs, command input | `9567dea` |
| NLP intent parser | (T) | Claude Haiku 4.5 via Bedrock, NL → MissionCommand JSON | `b19001b` |
| GPS/NED waypoint conversion | (T) | `geo.py` utility, `assign_gps_waypoints()` on SwarmManager | `b0abef4` |
| Disk management | (T) | PX4 log cleanup, SDLOG disable, open FD handling | Day 1 |
| OpenKnowledge docs | (K) | Full doc suite: architecture, guides, API, plan | Ongoing |
| Project restructure | (T)+(K) | Flatten src/, nuke ArduPilot, self-contained px4_msgs | `2d1b4f2` |
| Swarm start script (camera) | (T) | Defaults to `x500_mono_cam_45`, configurable model | `b7997b6` |
| Path planner | (T) | Voronoi decomposition, lawnmower sweep, formation, orbit, perimeter | Scaffold |
| Fleet manager | (T) | Drone allocation, failover, battery warnings | Scaffold |
| Mission executor | (T) | Command → waypoints per drone, RTH, takeoff | Scaffold |
| Pydantic mission schemas | (T) | 8 mission types, formations, sensors, contingencies | Scaffold |

## In Progress

| Feature | Source | Blocker / Next Step |
|---------|--------|--------------------|
| Live PX4 → Command Center | (T) | Connect SwarmManager to web backend via bridge |
| Command → drone execution | (T) | Wire NLP output through fleet manager → executor → swarm node |
| Voice input (browser) | (K) | Web Speech API wired in UI, needs Whisper backend for reliability |

## Planned — Near Term (Phase 1-2)

| Feature | Source | Priority | Notes |
|---------|--------|----------|-------|
| End-to-end command execution | (T) | **P0** | Type command → drones move in Gazebo |
| Camera feed in command center | (K) | **P0** | Live MJPEG/WebSocket stream from drone cameras |
| Telemetry terminal display | (T) | P1 | Live-updating fleet state in terminal (debugging) |
| Whisper STT backend | (K) | P1 | faster-whisper for reliable voice, not browser-only |
| Operator HUD polish | (K) | P1 | Better map (Leaflet?), camera feed panel, mission timeline |
| Geofencing | (K)(T) | P1 | Soft + hard geofence — see [Guardrails](../architecture/guardrails.md) |
| Battery auto-RTH | (T) | P1 | Enforce min battery → auto return |
| Command confirmation | (K)(T) | P2 | Dangerous commands require operator confirm |
| Emergency stop button | (K)(T) | P2 | Red button in UI, voice keyword bypass |

## Planned — Mid Term (Phase 3)

| Feature | Source | Priority | Notes |
|---------|--------|----------|-------|
| Multi-mission orchestration | (T) | P1 | 2+ concurrent missions with deconfliction |
| Dynamic replanning | (K) | P1 | Mid-mission voice override: "redirect drone 2 north" |
| Context memory | (T) | P2 | LLM remembers fleet state across commands |
| YOLOv8 object detection | (T) | P2 | Detect people/objects in camera feed, geo-tagged alerts |
| Detection → notification | (K) | P2 | "Found" events in command center with GPS + confidence |
| Detection → auto-orbit | (T) | P3 | Drone auto-orbits detected target |
| Stress testing (30 min) | (T) | P2 | Unbroken session with full feature set |

## Planned — Physical Drones (Phase 4)

| Feature | Source | Priority | Notes |
|---------|--------|----------|-------|
| Hardware procurement | (K) | P0 | SpeedyBee F405 V4 — see hardware recs |
| Pre-flight checklist | (T) | **P0** | Must exist before first real flight |
| Progressive test protocol | (T) | **P0** | Single drone → 2 drone → 3 drone — see [Guardrails](../architecture/guardrails.md) |
| RC kill switch setup | (T) | **P0** | Hardware emergency stop independent of software |
| Real CA parameters | (T) | P1 | Wider margins than sim (8m critical vs 5m) |
| PX4 log retention | (T) | P1 | Never disable logging on real hardware |
| Post-flight review tool | (T) | P2 | Automated log analysis after each flight |
| Outdoor GPS testing | (T) | P1 | Verify GPS accuracy in target flying area |
| Wind limit enforcement | (T) | P2 | Weather API check before arming |

## Planned — Demo (Phase 5)

| Feature | Source | Priority | Notes |
|---------|--------|----------|-------|
| System integration (sim↔real) | (T) | P1 | Same code runs both, config switch |
| Demo choreography | (K) | P1 | Scripted sequence for video |
| Video recording pipeline | (K) | P2 | All camera feeds + screen + voice recorded |
| Pitch deck | (K) | P2 | Problem, solution, demo, market, team, ask |

## Operator Requests Log

Raw requests from Keshav, as given, with dates:

| Date | Request | Status |
|------|---------|--------|
| 2026-11-19 | 45-degree camera (no gimbal on real drone) | Done |
| 2026-11-19 | Document everything in OpenKnowledge, commit+push always | Policy established |
| 2026-11-20 | Collision avoidance — drones at different altitudes, aware of each other | Done |
| 2026-11-20 | Command center: see all drones, feeds, logs, objectives found, command input (voice+text) | Done (v1) |
| 2026-11-20 | Guardrails for real drones (work on before testing) | Documented |
| 2026-11-20 | Organize docs: what's built, what's planned, what I asked for | This doc |
| 2026-11-20 | Nuke ArduPilot, flatten folder structure, everything self-contained | Done |
