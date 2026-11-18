---
title: Hardware Recommendations
description: 3-tier hardware options for the physical drone setup with cost breakdowns
tags:
  - hardware
  - budget
  - physical
---
# Hardware Recommendations

Three tiers for your 3-drone physical setup. All are ArduPilot-native, which means the same codebase works in [simulation and physical](./master-plan.md) with only a config change.

## Chosen Build: SpeedyBee F405 V4 DIY

> **Decision made.** Budget constraint of $500-600 means we go DIY with SpeedyBee F405 V4 stacks on 5" frames. Same ArduPilot firmware as Pixhawk, fraction of the price. Full purchase plan in [Hardware Feasibility](./feasibility-analysis.md). Full financial projections in [Cost & Feasibility Analysis](./cost-feasibility-analysis.md).

## Decision Matrix

| Factor | **Chosen: DIY SpeedyBee** | Tier 2: Dev Kit | Tier 3: Pro |
|--------|--------------------------|----------------------|-------------|
| **Per-drone cost** | **~$155** | ~$450-550 | ~$700-900 |
| **Total (3 drones)** | **~$465 + $116 shared** | ~$1,350-1,650 | ~$2,100-2,700 |
| **Flight controller** | **SpeedyBee F405 V4** | Pixhawk 6C | CubePilot Orange+ |
| **Frame** | **5" (Source One/Mark4)** | Holybro X500 V2 | Holybro X500 V2 |
| **GPS** | **BN-880** | M9N with compass | HERE3+ RTK-ready |
| **Companion computer** | **None (ground station)** | Raspberry Pi 4/5 | Jetson Orin Nano |
| **Camera** | **None (sim for demo)** | Pi Camera v3 | Pi Camera + Thermal |
| **Telemetry** | **ESP32 Wi-Fi** | Wi-Fi (ESP32) | Wi-Fi + 4G fallback |
| **Flight time** | **~8-12 min (5")** | ~18 min | ~20 min |
| **Assembly difficulty** | **High (full DIY solder)** | Easy (dev kit) | Medium |
| **Best for** | **$600 budget demo** | Unlimited budget demo | Sustained development |

## Reference: Tier 2 (Holybro X500 V2 Dev Kit)

This was the original recommendation before the $500-600 budget constraint. It remains the upgrade path if budget opens up (e.g., after funding). It is the ArduPilot reference development platform with excellent community support.

### Bill of Materials (per drone)

| Component | Product | Approx. Cost |
|-----------|---------|---------------|
| Frame kit | Holybro X500 V2 kit (frame + motors + ESCs + PDB) | $180 |
| Flight controller | Pixhawk 6C | $120 (often bundled) |
| GPS | M9N GPS with compass | $45 |
| Battery | 4S 5200mAh LiPo | $40 |
| Propellers | 10x4.5 (2 sets) | $15 |
| Companion computer | Raspberry Pi 5 (4GB) | $60 |
| Camera | Pi Camera Module 3 | $25 |
| Wi-Fi telemetry | ESP32 or Pi onboard Wi-Fi | $0-15 |
| Misc (wires, mounts, zip ties) | | $15 |
| **Per drone total** | | **~$500-520** |
| **3 drones** | | **~$1,500-1,560** |

### Additional Equipment

| Item | Cost |
|------|------|
| LiPo charger (ISDT D2) | $50 |
| Battery checker/alarm | $10 |
| Spare props (3 sets) | $25 |
| Tool kit (hex drivers, soldering iron) | $30 |
| Landing pad (portable) | $20 |
| Carry case | $40 |
| **Accessories total** | **~$175** |

### Grand Total: ~$1,675-1,735

Well within range, and you get a professional-looking setup for the demo video.

## Communication Architecture

For the demo, all 3 drones connect to a portable Wi-Fi router. The laptop runs the NLP pipeline and sends MAVLink commands over Wi-Fi.

```
Laptop (NLP + Orchestrator)
    |
    | Wi-Fi (5GHz, dedicated router)
    |
    +--- Drone 1 (Pi 5 + ArduPilot)
    +--- Drone 2 (Pi 5 + ArduPilot)
    +--- Drone 3 (Pi 5 + ArduPilot)
```

The Raspberry Pi on each drone runs a lightweight MAVLink proxy that bridges Wi-Fi to the Pixhawk's serial port. MAVSDK-Python on the laptop connects to each Pi's IP address.

## Where to Buy

- **Holybro X500 V2 kit:** Holybro direct store, Amazon, RobotShop, GetFPV
- **Pixhawk 6C:** Same as above (often bundled with X500)
- **Raspberry Pi 5:** Adafruit, PiShop, Amazon
- **LiPo batteries:** Amazon, HobbyKing, GetFPV

Order by **Dec 8** for delivery by Dec 15-17 (standard shipping). Express if ordering later.

## Tier 1: Budget Alternative

If budget is tight, the S500 frame + Pixhawk 4 Mini gives you a working ArduPilot drone for ~$300/each without a companion computer. You lose onboard camera processing but the voice-to-flight demo still works. Camera and detection can be simulated from a ground station.

## Tier 3: Pro Setup

For continued development beyond the demo, a Jetson Orin Nano ($200) replaces the Pi and runs YOLOv8 onboard at 30 FPS. Add a FLIR Lepton thermal module ($200) for real thermal detection. This is the path to the product, not the demo.

## AWS Credits Strategy

With $20K in AWS credits, consider:
- **Bedrock (Claude):** ~$0.003-0.015 per command parse. Even 10,000 test commands costs under $150.
- **EC2 GPU (g5.xlarge):** ~$1.00/hr for YOLOv8 training. A few hours of training costs $5-10.
- **EC2 for remote SITL:** Run SITL on a c5.2xlarge ($0.34/hr) if local Docker is too slow on Windows.
- **S3 for telemetry logs:** Essentially free for logging mission data.

You will use less than $500 of the $20K credits. The rest is runway for scaling later.