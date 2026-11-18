# Drone VLA — Natural Language Drone Swarm C2

## Project Overview
Voice/text commands → Claude (Bedrock) intent extraction → autonomous multi-drone swarm orchestration via ArduPilot + ROS2.

## Stack
- **Flight controller**: ArduPilot SITL (not PX4 — PX4 lacks proper ros_gz_bridge)
- **LLM**: Claude API via AWS Bedrock for structured intent extraction
- **Middleware**: Python + ROS2 (Humble) nodes
- **STT**: faster-whisper for local speech-to-text
- **Simulation**: ArduPilot SITL + Gazebo with ros_gz_bridge
- **Path planning**: Voronoi decomposition, APF, boustrophedon sweep

## Project Structure
```
src/drone_vla/
  stt/            — Speech-to-text (faster-whisper)
  nlp/            — Intent parsing (Claude Bedrock) + Pydantic schemas
  orchestrator/   — Fleet manager, path planner, mission executor
  flight/         — MAVSDK-Python bridge to ArduPilot
  ros2_bridge/    — ROS2 node wrappers
config/           — YAML config + JSON mission schemas
launch/           — ROS2 launch files
tests/            — pytest tests
```

## Commands
- `drone-vla --text` — Run in text-input mode (no mic needed)
- `drone-vla` — Run with voice input (requires microphone)
- `pytest` — Run tests
- `docker compose up` — Start ArduPilot SITL + Gazebo
- `ros2 launch drone_vla simulation.launch.py` — Full ROS2 pipeline

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
    data-flow.md                   — End-to-end command trace with sequence diagrams
  guides/
    getting-started.md             — Environment setup, first run
    ardupilot-sitl-setup.md        — Docker or native SITL configuration
  api/
    mission-schemas.md             — Pydantic model reference
    fleet-manager.md               — Fleet allocation and failover API
  milestones/
    phase-1-simulation.md          — 14-day MVP plan with accountability checkpoints
```

### When to Update Docs
- Adding a new module or feature → add/update the relevant doc
- Changing an API or schema → update `docs/api/`
- Making an architecture decision → document rationale in `docs/architecture/`
- Hitting a milestone → update `docs/milestones/`

## Conventions
- Python 3.10+, asyncio throughout
- Pydantic v2 for all data schemas
- MAVSDK-Python (not pymavlink) for ArduPilot communication
- All drone IDs are 1-based integers
- GPS coordinates as decimal degrees (lat, lon)
- Altitudes in meters AGL (above ground level)
- Config via YAML (`config/default.yaml`), overridable via env vars
- Node.js 24+ required for OpenKnowledge (`fnm use 24`)
