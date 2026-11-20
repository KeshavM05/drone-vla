---
title: Safety Guardrails
description: All safety systems, limits, and checks required before real drone testing
tags:
  - architecture
  - safety
  - guardrails
  - critical
---
# Safety Guardrails

This document defines every safety system that must exist before flying real hardware. Simulation can tolerate shortcuts. Real drones cannot.

## SIMULATED vs REAL — Hard Rules

| Behavior | SITL (Simulation) | Real Hardware |
|----------|-------------------|---------------|
| Force-arm (`param2=21196`) | Allowed | **NEVER** — bypasses all preflight |
| `SDLOG_MODE=-1` | Allowed (saves disk) | **NEVER** — logs are crash evidence |
| Collision avoidance | Should be on | **MANDATORY** — no override |
| Geofence | Optional | **MANDATORY** |
| Kill switch | Not needed | **MANDATORY** — hardware RC kill |
| Pre-flight checklist | Skippable | **MANDATORY** — every flight |
| Battery auto-RTH | Configurable | **MANDATORY** at 25% |
| GPS quality check | Skippable | **MANDATORY** — min 8 satellites, HDOP < 2.0 |

## Guardrail Categories

### 1. Geofencing

**Status:** Not built yet

Before any real flight, the system must enforce a geographic boundary:

- **Soft geofence**: Operator defines a polygon. Drones approaching the boundary receive a velocity correction pushing them inward. Logged as a warning.
- **Hard geofence**: PX4 built-in geofence (`GF_ACTION=2` = loiter at boundary). Absolute backstop if software geofence fails.
- **Vertical limits**: Max altitude (configurable, default 40m AGL). Min altitude (5m AGL — below this only during landing).
- **Home radius**: Max distance from home point (configurable, default 200m).

**Implementation plan:**
- Add `GeofenceConfig` to `config.py` with polygon, max_alt, max_radius
- Add geofence check in SwarmManager tick loop (same place as CA checks)
- Set PX4 geofence params via `set_px4_params.py` as hardware backup

### 2. Battery Management

**Status:** Schema exists (`FleetConfig.min_battery_pct`), not enforced in flight layer

- **Warning level (30%)**: Alert operator, log event, mark in command center
- **Critical level (25%)**: Auto-RTH — drone returns home regardless of mission
- **Emergency level (15%)**: Auto-land — drone lands immediately at current position
- Battery data must flow from PX4 telemetry → FleetManager → Command Center

### 3. Communication Loss

**Status:** PX4 params set (`COM_RCL_EXCEPT=4`, `NAV_DLL_ACT=0`), needs software-side handling

- **Heartbeat timeout (5s)**: If SwarmManager loses telemetry from a drone for 5s, mark it `OFFLINE`
- **GCS link loss (10s)**: If the command center WebSocket disconnects for 10s, all drones hold position
- **Full comms loss (30s)**: All drones auto-RTH
- **On real hardware**: PX4 RC failsafe handles this at firmware level. The software layer is an additional safety net.

### 4. Emergency Stop / Kill Switch

**Status:** Not built yet

- **Software kill**: Command center red button sends `VEHICLE_CMD_COMPONENT_ARM_DISARM` (disarm) to all drones. Motors cut immediately. Drones fall.
- **Hardware kill**: RC transmitter kill switch (channel 5 or 6). Independent of software — works even if laptop crashes.
- **Voice kill**: Recognizing "STOP" or "EMERGENCY" at any time should trigger software kill with zero NLP processing delay.

**Implementation plan:**
- Add emergency stop button to command center UI
- Add keyword detection bypass in voice pipeline (before NLP)
- Document RC kill switch channel assignment for real hardware

### 5. Command Validation

**Status:** Partially built (NLP outputs structured commands, no validation layer yet)

Before any parsed command executes:

- **Altitude check**: Reject commands with altitude > max_altitude or < min_altitude
- **Distance check**: Reject waypoints outside geofence
- **Speed check**: Reject speeds > max_speed (configurable, default 10 m/s)
- **Drone count check**: Don't send more drones than available
- **Conflict check**: Don't assign a drone that's already mid-mission without explicit override
- **Confirmation for dangerous commands**: "land immediately" or "disarm all" require operator confirmation in command center

### 6. Collision Avoidance (Existing)

**Status:** Built — see [Collision Avoidance](./collision-avoidance.md)

On real hardware, additional requirements:
- CA must be **non-disableable** — no config flag to turn it off
- Altitude layer spacing increased to 8m (vs 5m in sim) for GPS vertical error margin
- Warning threshold increased to 15m (vs 10m in sim)
- Critical threshold increased to 8m (vs 5m in sim)
- If reactive avoidance fires, **log and alert** — operator must acknowledge before next mission

### 7. Pre-Flight Checklist

**Status:** Not built yet

The system must block arming until all checks pass:

- [ ] GPS lock: min 8 satellites, HDOP < 2.0
- [ ] Battery: > 80% for mission start
- [ ] Compass calibration: within tolerance
- [ ] Accelerometer calibration: within tolerance
- [ ] RC link: connected with > -80 dBm RSSI
- [ ] Geofence: loaded and active
- [ ] Kill switch: tested (arm → kill → verify disarm)
- [ ] Weather: wind < 20 km/h, no precipitation
- [ ] Airspace: clear of manned aircraft, legal to fly
- [ ] Spotter: designated visual observer in position
- [ ] Landing zone: clear of people and obstacles

### 8. Operational Limits

| Parameter | Simulation | Real (Initial) | Real (Proven) |
|-----------|-----------|----------------|---------------|
| Max altitude | 100m | 30m | 50m |
| Max speed | 20 m/s | 5 m/s | 10 m/s |
| Max range | Unlimited | 100m | 200m |
| Max drones | 5 | 1 (then 3) | 3 |
| Min battery for mission | 20% | 50% | 30% |
| CA altitude layer | 5m | 8m | 8m |
| CA critical distance | 5m | 8m | 8m |

**Real (Initial)** = first 10 flights. Conservative limits until confidence builds.
**Real (Proven)** = after 10 successful flights with no incidents.

### 9. Logging and Black Box

- **PX4 .ulg logs**: Always enabled on real hardware (never `SDLOG_MODE=-1`)
- **Command center logs**: Every command, every NLP parse, every CA alert written to disk with timestamps
- **Video recording**: All camera feeds recorded during mission (not just viewed)
- **Post-flight review**: After every real flight, review logs for any anomaly before next flight

### 10. Progressive Testing Protocol

Do NOT go from simulation to 3-drone autonomous swarm. Step by step:

1. **Single drone, manual RC**: Hover test, GPS hold, basic maneuvers. Prove hardware works.
2. **Single drone, software takeoff+land**: One `arm → takeoff → hold → land` command from laptop. Prove comms work.
3. **Single drone, waypoint mission**: Send to 3 waypoints and RTH. Prove navigation works.
4. **Single drone, voice command**: Full NLP pipeline to one physical drone. Prove end-to-end works.
5. **Two drones, manual spacing**: Fly 2 drones with manual altitude separation. Prove multi-drone is survivable.
6. **Two drones, CA active**: Let collision avoidance manage altitude. Prove CA works in real air.
7. **Three drones, full system**: The demo configuration. Only attempt after steps 1-6 pass.

Each step requires 3 successful repetitions before advancing.
