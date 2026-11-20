"""Pydantic models for mission schemas — the structured output contract between LLM and orchestrator."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MissionType(str, Enum):
    AREA_SEARCH = "area_search"
    PERIMETER_PATROL = "perimeter_patrol"
    FORMATION_FLIGHT = "formation_flight"
    POINT_INSPECTION = "point_inspection"
    RELAY_STATION = "relay_station"
    RETURN_TO_HOME = "return_to_home"
    TAKEOFF = "takeoff"
    LAND = "land"


class FormationType(str, Enum):
    LINE = "line"
    TRIANGLE = "triangle"
    DIAMOND = "diamond"
    CIRCLE = "circle"
    V_SHAPE = "v_shape"
    GRID = "grid"


class SensorMode(str, Enum):
    RGB = "rgb"
    THERMAL = "thermal"
    THERMAL_RGB_FUSED = "thermal_rgb_fused"
    MULTISPECTRAL = "multispectral"


class ContingencyAction(str, Enum):
    AUTO_RTH = "auto_rth"
    LOITER_IN_PLACE = "loiter_in_place"
    LAND_IMMEDIATELY = "land_immediately"
    CONTINUE_MISSION = "continue_mission"


class GeoPoint(BaseModel):
    lat: float = Field(description="Latitude in decimal degrees")
    lon: float = Field(description="Longitude in decimal degrees")


class DroneAssignment(BaseModel):
    drone_ids: list[int] = Field(
        default_factory=list,
        description="Specific drone IDs to assign. Empty means auto-assign.",
    )
    group_name: Optional[str] = Field(
        default=None,
        description="Named group reference (e.g. 'Alpha', 'Swarm 1')",
    )


class MissionCommand(BaseModel):
    """Top-level structured command produced by the intent parser."""

    mission_type: MissionType
    assignment: DroneAssignment = Field(default_factory=DroneAssignment)

    search_polygon: Optional[list[GeoPoint]] = None
    perimeter_polygon: Optional[list[GeoPoint]] = None
    center_point: Optional[GeoPoint] = None
    target_point: Optional[GeoPoint] = None
    station_points: Optional[list[GeoPoint]] = None

    altitude_agl_m: Optional[float] = Field(default=None, ge=0.0, le=500.0)
    speed_ms: Optional[float] = Field(default=None, ge=0.5, le=30.0)

    formation_type: Optional[FormationType] = None
    spacing_m: Optional[float] = Field(default=None, ge=1.0, le=100.0)
    heading_deg: Optional[float] = Field(default=None, ge=0.0, le=360.0)

    orbit_radius_m: Optional[float] = Field(default=None, ge=5.0, le=500.0)
    direction: Optional[str] = Field(default=None, pattern="^(clockwise|counterclockwise)$")

    sensor_mode: Optional[SensorMode] = None
    target_classes: Optional[list[str]] = None
    overlap_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)

    duration_s: Optional[float] = Field(default=None, ge=0.0)
    contingency: ContingencyAction = ContingencyAction.AUTO_RTH

    raw_intent: str = Field(
        default="",
        description="Original natural language command for audit trail",
    )


class ParsedIntent(BaseModel):
    """Wrapper returned by the intent parser with confidence metadata."""

    commands: list[MissionCommand] = Field(
        description="One or more commands extracted from a single utterance"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Parser confidence 0-1")
    clarification_needed: Optional[str] = Field(
        default=None,
        description="If set, the parser needs the operator to clarify something",
    )
