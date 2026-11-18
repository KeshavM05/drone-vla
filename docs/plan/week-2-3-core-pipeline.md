---
title: "Weeks 2-3: Core Pipeline"
description: Detailed breakdown of intent parser tuning and SITL integration for Days 8-17
tags:
  - plan
  - week-2
  - week-3
  - pipeline
---
# Weeks 2-3: Core Pipeline (Nov 25 - Dec 4)

Parent: [Master Plan](./master-plan.md)

## Goal

Type a natural language command and watch drones execute it in simulation.

## Day 8 (Mon 11/25): Intent Parser Standalone Testing

### Test Suite (20 commands)

Create `scripts/test_intent_parser.py` with these commands:

| # | Command | Expected type | Assignment |
|---|---------|--------------|------------|
| 1 | "Take off to 20 meters" | takeoff | all |
| 2 | "All drones land" | land | all |
| 3 | "Drone 1, take off to 30 meters" | takeoff | [1] |
| 4 | "Form a triangle formation at 25 meters" | formation_flight | auto |
| 5 | "Drones 1 and 2, form a line" | formation_flight | [1, 2] |
| 6 | "Search the area north of here" | area_search | auto |
| 7 | "Patrol the perimeter clockwise" | perimeter_patrol | auto |
| 8 | "Orbit that building at 40 meters" | point_inspection | auto |
| 9 | "Drone 3, relay at 50 meters" | relay_station | [3] |
| 10 | "Everyone return to home" | return_to_home | all |
| 11 | "Take off, form a V, sweep north" | 3 commands | auto |
| 12 | "Swarm Alpha, search the treeline" | area_search | group: Alpha |
| 13 | "Abort all missions" | return_to_home | all |
| 14 | "Increase altitude to 40 meters" | altitude change | all |
| 15 | "Switch to thermal camera" | sensor change | all |
| 16 | "Drone 2, go to where Drone 1 is" | relative nav | [2] |
| 17 | "Hold position" | loiter | all |
| 18 | "Speed up to 10 m/s" | speed change | all |
| 19 | "Diamond formation, orbit the lake" | formation + orbit | auto |
| 20 | "What is Drone 3 doing?" | status query | [3] |

Target: 18/20 produce valid JSON. Commands 14-18 are stretch.

## Day 9 (Tue 11/26): Prompt Engineering

Iterate on the system prompt:
- Multi-command parsing (commands 11, 19)
- Ambiguity handling ("that building" without coordinates)
- Status queries vs. action commands
- Edge cases: empty input, nonsense, non-English

## Day 10 (Wed 11/27): Fleet Manager + SITL Integration

Connect `FleetManager` to live SITL telemetry:
- Register all 3 drones from `MAVLinkBridge`
- Verify `get_fleet_state_summary()` returns real battery/position
- Pass state to LLM for context-aware parsing

## Day 11 (Thu 11/28): End-to-End Text Mode

The critical integration day. Run `drone-vla --text` and type commands:
- "Take off all drones to 20 meters" (watch Gazebo)
- "Form a triangle at 25 meters" (watch repositioning)
- "Return to home" (watch landing)

If this works, you have the core product.

## Day 12 (Fri 11/29): All Mission Types

Test each [mission type](../api/mission-schemas.md) in sequence:
- takeoff, land
- formation_flight (triangle, line, circle)
- area_search (Voronoi decomposition)
- perimeter_patrol
- point_inspection (orbit)
- return_to_home

## Day 13 (Sat 11/30): Checkpoint 2

Record: type a formation + orbit command, show drones executing in Gazebo.

## Day 14 (Mon 12/1): Failover

Kill one SITL instance mid-mission. Verify:
- Fleet manager detects heartbeat loss within 5s
- Backup drone absorbs failed sector
- Zero operator intervention

## Day 15 (Tue 12/2): Path Planner Tuning

Visual quality check in Gazebo:
- Voronoi cells partition evenly
- Formation spacing looks intentional
- Orbits are smooth circles

## Day 16 (Wed 12/3): Battery Auto-RTH

Simulate drain, verify:
- Warning at 30%
- Auto-RTH at 20%
- Safe return and land

## Day 17 (Thu 12/4): Buffer

10 consecutive commands without failure. Fix reliability issues.