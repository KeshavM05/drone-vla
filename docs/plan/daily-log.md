---
title: Daily Log
description: Running journal of daily progress, blockers, and decisions throughout the 8-week build
tags:
  - log
  - accountability
  - journal
---
# Daily Log

Write here at the start and end of every work session. This is your accountability trail and the raw material for the journey retrospective.

## Format

For each session, add an entry at the top (newest first):

```
## DATE - Day N

**Plan:** What I intend to do this session
**Actual:** What I actually did
**Blocked by:** What stopped me or slowed me down
**Decision:** Any decision I made and why
**Next:** What I will do next session
**Hours:** X.Xh
```

---

## Nov 19, 2026 - Day 1 (Evening Session)

**Plan:** Fix arming failures in ROS2 swarm test, get 3-drone formation flying
**Actual:** Discovered PX4 v1.16 renamed `vehicle_status` topic to `vehicle_status_v1` — our ROS2 subscription was silently failing, so arming state was never detected. Fixed topic name, added force-arm (param2=21196) to bypass SITL preflight checks. All 3 drones successfully armed, took off to 20m, flew triangle formation (30m spacing), held 10s, and landed cleanly. Also discovered PX4 SITL writes `.ulg` flight logs continuously — 3 idle instances consumed 27+ GB over 7.5 hours and filled the disk. Fixed by adding `SDLOG_MODE=-1` to param setter and log cleanup to start script.
**Blocked by:** Disk space — PX4 flight logs + open file descriptors from running processes. Had to kill all PX4/Gazebo processes to free space held by deleted-but-open files. Also: pymavlink INT32 params need byte-level encoding (`struct.pack('I', val)` reinterpreted as float), not direct float values.
**Decision:** Switched from ArduPilot to PX4 v1.16 for multi-drone SITL — ArduPilot multi-instance was too fragile. PX4 + MicroXRCE-DDS provides reliable native ROS2 integration without needing ros_gz_bridge for command/control.
**Next:** Set up OpenKnowledge properly. Update all stale docs. Then: camera topics via ros_gz_bridge, NLP command layer.
**Hours:** 5h

## Nov 19, 2026 - Day 1 (Morning Session)

**Plan:** Install ArduPilot SITL, get single instance booting natively
**Actual:** Cloned ArduPilot, ran install-prereqs-ubuntu.sh, built ArduCopter SITL via waf, launched sim_vehicle.py, connected MAVProxy and confirmed heartbeats + EKF + GPS lock. Installed MAVSDK and MAVProxy pip packages. Set up fnm + Node 24 for OpenKnowledge. Attempted multi-drone ArduPilot SITL — too fragile, instances crash and interfere. Evaluated PX4 instead. Built PX4 v1.16 from source, launched 3-drone Gazebo swarm with x500 models. Built px4_msgs ROS2 package and connected via MicroXRCE-DDS Agent.
**Blocked by:** SSH key wasn't registered with GitHub (fixed). ArduPilot multi-instance SITL instability. PX4 Gazebo model spawning needed specific env vars (`PX4_GZ_STANDALONE=1`, `PX4_GZ_MODEL_NAME`).
**Decision:** Native SITL over Docker — simpler for dev. Switched from ArduPilot to PX4 — more stable multi-drone sim with native ROS2 via MicroXRCE-DDS.
**Next:** Fix ROS2 arming issue (status topic mismatch discovered).
**Hours:** 2h