"""Tests for fleet manager allocation and failover."""

from drone_vla.config import FleetConfig
from drone_vla.nlp.schemas import DroneAssignment, MissionCommand, MissionType
from drone_vla.orchestrator.fleet_manager import DroneStatus, FleetManager


def _make_fleet(n: int = 5) -> FleetManager:
    config = FleetConfig(max_drones=n, min_battery_pct=20, failover_enabled=True)
    fm = FleetManager(config)
    for i in range(1, n + 1):
        fm.register_drone(i, status=DroneStatus.IDLE, battery_pct=100.0 - i * 5)
    return fm


def test_register_and_list():
    fm = _make_fleet(3)
    assert len(fm.all_drones) == 3
    assert len(fm.available_drones) == 3


def test_allocate_auto():
    fm = _make_fleet(5)
    cmd = MissionCommand(mission_type=MissionType.AREA_SEARCH, altitude_agl_m=20.0)
    drones = fm.allocate_drones(cmd)
    assert len(drones) == 3
    assert drones[0].battery_pct >= drones[1].battery_pct


def test_allocate_specific():
    fm = _make_fleet(5)
    cmd = MissionCommand(
        mission_type=MissionType.FORMATION_FLIGHT,
        assignment=DroneAssignment(drone_ids=[2, 4]),
        altitude_agl_m=20.0,
    )
    drones = fm.allocate_drones(cmd)
    assert [d.drone_id for d in drones] == [2, 4]


def test_allocate_unavailable_filtered():
    fm = _make_fleet(3)
    fm.get_drone(2).status = DroneStatus.IN_MISSION
    cmd = MissionCommand(
        mission_type=MissionType.FORMATION_FLIGHT,
        assignment=DroneAssignment(drone_ids=[1, 2, 3]),
        altitude_agl_m=20.0,
    )
    drones = fm.allocate_drones(cmd)
    assert 2 not in [d.drone_id for d in drones]


def test_failover():
    fm = _make_fleet(5)
    cmd = MissionCommand(mission_type=MissionType.AREA_SEARCH, altitude_agl_m=20.0)
    allocated = fm.allocate_drones(cmd)
    failed_id = allocated[0].drone_id

    backup = fm.handle_failover(failed_id)
    assert backup is not None
    assert backup.drone_id != failed_id
    assert fm.get_drone(failed_id).status == DroneStatus.ERROR


def test_failover_no_backup():
    fm = _make_fleet(3)
    for d in fm.all_drones:
        d.status = DroneStatus.IN_MISSION
        d.current_mission_id = "M0001"

    fm.get_drone(1).battery_pct = 5.0
    backup = fm.handle_failover(1)
    assert backup is None


def test_battery_warnings():
    fm = _make_fleet(3)
    fm.get_drone(1).status = DroneStatus.IN_MISSION
    fm.get_drone(1).battery_pct = 15.0
    fm.get_drone(2).status = DroneStatus.IN_MISSION
    fm.get_drone(2).battery_pct = 50.0

    low = fm.check_battery_warnings()
    assert len(low) == 1
    assert low[0].drone_id == 1


def test_fleet_state_summary():
    fm = _make_fleet(3)
    summary = fm.get_fleet_state_summary()
    assert summary["total"] == 3
    assert summary["available"] == 3
    assert len(summary["drones"]) == 3
