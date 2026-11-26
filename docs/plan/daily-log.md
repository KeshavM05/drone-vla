---
title: Daily Log
description: Running journal of daily progress, blockers, and decisions throughout the 8-week build
tags:
  - log
  - accountability
  - journal
---
# Daily Log

## Nov 26, 2026 - Day 6

**Plan:** Build YOLO detection pipeline, plan physical demo scenario
**Actual:** Built `drone_vla/cv/detector.py` — DetectionManager with two backends: YOLOv8n (COCO objects) and HSV color filtering (orange/red/yellow/blue SAR markers). Added raw BGR frame storage to CameraManager. Camera stream auto-serves annotated frames with bounding boxes. Detection alerts broadcast to Command Center via WebSocket. Added DetectionConfig to config system. API endpoint `GET /api/detections/{drone_id}`. Tested both backends — YOLO loads and runs, color detection correctly identifies orange markers. Discussed physical demo: 2 drones, no pre-programmed GPS, dynamic discovery. Orange marker = detect + descend + Claude Vision. Blue marker = precision landing with PID visual servoing (hover as fallback).
**Blocked by:** No GPU on dev machine — YOLO runs CPU-only (~5-10 FPS). Need live test with Gazebo camera feed.
**Decision:** Two detection backends (YOLO for real objects, color for SAR markers). Precision landing is stretch goal — hover-and-hold is safe fallback. Camera angle (both 45° vs one 45° + one down) TBD after flight testing.
**Next:** Test detection pipeline with live Gazebo camera. Claude Vision integration for scene analysis. Visual servoing for precision landing. AWS GPU setup.
**Hours:** 2h

---

## Nov 25, 2026 - Day 5

**Plan:** Test SAR village world, fix E2E pipeline issues, add CV pipeline
**Actual:** Created SAR village Gazebo world (buildings, vehicles, containers, trees, SAR markers, landing pad — all SDF primitives). Fixed PX4_GZ_WORLD not being passed to standalone instances (drones 2/3 were connecting to world "default" instead of "sar_village"). Fixed per-drone land command (was landing all 3 when asked to land 1). Added NLP conversation history (10-msg window) so follow-ups like "within 100m radius" carry context. Updated NLP system prompt with SAR village GPS coords so it generates real waypoints. Throttled collision avoidance logging (was flooding WebSocket at 30 msg/s, freezing browser). Rewrote path planner: replaced Voronoi + arc sweeps with clean boustrophedon lawnmower pattern with meter-based lane widths.
**Blocked by:** Gazebo world name must match PX4_GZ_WORLD env var exactly. Collision avoidance spam caused browser freeze. Camera bridge needs restart after drone reconnection. Sim performance is slow on laptop CPU.
**Decision:** Need real CV pipeline (YOLO + Claude Vision), not position-based shortcuts. Moving to AWS GPU for sim performance is priority. Path planner simplified — Voronoi was overkill, horizontal strip division is cleaner.
**Next:** YOLO real-time object detection on camera feed. Claude Vision for scene analysis. AWS EC2 GPU setup for sim performance. Fix camera mounting angle on drone model.
**Hours:** 4h

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

## Nov 21, 2026 - Day 4 (Session 2)

**Plan:** Optimize camera performance and test 1-camera config
**Actual:** Built full camera pipeline (Gazebo → ros_gz_image → CameraManager → MJPEG → browser). 3 cameras overwhelmed local GPU. Optimized: downscale 1280x960 → 480x360, JPEG quality 50, throttle to 4fps. Switched to 1-camera config (drone 1 = x500_mono_cam_45, drones 2-3 = x500). Camera feed overlay in Command Center: switchable per drone, click to resize. Created Day 3 demo artifact and build-in-public content log for LinkedIn/Twitter.
**Blocked by:** 3 camera viewpoints made Gazebo choppy on local GPU. Timing issue: Command Center started before ros_gz_image bridge was registered in ROS2 DDS, causing empty camera discovery.
**Decision:** 1-camera config as interim — only drone 1 gets camera model. Plan to move sim to AWS EC2 GPU instance (g5.xlarge, $25K credits available) for multi-camera. Stream sleep increased to 250ms to match throttled frame rate.
**Next:** Whisper STT backend, AWS EC2 GPU setup.
**Hours:** 2h

## Nov 21, 2026 - Day 4 (Session 1)

**Plan:** Fix disk space crisis (PX4 stdout logs filled disk to 0 bytes free)
**Actual:** Found 22 GB of PX4 stdout logs in `/tmp/px4_drone{1,3}.log` (11 GB each) plus 727 MB of camera test logs. No PX4/Gazebo processes running (crashed or killed when disk hit 0). Deleted all temp files, cleared Chrome cache — freed 24 GB (93% → 76%, 35 GB free). Root-caused to `start_px4_swarm.sh` redirecting PX4 stdout to `/tmp/*.log` with no size limit. Fixed by redirecting to `/dev/null`. Created `scripts/cleanup_disk.sh` one-command emergency cleanup script. Updated CLAUDE.md and disk-management docs.
**Blocked by:** Disk at 0 bytes prevented Claude from starting. Had to recover some space before session could begin.
**Decision:** PX4 stdout goes to `/dev/null` — we don't need it (useful diagnostics are in ROS2 topics and set_px4_params.py output). Emergency cleanup script avoids having to remember the multi-step manual process.
**Next:** Camera feed in Command Center, Whisper STT backend.
**Hours:** 0.5h

## Nov 20, 2026 - Day 3 (Session 2)

**Plan:** Wire end-to-end command execution pipeline (NLP → orchestrator → swarm → PX4)
**Actual:** Rewrote `SwarmBridge` in `app.py` with full execution capability: LAND/RTH/TAKEOFF dispatch directly to SwarmManager, complex missions (formation, search, patrol, orbit) route through MissionExecutor → PathPlanner → SwarmManager GPS waypoints. Added `sync_fleet_telemetry()` that pushes PX4 telemetry into FleetManager on every tick. Rewrote `start_command_center.py` with `--live` mode that creates ROS2 SwarmManager in a background thread, wires FleetManager + MissionExecutor + SwarmBridge together. Fixed `altitude_agl_m` validation bug (ge=1.0 → ge=0.0) — LLM correctly returns 0.0 for land commands. Tested simulated mode: both land and formation commands parse successfully.
**Blocked by:** Nothing
**Decision:** Hybrid architecture — single process with ROS2 spinning in background thread rather than separate processes. SwarmBridge holds references to all pipeline components. Simple commands (LAND/RTH/TAKEOFF) bypass MissionExecutor for lower latency.
**Next:** Camera feed in Command Center, Whisper STT backend.
**Hours:** 3h (including live testing)

**Live test results:**
- Fixed 3 bugs blocking E2E: `SYS_HAS_MAG=0` broke EKF yaw alignment; `FleetManager.is_available` excluded ARMED drones; `MissionExecutor` required `center_point` for formations
- After fixes: "fly triangle formation" → NLP parses → allocates 3 drones → computes waypoints → drones fly to positions in Gazebo
- "land all drones" → all 3 descend and land
- Also fixed `struct.pack("I", -1)` crash in set_px4_params.py (unsigned can't hold -1)

## Nov 20, 2026 - Day 3 (Session 1)

**Plan:** Reorganize project structure, nuke all ArduPilot dead code, make project self-contained
**Actual:** Flattened `src/drone_vla/` to `drone_vla/` at project root (one less nesting level). Deleted 14 ArduPilot files (`drone.py`, `mavlink_bridge.py`, `docker-compose.yml`, `launch/`, etc.) and 9 dead MAVSDK scripts. Tracked `px4_msgs` source in `ros2_ws/src/` so the project is fully self-contained. Updated `pyproject.toml` (packages.find.where to `["."]`, replaced mavsdk dep with pymavlink). Rewrote `main.py` and `orchestrator_node.py` to remove MAVLinkBridge references. Fixed config path resolution bug (`parents[2]` → `parents[1]` after flatten). Synced YAML defaults (haiku-4.5 model, ros2 enabled). Updated 7 docs with correct file paths. Ran full test suite: 11/11 component tests pass, 4 expected ROS2/audio skips.
**Blocked by:** Nothing
**Decision:** Keep px4_msgs inside the project for self-containment (user requirement — "everything needed should be in this folder"). Historical ArduPilot docs (feasibility analysis, hardware recs, etc.) preserved as records of the journey rather than deleted.
**Next:** Wire live PX4 telemetry to Command Center. End-to-end command execution pipeline.
**Hours:** 2h

## Nov 20, 2026 - Day 2

**Plan:** Get simulated camera working with 45-degree fixed mount via ros_gz_bridge into ROS2
**Actual:** Created custom `x500_mono_cam_45` Gazebo model (0.7854 rad pitch = 45 deg forward-down). Discovered critical version mismatch: the default `ros-humble-ros-gz-bridge` links against Gazebo Fortress (gz-transport12) but we run Gazebo Harmonic (gz-transport13) — the bridge silently produces zero messages. Fixed by installing `ros-humble-ros-gzharmonic-bridge` and `ros-humble-ros-gzharmonic-image` (replaces the Fortress packages). Camera images now flow at ~4-9 Hz, 1280x960 RGB, verified with test script that saves frames as PNG. Also documented all PX4 SITL findings and disk management procedures after losing previous chat history.
**Blocked by:** ros_gz_bridge Fortress/Harmonic transport version mismatch — no error messages, just silence. Took multiple install attempts (`apt 404` errors from stale optional deps in meta-package; fixed with `--no-install-recommends`). Also: previous session context was lost to compaction with no doc trail, so had to reconstruct and document retroactively.
**Decision:** 45-degree camera angle for the fixed mount — best compromise between forward navigation view and ground reconnaissance. No gimbal on real hardware. Also established strict doc-and-push-after-every-change rule to prevent knowledge loss.
**Next:** Integrate camera feed into swarm start script. Begin telemetry streaming layer. Start NLP command parsing with Claude Bedrock.
**Hours:** 3h

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