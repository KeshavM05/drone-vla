---
title: Disk Management
description: How to prevent PX4 SITL from filling the 149 GB dev partition, cleanup procedures, and rules for agents
tags:
  - guide
  - operations
  - disk
  - px4
---
# Disk Management

This dev machine has a 149 GB partition. PX4 SITL simulation and build artifacts can fill it in hours if not managed. Every agent and developer working in this repo must follow these rules.

## The PX4 Log Problem

PX4 SITL generates two types of disk-eating output:

1. **`.ulg` flight logs** written to `~/PX4-Autopilot/build/px4_sitl_default/rootfs/*/log/` — hundreds of MB per hour per drone
2. **stdout logs** — the start script previously redirected PX4 stdout to `/tmp/px4_drone*.log`, which grew to **11 GB each** (22 GB total for 3 drones)

On 2026-11-19, .ulg logs consumed **27+ GB** in 7.5 hours. On 2026-11-21, stdout logs consumed **22+ GB**. Both incidents filled the disk completely.

### Fix applied (2026-11-21)

- `start_px4_swarm.sh` now redirects PX4/MicroXRCE stdout to `/dev/null` instead of `/tmp/*.log`
- Start script clears old `/tmp/px4_*.log` files on launch
- `cleanup_disk.sh` added for one-command emergency cleanup

### Why deleting files doesn't free space

Linux keeps disk allocated for files that have open file descriptors. If PX4 or Gazebo is still running and has a `.ulg` file open, `rm` marks the file as deleted but the kernel does not reclaim the blocks until the process closes or dies.

This means:
1. You `rm -rf` the log directory
2. `df -h` still shows the disk full
3. You delete more things, still full
4. You kill PX4/Gazebo
5. Suddenly 27 GB frees up

**Always kill processes first, then clean up files.**

## Cleanup Procedure

One-liner: `bash ~/drone-vla/scripts/cleanup_disk.sh` — kills processes, deletes all PX4/Gazebo temp files, clears Chrome cache, and reports disk before/after.

Manual steps:

```bash
# 1. Kill PX4 + Gazebo + XRCE Agent
pkill -f "px4.*-i [0-9]"
pkill -f "gz sim"
pkill -f MicroXRCEAgent
sleep 2

# 2. Clear PX4 flight logs and stdout logs
rm -rf ~/PX4-Autopilot/build/px4_sitl_default/rootfs/*/log/
rm -rf ~/PX4-Autopilot/build/px4_sitl_default/rootfs/log/
rm -f /tmp/px4_drone*.log /tmp/px4_cam*.log /tmp/xrce_agent.log

# 3. Verify
df -h /
```

## Mitigations in Place

- **`scripts/start_px4_swarm.sh`** clears old logs on launch, redirects PX4 stdout to `/dev/null` (see [PX4 SITL Setup](./px4-sitl-setup.md))
- **`scripts/cleanup_disk.sh`** one-command emergency cleanup: kills processes, deletes all temp/log files, clears Chrome cache
- **`scripts/set_px4_params.py`** sets `SDLOG_MODE=-1` to disable .ulg logging after PX4 boots
- **`.gitignore`** excludes `ros2_ws/`, `terrain/`, and `*.log` from the repo

## What's Eating Disk

Baseline usage as of 2026-11-19:

| Directory | Size | Notes |
|-----------|------|-------|
| `~/PX4-Autopilot/build/` | 3.8 GB | Build artifacts, needed |
| `~/PX4-Autopilot/.git/` | 1.3 GB | Could shallow-clone to reduce |
| `~/.local/lib/python3.10/nvidia+torch+triton` | 5.0 GB | PyTorch GPU stack — remove if not using local ML |
| `~/.cache/google-chrome/` | 1.1 GB | Safe to clear anytime |
| `~/.gz/` | 707 MB | Gazebo models, needed for sim |
| `~/Micro-XRCE-DDS-Agent/` | 421 MB | Build dir, needed |

## Rules for Agents

1. **Check disk before starting PX4:** `df -h /` — do not start if < 5 GB free
2. **Always kill PX4 when done** — never leave instances running idle
3. **Use the start script** (`bash ~/drone-vla/scripts/start_px4_swarm.sh`) which handles cleanup
4. **If disk fills during a session:** kill all PX4/Gazebo first, then clear logs, then verify with `df -h /`