"""Command Center backend — FastAPI + WebSocket telemetry bridge."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from drone_vla.config import LLMConfig
from drone_vla.nlp.intent_parser import IntentParser
from drone_vla.nlp.schemas import MissionCommand, MissionType

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Drone VLA Command Center")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class SwarmBridge:
    """Bridges NLP → Orchestrator → SwarmManager → Web UI.

    Live mode: set_swarm_manager() + set_executor() to connect real PX4 telemetry
    and execute commands end-to-end.
    Sim mode: serves simulated telemetry for UI development.
    """

    def __init__(self):
        self._swarm = None
        self._fleet = None
        self._executor = None
        self._intent_parser = None
        self._camera = None
        self._logs: list[dict] = []
        self._max_logs = 500
        self._ws_clients: set[WebSocket] = set()

    def set_swarm_manager(self, swarm):
        self._swarm = swarm

    def set_executor(self, fleet, executor):
        self._fleet = fleet
        self._executor = executor

    def set_camera_manager(self, cam):
        self._camera = cam

    def set_intent_parser(self, parser):
        self._intent_parser = parser

    @property
    def is_live(self) -> bool:
        return self._swarm is not None

    def add_log(self, level: str, message: str, source: str = "system"):
        entry = {
            "timestamp": time.time(),
            "level": level,
            "source": source,
            "message": message,
        }
        self._logs.append(entry)
        if len(self._logs) > self._max_logs:
            self._logs = self._logs[-self._max_logs:]
        asyncio.ensure_future(self._broadcast({"type": "log", "data": entry}))

    def get_telemetry(self) -> list[dict]:
        if self._swarm:
            return self._swarm.get_telemetry()
        return self._sim_telemetry()

    def get_alerts(self) -> list[dict]:
        if self._swarm:
            return self._swarm.get_proximity_alerts()
        return []

    def get_swarm_state(self) -> str:
        if self._swarm:
            return self._swarm.state.value
        return "disconnected"

    async def process_command(self, text: str) -> dict:
        self.add_log("info", f"Command received: {text}", "operator")

        if not self._intent_parser:
            self.add_log("warning", "NLP not connected — command logged only", "system")
            return {"status": "no_nlp", "message": "Intent parser not available"}

        try:
            intent = await self._intent_parser.aparse(text, self._get_fleet_state())
            self.add_log(
                "info",
                f"Parsed {len(intent.commands)} command(s), "
                f"confidence: {intent.confidence:.0%}",
                "nlp",
            )
            if intent.clarification_needed:
                self.add_log(
                    "warning",
                    f"Clarification needed: {intent.clarification_needed}",
                    "nlp",
                )

            executed = []
            if intent.commands and self._executor and self._swarm:
                for cmd in intent.commands:
                    result = await self._execute_command(cmd)
                    executed.append(result)
            elif intent.commands and not self._swarm:
                self.add_log(
                    "warning",
                    "PX4 not connected — commands parsed but not executed",
                    "system",
                )

            return {
                "status": "executed" if executed else "parsed",
                "commands": [c.model_dump() for c in intent.commands],
                "confidence": intent.confidence,
                "clarification": intent.clarification_needed,
                "executed": executed,
            }
        except Exception as e:
            self.add_log("error", f"Parse failed: {e}", "nlp")
            return {"status": "error", "message": str(e)}

    async def _execute_command(self, cmd: MissionCommand) -> dict:
        """Dispatch a parsed command to the orchestrator → swarm pipeline."""
        mt = cmd.mission_type

        if mt == MissionType.LAND:
            self._swarm.command_land()
            drone_ids = cmd.assignment.drone_ids or [d.id for d in self._swarm.drones]
            self.add_log("info", f"LAND: drones {drone_ids}", "executor")
            return {"type": "land", "drones": drone_ids}

        if mt == MissionType.RETURN_TO_HOME:
            self._swarm.command_land()
            drone_ids = cmd.assignment.drone_ids or [d.id for d in self._swarm.drones]
            self.add_log("info", f"RTH: drones {drone_ids}", "executor")
            return {"type": "rth", "drones": drone_ids}

        if mt == MissionType.TAKEOFF:
            self._swarm.command_takeoff()
            drone_ids = cmd.assignment.drone_ids or [d.id for d in self._swarm.drones]
            self.add_log("info", f"TAKEOFF: drones {drone_ids}", "executor")
            return {"type": "takeoff", "drones": drone_ids}

        try:
            mission = await self._executor.execute_command(cmd)
            if mission:
                self.add_log(
                    "info",
                    f"Mission {mission.mission_id}: {mt.value} → "
                    f"drones {mission.assigned_drones}, "
                    f"{sum(len(w) for w in mission.waypoint_plans.values())} waypoints",
                    "executor",
                )
                return {
                    "type": mt.value,
                    "mission_id": mission.mission_id,
                    "drones": mission.assigned_drones,
                    "waypoints": sum(len(w) for w in mission.waypoint_plans.values()),
                }
            else:
                self.add_log("warning", f"No drones available for {mt.value}", "executor")
                return {"type": mt.value, "error": "no drones available"}
        except Exception as e:
            self.add_log("error", f"Execution failed: {e}", "executor")
            return {"type": mt.value, "error": str(e)}

    def sync_fleet_telemetry(self):
        """Push SwarmManager telemetry into FleetManager state."""
        if not self._swarm or not self._fleet:
            return
        for t in self._swarm.get_telemetry():
            drone_id = t["drone_id"]
            if not self._fleet.get_drone(drone_id):
                from drone_vla.orchestrator.fleet_manager import DroneStatus
                self._fleet.register_drone(drone_id, status=DroneStatus.ARMED)
            self._fleet.update_telemetry(
                drone_id,
                lat=t.get("lat", 0.0),
                lon=t.get("lon", 0.0),
                alt_m=t.get("alt_agl_m", 0.0),
                heading_deg=math.degrees(t.get("heading_rad", 0.0)),
                speed_ms=math.sqrt(t.get("vx", 0) ** 2 + t.get("vy", 0) ** 2),
            )

    def _get_fleet_state(self) -> dict:
        return {
            "drones": self.get_telemetry(),
            "swarm_state": self.get_swarm_state(),
        }

    def _sim_telemetry(self) -> list[dict]:
        t = time.time()
        drones = []
        for i in range(1, 4):
            alt = 15.0 + (i - 1) * 5.0
            angle = (t * 0.1 + i * 2.094)
            drones.append({
                "drone_id": i,
                "armed": True,
                "offboard": True,
                "x": 20.0 * math.cos(angle),
                "y": 20.0 * math.sin(angle),
                "z": -alt,
                "alt_agl_m": alt,
                "lat": 47.397742 + 0.0001 * math.cos(angle),
                "lon": 8.545594 + 0.0001 * math.sin(angle),
                "vx": -2.0 * math.sin(angle),
                "vy": 2.0 * math.cos(angle),
                "heading_rad": angle,
                "assigned_alt_m": alt,
                "task_active": True,
                "task_wp": f"{(int(t) % 5) + 1}/8",
            })
        return drones

    async def _broadcast(self, message: dict):
        dead = set()
        for ws in self._ws_clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self._ws_clients -= dead

    async def telemetry_loop(self):
        while True:
            self.sync_fleet_telemetry()
            data = {
                "type": "telemetry",
                "data": {
                    "drones": self.get_telemetry(),
                    "alerts": self.get_alerts(),
                    "swarm_state": self.get_swarm_state(),
                    "timestamp": time.time(),
                },
            }
            await self._broadcast(data)
            await asyncio.sleep(0.5)


bridge = SwarmBridge()


@app.on_event("startup")
async def startup():
    asyncio.create_task(bridge.telemetry_loop())
    try:
        parser = IntentParser(LLMConfig())
        bridge.set_intent_parser(parser)
        bridge.add_log("info", "NLP connected (Claude Haiku 4.5 via Bedrock)", "system")
    except Exception as e:
        bridge.add_log("warning", f"NLP init failed: {e}", "system")
    mode = "LIVE (PX4)" if bridge.is_live else "SIMULATED"
    bridge.add_log("info", f"Command Center online — {mode} mode", "system")


@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    bridge._ws_clients.add(ws)
    bridge.add_log("info", "Operator connected", "system")
    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") == "command":
                result = await bridge.process_command(data["text"])
                await ws.send_json({"type": "command_result", "data": result})
    except WebSocketDisconnect:
        bridge._ws_clients.discard(ws)
        bridge.add_log("info", "Operator disconnected", "system")


@app.get("/api/telemetry")
async def api_telemetry():
    return JSONResponse({
        "drones": bridge.get_telemetry(),
        "alerts": bridge.get_alerts(),
        "swarm_state": bridge.get_swarm_state(),
    })


@app.get("/api/logs")
async def api_logs(limit: int = 100):
    return JSONResponse(bridge._logs[-limit:])


@app.post("/api/command")
async def api_command(body: dict):
    result = await bridge.process_command(body.get("text", ""))
    return JSONResponse(result)


@app.get("/camera/{drone_id}")
async def camera_stream(drone_id: int):
    async def generate():
        while True:
            if bridge._camera:
                frame = bridge._camera.get_frame(drone_id)
                if frame:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                    )
            await asyncio.sleep(0.25)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/api/cameras")
async def api_cameras():
    if bridge._camera:
        return JSONResponse({"cameras": bridge._camera.get_active_cameras()})
    return JSONResponse({"cameras": []})


def run(host: str = "0.0.0.0", port: int = 8080):
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run()
