"""Main entry point — standalone async loop tying STT -> Intent Parser -> Orchestrator -> Flight."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from drone_vla.config import load_config
from drone_vla.flight.mavlink_bridge import MAVLinkBridge
from drone_vla.nlp.intent_parser import IntentParser
from drone_vla.orchestrator.fleet_manager import FleetManager
from drone_vla.orchestrator.mission_executor import MissionExecutor
from drone_vla.stt.whisper_engine import WhisperSTT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("drone_vla")


async def run_pipeline(config_path: str | None = None):
    config = load_config(config_path)

    fleet = FleetManager(config.fleet)
    bridge = MAVLinkBridge(config.fleet, config.simulation, fleet)
    executor = MissionExecutor(fleet, bridge.send_waypoints)
    parser = IntentParser(config.llm)
    stt = WhisperSTT(config.stt)

    logger.info("Connecting to %d ArduPilot SITL instances...", config.simulation.sitl_instances)
    await bridge.connect_all()
    logger.info("All drones connected. Listening for voice commands...")

    async def process_command(text: str):
        logger.info("Operator: %s", text)
        fleet_state = fleet.get_fleet_state_summary()
        intent = await parser.aparse(text, fleet_state)

        if intent.clarification_needed:
            logger.warning("Clarification needed: %s", intent.clarification_needed)
            return

        for cmd in intent.commands:
            logger.info("Executing: %s (confidence=%.2f)", cmd.mission_type.value, intent.confidence)
            mission = await executor.execute_command(cmd)
            if mission:
                logger.info("Mission %s started with drones %s",
                            mission.mission_id, mission.assigned_drones)

    battery_check_interval = 5.0

    async def battery_monitor():
        while True:
            low = fleet.check_battery_warnings()
            for d in low:
                logger.warning("AUTO-RTH: Drone %d battery at %.0f%%", d.drone_id, d.battery_pct)
                backup = fleet.handle_failover(d.drone_id)
                if backup:
                    logger.info("Failover: drone %d -> drone %d", d.drone_id, backup.drone_id)
            await asyncio.sleep(battery_check_interval)

    monitor_task = asyncio.create_task(battery_monitor())

    try:
        async for text in stt.stream_transcriptions():
            await process_command(text)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        monitor_task.cancel()
        stt.stop()
        await bridge.shutdown()


async def run_text_mode(config_path: str | None = None):
    """Text input mode for testing without a microphone."""
    config = load_config(config_path)

    fleet = FleetManager(config.fleet)
    bridge = MAVLinkBridge(config.fleet, config.simulation, fleet)
    executor = MissionExecutor(fleet, bridge.send_waypoints)
    parser = IntentParser(config.llm)

    logger.info("Connecting to %d ArduPilot SITL instances...", config.simulation.sitl_instances)
    await bridge.connect_all()
    logger.info("Text mode ready. Type commands (Ctrl+C to exit):")

    loop = asyncio.get_event_loop()
    try:
        while True:
            text = await loop.run_in_executor(None, lambda: input("\n> "))
            if not text.strip():
                continue
            if text.strip().lower() in ("quit", "exit"):
                break

            fleet_state = fleet.get_fleet_state_summary()
            intent = await parser.aparse(text, fleet_state)

            if intent.clarification_needed:
                print(f"  ? {intent.clarification_needed}")
                continue

            for cmd in intent.commands:
                print(f"  -> {cmd.mission_type.value} "
                      f"(drones={cmd.assignment.drone_ids}, conf={intent.confidence:.2f})")
                mission = await executor.execute_command(cmd)
                if mission:
                    print(f"  Mission {mission.mission_id} started: drones {mission.assigned_drones}")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        await bridge.shutdown()


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Drone VLA — Natural Language Swarm C2")
    ap.add_argument("--config", default=None, help="Path to config YAML")
    ap.add_argument("--text", action="store_true", help="Text input mode (no microphone)")
    args = ap.parse_args()

    coro = run_text_mode(args.config) if args.text else run_pipeline(args.config)
    asyncio.run(coro)


if __name__ == "__main__":
    main()
