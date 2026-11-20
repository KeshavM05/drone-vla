"""Command Center backend — FastAPI + WebSocket telemetry bridge."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Drone VLA Command Center")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class SwarmBridge:
    """Bridges the ROS2 SwarmManager to the web layer.

    When ROS2 is running, call set_swarm_manager() to connect live data.
    Otherwise serves simulated telemetry for UI development.
    """

    def __init__(self):
        self._swarm = None
        self._intent_parser = None
        self._logs: list[dict] = []
        self._max_logs = 500
        self._ws_clients: set[WebSocket] = set()

    def set_swarm_manager(self, swarm):
        self._swarm = swarm

    def set_intent_parser(self, parser):
        self._intent_parser = parser

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

        if self._intent_parser:
            try:
                intent = await self._intent_parser.aparse(
                    text, self._get_fleet_state()
                )
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
                return {
                    "status": "parsed",
                    "commands": [c.model_dump() for c in intent.commands],
                    "confidence": intent.confidence,
                    "clarification": intent.clarification_needed,
                }
            except Exception as e:
                self.add_log("error", f"Parse failed: {e}", "nlp")
                return {"status": "error", "message": str(e)}
        else:
            self.add_log("warning", "NLP not connected — command logged only", "system")
            return {"status": "no_nlp", "message": "Intent parser not available"}

    def _get_fleet_state(self) -> dict:
        return {
            "drones": self.get_telemetry(),
            "swarm_state": self.get_swarm_state(),
        }

    def _sim_telemetry(self) -> list[dict]:
        t = time.time()
        import math
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
    bridge.add_log("info", "Command Center online", "system")


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


def run(host: str = "0.0.0.0", port: int = 8080):
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run()
