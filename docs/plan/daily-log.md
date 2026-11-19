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

## Nov 19, 2026 - Day 1

**Plan:** Install ArduPilot SITL, get single instance booting natively
**Actual:** Cloned ArduPilot, ran install-prereqs-ubuntu.sh, built ArduCopter SITL via waf, launched sim_vehicle.py, connected MAVProxy and confirmed heartbeats + EKF + GPS lock. Installed MAVSDK and MAVProxy pip packages. Set up fnm + Node 24 for OpenKnowledge.
**Blocked by:** SSH key wasn't registered with GitHub (fixed). sudo password needed for prereqs installer (ran manually).
**Decision:** Native SITL over Docker — simpler for dev, matches prod closer. ArduPilot over PX4 per prior decision (ros_gz_bridge support).
**Next:** Set up Gazebo visualization with ardupilot_gazebo plugin. Then MAVSDK connect test script.
**Hours:** 1.5h