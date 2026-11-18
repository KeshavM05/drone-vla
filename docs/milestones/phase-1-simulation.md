---
title: "Phase 1: Simulation MVP"
description: 14-21 day plan with hard accountability checkpoints for the simulation-first MVP
tags:
  - milestones
  - accountability
  - phase-1
---
# Phase 1: Simulation MVP

The goal: **type or speak a natural language command, and watch 3+ drones execute it in simulation**.

## Timeline

| Week | Days | Milestone | Deliverable |
|------|------|-----------|-------------|
| **W1** | 1–3 | Sim environment up | ArduPilot SITL + Gazebo running, 3 drones spawn, MAVSDK connects |
| | 2–4 | NLP pipeline working | Type a command → Claude Bedrock → structured JSON (tested standalone) |
| | 5–7 | First integration | Type a command → drones move in sim. End-to-end text mode works |
| **W2** | 8–9 | Voice-to-flight | Whisper mic input → Claude → drones execute. Full voice pipeline |
| | 10–12 | ROS2 + Gazebo cameras | ros_gz_bridge streaming camera feeds, ROS2 nodes running |
| | 13–14 | Multi-mission demo | Formations, area search, failover all working in sim |
| **W3** | 15–19 | Physical drones | 2–3 real ArduPilot quads, Wi-Fi, outdoor test |
| | 20–21 | Demo video | The 45-second pitch video |

## Hard Checkpoints (for accountability partner)

Binary pass/fail tests — share the screen recording or it didn't happen.

| Target Date | Checkpoint | Pass Condition |
|-------------|-----------|----------------|
| **Nov 21, 2026** | 3 drones fly in Gazebo | Screen recording showing 3 drones taking off via Python script |
| **Nov 24, 2026** | Typed command → flight | Recording: type a natural language command, drones move |
| **Nov 28, 2026** | Voice command → flight | Video with audio: speak a command, drones respond |
| **Dec 2, 2026** | Multi-mission sim demo | Uncut video: formation + area search + failover in one session |
| **Dec 7, 2026** | Physical drone demo | The 45-second pitch video with real drones |

## Risk Areas

**Biggest time sinks (budget extra time here):**

1. **ArduPilot SITL + Gazebo environment setup** (especially on Windows/WSL2) — budget a full day for Docker or native install issues
2. **LLM prompt tuning** — getting Claude to reliably produce valid [MissionCommand](../api/mission-schemas.md) JSON takes 1–2 days of iteration
3. **MAVSDK multi-instance timing** — connecting to multiple SITL instances concurrently has subtle race conditions

## What's Already Done

The full code scaffold is complete:
- All [Pydantic schemas](../api/mission-schemas.md) defined and tested
- [Fleet manager](../api/fleet-manager.md) with allocation + failover logic, tested
- Path planner (Voronoi, lawnmower, formations, orbits, patrols), tested
- Intent parser with Claude Bedrock integration
- MAVSDK flight bridge for ArduPilot
- ROS2 node wrappers
- [Docker compose](../guides/ardupilot-sitl-setup.md) for 3x SITL + Gazebo

This represents ~30–40% of the total work. The remaining effort is integration, testing against live SITL, and tuning.