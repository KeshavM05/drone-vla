---
title: Getting Started
description: Environment setup, dependency installation, and running your first simulation
tags:
  - guide
  - setup
---
# Getting Started

## Prerequisites

- **Python 3.10+** with pip
- **PX4 v1.16** built from source (see [PX4 SITL Setup](./px4-sitl-setup.md))
- **Node.js 24+** (for OpenKnowledge docs — use `fnm use 24`)
- **AWS credentials** configured for Bedrock access (`aws configure` or env vars)
- **Microphone** (optional — text mode works without one)

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url>
cd drone-vla
pip install -e ".[dev]"
```

### 2. Configure AWS Bedrock

Copy the environment template and fill in your AWS credentials:

```bash
cp .env.example .env
# Edit .env with your AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
```

Or use an AWS profile:
```bash
export AWS_PROFILE=your-profile
```

### 3. Start PX4 SITL simulation

See [PX4 SITL Setup](./px4-sitl-setup.md) for detailed instructions.

**Quick Docker start:**
```bash
docker compose up
```

### 4. Run in text mode (no mic needed)

```bash
drone-vla --text
```

You should see:
```
Connecting to 3 PX4 SITL instances...
All drones connected. Text mode ready.
Type commands (Ctrl+C to exit):

> take off all drones to 20 meters
  -> takeoff (drones=[], conf=0.95)
  Mission M0001 started: drones [1, 2, 3]
```

### 5. Run with voice input

```bash
drone-vla
```

Speak into your microphone. The system transcribes your speech, parses intent via Claude, and dispatches commands to the simulated drones.

## Running Tests

```bash
pytest
```

Tests cover [mission schemas](../api/mission-schemas.md), path planning algorithms, and fleet manager allocation/failover logic. No SITL or AWS credentials needed for tests.

## Project Structure

See [System Overview](../architecture/system-overview.md) for the full 4-tier architecture breakdown.