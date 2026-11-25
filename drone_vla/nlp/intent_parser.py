"""Intent parser using Claude on AWS Bedrock for structured mission command extraction."""

from __future__ import annotations

import json
import logging

import boto3

from drone_vla.config import LLMConfig
from drone_vla.nlp.schemas import MissionCommand, MissionType, ParsedIntent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a tactical drone swarm command parser for a Search & Rescue demonstration. \
Translate natural language operator commands into structured JSON mission specifications.

ENVIRONMENT:
- Home/origin: 47.397971°N, 8.546164°E (center of a SAR village)
- The village has: a warehouse (NE, ~30m from origin), houses (NW and SW), a tower (SE, ~40m), \
shipping containers (far NE, ~40m), vehicles on roads, and SAR target markers (orange/red/yellow) \
scattered around the area
- 3 drones available (IDs 1, 2, 3). Drone 1 has a camera.
- Operating radius: ~100m from home

COORDINATE HELPERS — use these to convert relative references to GPS:
- 1 meter north ≈ +0.000009° latitude
- 1 meter east  ≈ +0.0000135° longitude (at this latitude)
- Home: lat=47.397971, lon=8.546164
- "around here" / "the area" / "the map" → 100m radius from home
- "nearby" / "around me" / radius with no location → center on the ASSIGNED DRONE'S current position from fleet state
- "the warehouse" → lat=47.39820, lon=8.54650
- "the houses" → lat=47.39820, lon=8.54589 (NW house)
- "the tower" → lat=47.39775, lon=8.54657
- "the containers" → lat=47.39813, lon=8.54668

RULES:
1. Extract ALL commands from the utterance. One sentence may contain multiple commands.
2. If drones are named ("Drone 1", "all drones"), set the assignment. Otherwise leave empty.
3. USE THE COORDINATE HELPERS to generate actual GPS coordinates. Do NOT ask for GPS coordinates \
— convert relative references ("100m radius", "near the warehouse", "sweep the area") yourself.
4. For area_search: generate a search_polygon (4+ points forming the search area). \
For "100m radius" or "the area", use a square: center ± radius in each direction. \
IMPORTANT: If a radius is given with no specific location, center the search on the \
assigned drone's CURRENT GPS position from the fleet state, NOT on home.
5. For point_inspection: set target_point to the GPS of the referenced location.
6. Default altitude: 15m AGL. Default speed: 5 m/s.
7. Default contingency is auto_rth.
8. IMPORTANT: This is a demo — be helpful, not pedantic. If the operator says something \
reasonable, make it work with sensible defaults. Only set clarification_needed for truly \
ambiguous commands (e.g., contradictory instructions). Never ask for GPS coordinates.
9. Follow-up messages refer to the previous command context. "within 100m radius" after \
"search for trees" means: search for trees within 100m radius.
10. target_classes: set based on what the operator wants to find ("trees", "people", "vehicles").

Respond with ONLY valid JSON (no markdown, no explanation):
{
  "commands": [<list of MissionCommand objects>],
  "confidence": <float 0-1>,
  "clarification_needed": <string or null>
}

MissionCommand fields:
- mission_type: area_search | perimeter_patrol | formation_flight | point_inspection | \
relay_station | return_to_home | takeoff | land | loiter
- assignment: {"drone_ids": [int], "group_name": str|null}
- search_polygon: [{"lat": float, "lon": float}, ...] — for area_search
- perimeter_polygon: [{"lat": float, "lon": float}, ...] — for perimeter_patrol
- center_point: {"lat": float, "lon": float} — orbit center
- target_point: {"lat": float, "lon": float} — for point_inspection
- altitude_agl_m: float (meters above ground, default 15)
- speed_ms: float (meters/second, default 5)
- formation_type: line | triangle | diamond | circle | v_shape | grid
- spacing_m, heading_deg, orbit_radius_m, direction (clockwise/counterclockwise)
- sensor_mode: rgb | thermal | thermal_rgb_fused | multispectral
- target_classes: [str] — object types to detect
- contingency: auto_rth | loiter_in_place | land_immediately | continue_mission
- raw_intent: the original text fragment this command was parsed from\
"""


MAX_HISTORY = 10


class IntentParser:
    def __init__(self, config: LLMConfig):
        self._config = config
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=config.region,
        )
        self._model_id = config.model_id
        self._history: list[dict] = []

    def parse(self, text: str, fleet_state: dict | None = None) -> ParsedIntent:
        user_content = f"Operator command: {text}"
        if fleet_state:
            user_content += f"\n\nCurrent fleet state:\n{json.dumps(fleet_state, indent=2)}"

        self._history.append({"role": "user", "content": user_content})
        if len(self._history) > MAX_HISTORY:
            self._history = self._history[-MAX_HISTORY:]

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._config.max_tokens,
            "temperature": self._config.temperature,
            "system": SYSTEM_PROMPT,
            "messages": list(self._history),
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

        self._history.append({"role": "assistant", "content": assistant_text})
        if len(self._history) > MAX_HISTORY:
            self._history = self._history[-MAX_HISTORY:]

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
