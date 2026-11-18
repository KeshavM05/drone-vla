"""Tests for mission schema validation."""

import pytest
from pydantic import ValidationError

from drone_vla.nlp.schemas import (
    ContingencyAction,
    DroneAssignment,
    FormationType,
    GeoPoint,
    MissionCommand,
    MissionType,
    ParsedIntent,
    SensorMode,
)


def test_basic_takeoff_command():
    cmd = MissionCommand(
        mission_type=MissionType.TAKEOFF,
        altitude_agl_m=20.0,
        raw_intent="take off to 20 meters",
    )
    assert cmd.mission_type == MissionType.TAKEOFF
    assert cmd.altitude_agl_m == 20.0
    assert cmd.contingency == ContingencyAction.AUTO_RTH


def test_area_search_command():
    polygon = [
        GeoPoint(lat=47.397, lon=8.545),
        GeoPoint(lat=47.398, lon=8.545),
        GeoPoint(lat=47.398, lon=8.546),
        GeoPoint(lat=47.397, lon=8.546),
    ]
    cmd = MissionCommand(
        mission_type=MissionType.AREA_SEARCH,
        search_polygon=polygon,
        altitude_agl_m=40.0,
        sensor_mode=SensorMode.THERMAL_RGB_FUSED,
        target_classes=["person", "heat_signature"],
    )
    assert len(cmd.search_polygon) == 4
    assert cmd.sensor_mode == SensorMode.THERMAL_RGB_FUSED


def test_formation_command():
    cmd = MissionCommand(
        mission_type=MissionType.FORMATION_FLIGHT,
        center_point=GeoPoint(lat=47.397, lon=8.545),
        formation_type=FormationType.TRIANGLE,
        spacing_m=15.0,
        altitude_agl_m=25.0,
        assignment=DroneAssignment(drone_ids=[1, 2, 3]),
    )
    assert cmd.formation_type == FormationType.TRIANGLE
    assert cmd.assignment.drone_ids == [1, 2, 3]


def test_parsed_intent_multi_command():
    intent = ParsedIntent(
        commands=[
            MissionCommand(mission_type=MissionType.TAKEOFF, altitude_agl_m=20.0),
            MissionCommand(
                mission_type=MissionType.FORMATION_FLIGHT,
                formation_type=FormationType.LINE,
                center_point=GeoPoint(lat=47.0, lon=8.0),
                altitude_agl_m=20.0,
            ),
        ],
        confidence=0.95,
    )
    assert len(intent.commands) == 2
    assert intent.confidence == 0.95
    assert intent.clarification_needed is None


def test_altitude_validation():
    with pytest.raises(ValidationError):
        MissionCommand(mission_type=MissionType.TAKEOFF, altitude_agl_m=-5.0)

    with pytest.raises(ValidationError):
        MissionCommand(mission_type=MissionType.TAKEOFF, altitude_agl_m=600.0)


def test_json_round_trip():
    cmd = MissionCommand(
        mission_type=MissionType.PERIMETER_PATROL,
        perimeter_polygon=[
            GeoPoint(lat=47.0, lon=8.0),
            GeoPoint(lat=47.1, lon=8.0),
            GeoPoint(lat=47.1, lon=8.1),
        ],
        altitude_agl_m=30.0,
        direction="clockwise",
    )
    json_str = cmd.model_dump_json()
    restored = MissionCommand.model_validate_json(json_str)
    assert restored.mission_type == cmd.mission_type
    assert len(restored.perimeter_polygon) == 3
