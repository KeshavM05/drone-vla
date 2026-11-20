---
title: Mission Schemas
description: Pydantic models defining the structured contract between the LLM intent parser and the swarm orchestrator
tags:
  - api
  - schemas
  - pydantic
---
# Mission Schemas

All mission data flows through Pydantic v2 models defined in `drone_vla/nlp/schemas.py`. These models are the structured contract between the [intent parser](./fleet-manager.md) and the [swarm orchestrator](../architecture/system-overview.md).

## Core Models

### MissionCommand

The top-level command produced by the intent parser for a single mission.

| Field | Type | Description |
|-------|------|-------------|
| `mission_type` | `MissionType` | One of 8 mission types (see below) |
| `assignment` | `DroneAssignment` | Which drones to use (specific IDs or auto-assign) |
| `altitude_agl_m` | `float` (1–500) | Altitude in meters above ground |
| `speed_ms` | `float` (0.5–30) | Speed in meters/second |
| `formation_type` | `FormationType` | Formation shape (for formation_flight) |
| `sensor_mode` | `SensorMode` | Camera/sensor configuration |
| `target_classes` | `list[str]` | Object types to detect (e.g., `["person", "heat_signature"]`) |
| `contingency` | `ContingencyAction` | What to do on failure (default: `auto_rth`) |
| `raw_intent` | `str` | Original spoken command for audit trail |

### ParsedIntent

Wrapper returned by the intent parser containing one or more commands from a single utterance.

| Field | Type | Description |
|-------|------|-------------|
| `commands` | `list[MissionCommand]` | Extracted commands |
| `confidence` | `float` (0–1) | Parser confidence score |
| `clarification_needed` | `str \| None` | Question for the operator if ambiguous |

## Enums

### MissionType

| Value | Description |
|-------|-------------|
| `area_search` | Sweep a polygon area with coordinated search patterns |
| `perimeter_patrol` | Continuous patrol around a perimeter |
| `formation_flight` | Fly in a specified formation shape |
| `point_inspection` | Inspect a point of interest from multiple angles |
| `relay_station` | Position drones as communication relay nodes |
| `return_to_home` | Command drones to return to launch positions |
| `takeoff` | Arm and take off to specified altitude |
| `land` | Land at current position |

### FormationType

`line` \| `triangle` \| `diamond` \| `circle` \| `v_shape` \| `grid`

### SensorMode

`rgb` \| `thermal` \| `thermal_rgb_fused` \| `multispectral`

### ContingencyAction

`auto_rth` \| `loiter_in_place` \| `land_immediately` \| `continue_mission`

## JSON Example

A typical parsed output from the operator saying "Swarm Alpha, search the northern field for lost hikers at 40 meters":

```json
{
  "commands": [{
    "mission_type": "area_search",
    "assignment": {"drone_ids": [], "group_name": "Alpha"},
    "search_polygon": [
      {"lat": 47.398, "lon": 8.545},
      {"lat": 47.399, "lon": 8.545},
      {"lat": 47.399, "lon": 8.547},
      {"lat": 47.398, "lon": 8.547}
    ],
    "altitude_agl_m": 40.0,
    "sensor_mode": "thermal_rgb_fused",
    "target_classes": ["person", "heat_signature"],
    "contingency": "auto_rth",
    "raw_intent": "Swarm Alpha, search the northern field..."
  }],
  "confidence": 0.94,
  "clarification_needed": null
}
```