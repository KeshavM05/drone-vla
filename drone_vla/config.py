from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel


class STTConfig(BaseModel):
    model_size: str = "base.en"
    language: str = "en"
    device: str = "auto"
    vad_filter: bool = True
    beam_size: int = 5


class LLMConfig(BaseModel):
    provider: str = "bedrock"
    region: str = "us-east-1"
    model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    max_tokens: int = 2048
    temperature: float = 0.0


class CollisionAvoidanceConfig(BaseModel):
    altitude_base_m: float = 15.0
    altitude_layer_m: float = 5.0
    warning_distance_m: float = 10.0
    critical_distance_m: float = 5.0
    repulsive_gain: float = 3.0
    max_repulsive_offset_m: float = 8.0


class FleetConfig(BaseModel):
    max_drones: int = 5
    default_altitude_m: float = 20.0
    min_battery_pct: int = 20
    failover_enabled: bool = True
    deconfliction_buffer_m: float = 5.0
    collision_avoidance: CollisionAvoidanceConfig = CollisionAvoidanceConfig()


class SimulationConfig(BaseModel):
    sitl_instances: int = 3
    start_port: int = 14550
    home_lat: float = 47.397742
    home_lon: float = 8.545594
    home_alt: float = 488.0
    camera_model: str = "x500_mono_cam_45"


class ROS2Config(BaseModel):
    enabled: bool = True
    namespace: str = "/drone_vla"
    qos_depth: int = 10


class AppConfig(BaseModel):
    stt: STTConfig = STTConfig()
    llm: LLMConfig = LLMConfig()
    fleet: FleetConfig = FleetConfig()
    simulation: SimulationConfig = SimulationConfig()
    ros2: ROS2Config = ROS2Config()


def load_config(path: str | Path | None = None) -> AppConfig:
    if path is None:
        path = Path(__file__).parents[2] / "config" / "default.yaml"
    path = Path(path)

    if path.exists():
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        return AppConfig(**raw)

    return AppConfig()
