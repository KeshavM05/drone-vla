---
title: Drone VLA Documentation
description: Hub for all project documentation — architecture, guides, API reference, and milestones
tags:
  - index
  - overview
---
# Drone VLA — Natural Language Drone Swarm C2

Documentation hub for the Drone VLA project: a system that lets a single operator command a swarm of autonomous drones using natural language voice commands.

## Documentation Map

### [Architecture](./architecture/system-overview.md)
System design, tier breakdown, and design decisions.

- [System Overview](./architecture/system-overview.md) — 4-tier pipeline from voice to flight
- [Data Flow](./architecture/data-flow.md) — How a spoken command becomes coordinated drone movement

### [Guides](./guides/getting-started.md)
Setup and development guides.

- [Getting Started](./guides/getting-started.md) — Environment setup, first simulation run
- [ArduPilot SITL Setup](./guides/ardupilot-sitl-setup.md) — Docker or native SITL configuration

### [API Reference](./api/mission-schemas.md)
Module-level documentation and data contracts.

- [Mission Schemas](./api/mission-schemas.md) — Pydantic models for all mission types
- [Fleet Manager API](./api/fleet-manager.md) — Drone allocation, failover, telemetry

### [Project Plan](./plan/master-plan.md)
8-week master plan from scaffold to physical demo.

- [Master Plan](./plan/master-plan.md) — Full 8-week timeline with Gantt chart
- [Hardware Recommendations](./plan/hardware-recommendations.md) — 3-tier drone hardware options
- [Week 1: Foundation](./plan/week-1-foundation.md) — SITL + Gazebo environment setup
- [Weeks 2-3: Core Pipeline](./plan/week-2-3-core-pipeline.md) — NLP-to-flight integration
- [Daily Log](./plan/daily-log.md) — Accountability journal

### [Milestones](./milestones/phase-1-simulation.md)
Project timeline and accountability checkpoints.

- [Phase 1: Simulation](./milestones/phase-1-simulation.md) — 14-day MVP plan with hard checkpoints