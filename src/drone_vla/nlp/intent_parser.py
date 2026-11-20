"""Intent parser using Claude on AWS Bedrock for structured mission command extraction."""

from __future__ import annotations

import json
import logging

import boto3

from drone_vla.config import LLMConfig
from drone_vla.nlp.schemas import MissionCommand, MissionType, ParsedIntent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a tactical drone swarm command parser. Your job is to translate natural language \
operator commands into structured JSON mission specifications.

You control a fleet of autonomous drones. Each drone has:
- A numeric ID (1-based)
- GPS position, altitude, battery level, sensor payload
- Ability to execute: takeoff, land, area_search, perimeter_patrol, formation_flight, \
point_inspection, relay_station, return_to_home

Rules:
1. Extract ALL commands from the utterance. A single sentence may contain multiple commands.
2. If the operator names specific drones or groups ("Drone 1", "Swarm Alpha"), set the assignment.
3. If no drones are specified, leave assignment empty (the orchestrator will auto-assign).
4. Convert all relative directions ("northern ridge", "200m east") to mission parameters. \
If you cannot determine exact GPS coordinates, set the relevant polygon/point fields to null \
and note what you understood in raw_intent.
5. Default contingency is auto_rth (return to home on low battery).
6. If the command is ambiguous, set clarification_needed with a short question.

Respond with ONLY valid JSON matching this schema (no markdown, no explanation):
{
  "commands": [<list of MissionCommand objects>],
  "confidence": <float 0-1>,
  "clarification_needed": <string or null>
}

MissionCommand fields:
- mission_type: area_search | perimeter_patrol | formation_flight | point_inspection | \
relay_station | return_to_home | takeoff | land
- assignment: {"drone_ids": [int], "group_name": str|null}
- altitude_agl_m: float (meters above ground)
- speed_ms: float (meters/second)
- formation_type: line | triangle | diamond | circle | v_shape | grid
- spacing_m, heading_deg, orbit_radius_m, direction (clockwise/counterclockwise)
- sensor_mode: rgb | thermal | thermal_rgb_fused | multispectral
- target_classes: [str] — object types to detect
- contingency: auto_rth | loiter_in_place | land_immediately | continue_mission
- raw_intent: the original text fragment this command was parsed from\
"""


class IntentParser:
    def __init__(self, config: LLMConfig):
        self._config = config
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=config.region,
        )
        self._model_id = config.model_id

    def parse(self, text: str, fleet_state: dict | None = None) -> ParsedIntent:
        user_content = f"Operator command: {text}"
        if fleet_state:
            user_content += f"\n\nCurrent fleet state:\n{json.dumps(fleet_state, indent=2)}"

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._config.max_tokens,
            "temperature": self._config.temperature,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_content}],
        })

        logger.debug("Sending to Bedrock: %s", text)
        response = self._client.invoke_model(
            modelId=self._model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        response_body = json.loads(response["body"].read())
        assistant_text = response_body["content"][0]["text"]

        logger.debug("Bedrock response: %s", assistant_text)
        # Strip markdown code fences if present
        text = assistant_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        parsed = json.loads(text)
        intent = ParsedIntent(**parsed)

        for cmd in intent.commands:
            if not cmd.raw_intent:
                cmd.raw_intent = text

        return intent

    async def aparse(self, text: str, fleet_state: dict | None = None) -> ParsedIntent:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.parse, text, fleet_state)
