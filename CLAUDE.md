# Drone VLA — Natural Language Drone Swarm C2

## Project Overview
Voice/text commands → Claude (Bedrock) intent extraction → autonomous multi-drone swarm orchestration via PX4 + ROS2.

## Stack
- **Flight controller**: PX4 v1.16 SITL
- **LLM**: Claude API via AWS Bedrock for structured intent extraction
- **Middleware**: Python + ROS2 (Humble) nodes via MicroXRCE-DDS
- **STT**: faster-whisper for local speech-to-text
- **Simulation**: PX4 SITL + Gazebo Harmonic
- **Path planning**: Voronoi decomposition, APF, boustrophedon sweep

## Project Structure
```
drone_vla/
  stt/            — Speech-to-text (faster-whisper)
  nlp/            — Intent parsing (Claude Bedrock) + Pydantic schemas
  orchestrator/   — Fleet manager, path planner, mission executor
  flight/         — PX4 drone controller, collision avoidance, GPS/NED utils
  ros2_bridge/    — ROS2 node wrappers (STT, orchestrator, intent)
  web/            — Command Center (FastAPI + WebSocket dashboard)
config/           — YAML config + JSON mission schemas
scripts/          — PX4 SITL launcher, tests, command center starter
ros2_ws/          — ROS2 workspace with px4_msgs (source this for ROS2)
tests/            — pytest tests
docs/             — OpenKnowledge documentation
```

## Commands
- `drone-vla --text` — Run in text-input mode (no mic needed)
- `drone-vla --web` — Launch Command Center web UI
- `drone-vla` — Run with voice input (requires microphone)
- `pytest` — Run tests
- `bash ~/drone-vla/scripts/start_px4_swarm.sh` — Launch 3-drone PX4 SITL swarm + MicroXRCEAgent
- `python3 ~/drone-vla/scripts/test_px4_ros2_swarm.py` — Swarm test (arm, takeoff, triangle, land)
- `python3 ~/drone-vla/scripts/set_px4_params.py` — Disable PX4 preflight checks via pymavlink
- `python3 ~/drone-vla/scripts/test_collision_avoidance.py` — Test collision avoidance with 3 drones
- `python3 ~/drone-vla/scripts/start_command_center.py` — Launch Command Center (http://localhost:8080)
- `python3 ~/drone-vla/scripts/test_camera_bridge.py` — Test Gazebo camera → ROS2 image bridge

## Documentation
This project uses **OpenKnowledge** for all documentation. This is a hard requirement — follow it throughout the entire development process.

### Rules
- **ALWAYS** use OpenKnowledge MCP tools (`exec`, `write`, `edit`, `search`) for ALL `.md` / `.mdx` files — never use native Read/Edit/Write/Grep on markdown
- Document architecture decisions, API contracts, and integration guides as you build
- Keep docs in sync with code changes — when you modify a module, update its corresponding doc in `docs/`
- Use `ok start` or `ok open <doc>` to preview documentation locally
- Node.js 24+ required (`fnm use 24` before running `ok` commands)

### Documentation Structure
```
docs/
  index.md                        — Documentation hub
  architecture/
    system-overview.md             — 4-tier architecture with Mermaid diagrams
    collision-avoidance.md         — 3-layer CA system design
    guardrails.md                  — Safety rules for sim vs real
    data-flow.md                   — End-to-end command trace
  guides/
    getting-started.md             — Environment setup, first run
    px4-sitl-setup.md              — PX4 v1.16 multi-drone SITL with Gazebo + ROS2
    command-center.md              — Command Center web UI guide
    disk-management.md             — Disk space management
  api/
    mission-schemas.md             — Pydantic model reference
    fleet-manager.md               — Fleet allocation and failover API
  plan/
    current-status.md              — Living snapshot of project state
    feature-backlog.md             — Organized feature backlog
    daily-log.md                   — Daily progress log
  milestones/
    phase-1-simulation.md          — 14-day MVP plan
```

### When to Update Docs
- Adding a new module or feature → add/update the relevant doc
- Changing an API or schema → update `docs/api/`
- Making an architecture decision → document rationale in `docs/architecture/`
- Hitting a milestone → update `docs/milestones/`

## Git Workflow
- **Commit after every meaningful change.** Don't batch — commit as you go.
- **Push after every commit.** Run `git push` immediately after committing. The user works across multiple machines and needs changes available everywhere.
- Use logical, atomic commits: one commit per feature, fix, or doc update.
- Commit messages: short imperative subject, optional body explaining "why".
- Always end commit messages with: `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
- Never commit `.env`, credentials, or model weights.
- When both code and docs change together, separate into two commits (code first, then docs).
- **Document everything meaningful in OpenKnowledge docs AND commit+push.** If you made a decision, fixed a bug, discovered a gotcha, or changed architecture — it goes in docs/ via OK MCP tools, then gets committed and pushed. No exceptions.

## Shell Commands
- When suggesting `!` commands for the user to run, **always use absolute paths**: `bash ~/drone-vla/scripts/foo.sh`, `python3 -I ~/drone-vla/scripts/foo.py`
- **Never** use `cd && ./relative/path` patterns — the shell tab-completes instead of executing
- For env vars inline: `VAR=val command /absolute/path`

## ROS2 Workspace
- `ros2_ws/` contains px4_msgs source and build — source `ros2_ws/install/local_setup.bash` for ROS2 msg types
- px4_msgs is also available from `~/ros_workspace_2025/perception_ws/install/` (sourced in .bashrc)
- PX4 communication uses ROS2 px4_msgs via MicroXRCE-DDS (not MAVLink for flight control)
- pymavlink is only used for parameter setting (`scripts/set_px4_params.py`)

## Disk Space Management — READ THIS FIRST
This machine has a 149 GB partition that fills up fast. Every agent working in this repo MUST follow these rules:

### PX4 SITL writes flight logs that eat disk
- PX4 writes `.ulg` logs continuously to `~/PX4-Autopilot/build/px4_sitl_default/rootfs/*/log/`
- 3 idle drones = 27+ GB in hours. **Always kill PX4 when done:**
  ```
  pkill -f "px4.*-i [0-9]"; pkill -f "gz sim"; pkill -f MicroXRCEAgent
  ```
- The start script (`scripts/start_px4_swarm.sh`) clears old logs automatically on launch
- `scripts/set_px4_params.py` disables logging (`SDLOG_MODE=-1`) but only takes effect after PX4 boots

### Open file descriptors hold disk even after deletion
- If you `rm` files while PX4/Gazebo are still running, the OS does NOT free the space — the processes hold open file handles
- You MUST kill the processes first, then delete files, to actually reclaim disk
- Run `df -h /` before and after cleanup to verify space was freed

### Before starting PX4
- Check disk: `df -h /` — do NOT start PX4 if less than 5 GB free
- Use the start script which handles cleanup: `bash ~/drone-vla/scripts/start_px4_swarm.sh`

### Known large directories on this machine
- `~/PX4-Autopilot/build/` — 3.8 GB (PX4 build artifacts)
- `~/PX4-Autopilot/.git/` — 1.3 GB
- `~/.local/lib/python3.10/site-packages/nvidia+torch+triton` — 5 GB (PyTorch GPU stack)
- `~/.cache/google-chrome/` — 1+ GB (safe to clear)

## Conventions
- Python 3.10+, asyncio throughout
- Pydantic v2 for all data schemas
- ROS2 px4_msgs for PX4 communication (pymavlink only for param setting)
- All drone IDs are 1-based integers
- GPS coordinates as decimal degrees (lat, lon)
- Altitudes in meters AGL (above ground level)
- Config via YAML (`config/default.yaml`), overridable via env vars
- Node.js 24+ required for OpenKnowledge (`fnm use 24`)
