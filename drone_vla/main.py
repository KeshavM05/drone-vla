"""Main entry point — ties STT -> Intent Parser -> Orchestrator -> PX4 Flight via ROS2."""

from __future__ import annotations

import asyncio
import logging
import sys

from drone_vla.config import load_config
from drone_vla.nlp.intent_parser import IntentParser
from drone_vla.orchestrator.fleet_manager import FleetManager
from drone_vla.orchestrator.mission_executor import MissionExecutor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("drone_vla")


async def run_text_mode(config_path: str | None = None):
    """Text input mode for testing without a microphone."""
    config = load_config(config_path)

    fleet = FleetManager(config.fleet)
    parser = IntentParser(config.llm)

    logger.info("Text mode ready. Type commands (Ctrl+C to exit):")
    logger.info("Note: flight commands require PX4 SITL + SwarmManager running separately")

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
    except (KeyboardInterrupt, EOFError):
        pass


async def run_voice_mode(config_path: str | None = None):
    """Voice input mode with Whisper STT."""
    config = load_config(config_path)

    fleet = FleetManager(config.fleet)
    parser = IntentParser(config.llm)

    from drone_vla.stt.whisper_engine import WhisperSTT
    stt = WhisperSTT(config.stt)

    logger.info("Voice mode ready. Speak commands (Ctrl+C to exit):")
    logger.info("Note: flight commands require PX4 SITL + SwarmManager running separately")

    try:
        async for text in stt.stream_transcriptions():
            logger.info("Operator: %s", text)
            fleet_state = fleet.get_fleet_state_summary()
            intent = await parser.aparse(text, fleet_state)

            if intent.clarification_needed:
                logger.warning("Clarification needed: %s", intent.clarification_needed)
                continue

            for cmd in intent.commands:
                logger.info("Executing: %s (confidence=%.2f)", cmd.mission_type.value, intent.confidence)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        stt.stop()


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Drone VLA — Natural Language Swarm C2")
    ap.add_argument("--config", default=None, help="Path to config YAML")
    ap.add_argument("--text", action="store_true", help="Text input mode (no microphone)")
    ap.add_argument("--web", action="store_true", help="Launch Command Center web UI")
    args = ap.parse_args()

    if args.web:
        from drone_vla.web.app import run
        run()
    else:
        coro = run_text_mode(args.config) if args.text else run_voice_mode(args.config)
        asyncio.run(coro)


if __name__ == "__main__":
    main()
