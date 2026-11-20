---
title: Fleet Manager API
description: Drone registration, allocation, telemetry tracking, and automatic failover
tags:
  - api
  - fleet
  - orchestrator
---
# Fleet Manager API

The `FleetManager` class (`drone_vla/orchestrator/fleet_manager.py`) is the central registry for all drones in the swarm. It tracks state, allocates drones to missions, and handles automatic failover.

## DroneState

Each registered drone has a `DroneState` dataclass:

| Field | Type | Description |
|-------|------|-------------|
| `drone_id` | `int` | 1-based unique identifier |
| `status` | `DroneStatus` | Current state (see enum below) |
| `lat`, `lon`, `alt_m` | `float` | GPS position |
| `heading_deg` | `float` | Current heading |
| `battery_pct` | `float` | Battery percentage (0–100) |
| `current_mission_id` | `str \| None` | Active mission ID |
| `sensor_payload` | `str` | Sensor type (rgb, thermal, etc.) |
| `last_heartbeat` | `float` | Unix timestamp of last telemetry |

### DroneStatus

`idle` \| `armed` \| `in_mission` \| `returning` \| `landed` \| `offline` \| `error`

## Key Methods

### `allocate_drones(command: MissionCommand) -> list[DroneState]`

Allocates drones to a [mission command](./mission-schemas.md). If the command specifies drone IDs, those are used (filtering out unavailable ones). Otherwise, auto-selects by highest battery percentage.

**Auto-allocation counts by mission type:**
- `area_search`: 3 drones
- `perimeter_patrol`: 2 drones
- `formation_flight`: 3 drones
- `point_inspection`: 1 drone
- `relay_station`: 1 per station point

### `handle_failover(failed_drone_id: int) -> DroneState | None`

When a drone fails mid-mission:
1. Sets failed drone status to `ERROR`
2. Clears its mission assignment
3. Finds the next available drone with sufficient battery
4. Assigns the backup to the failed drone's mission
5. Returns the backup drone, or `None` if no backup available

Failover can be disabled via `fleet.failover_enabled: false` in config.

### `check_battery_warnings() -> list[DroneState]`

Returns all drones currently in-mission with battery below `min_battery_pct` (default 20%). The main loop uses this to trigger automatic RTH.

### `get_fleet_state_summary() -> dict`

Returns a JSON-serializable snapshot of the fleet, passed to the LLM as context so it can make allocation-aware parsing decisions.