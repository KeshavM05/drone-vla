"""Collision avoidance for multi-drone swarm.

Three layers:
1. Altitude deconfliction — each drone assigned a unique altitude layer
2. Separation monitoring — pairwise distance checks at every tick
3. Reactive avoidance — repulsive offset when drones breach critical distance
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from drone_vla.flight.px4_drone import PX4Drone

logger = logging.getLogger(__name__)


@dataclass
class CAConfig:
    altitude_base_m: float = 15.0
    altitude_layer_m: float = 5.0
    warning_distance_m: float = 10.0
    critical_distance_m: float = 5.0
    repulsive_gain: float = 3.0
    max_repulsive_offset_m: float = 8.0
    check_rate_hz: float = 10.0


@dataclass
class ProximityAlert:
    drone_a: int
    drone_b: int
    distance_m: float
    is_critical: bool


class CollisionAvoidance:
    def __init__(self, config: CAConfig | None = None):
        self.config = config or CAConfig()
        self._alerts: list[ProximityAlert] = []
        self._avoidance_active: dict[int, tuple[float, float, float]] = {}

    def assigned_altitude_ned(self, drone_id: int) -> float:
        alt_agl = self.config.altitude_base_m + (drone_id - 1) * self.config.altitude_layer_m
        return -alt_agl

    def deconflict_target(
        self, drone_id: int, x: float, y: float, z: float
    ) -> tuple[float, float, float]:
        enforced_z = self.assigned_altitude_ned(drone_id)
        return (x, y, enforced_z)

    def check_separations(self, drones: list[PX4Drone]) -> list[ProximityAlert]:
        self._alerts.clear()
        self._avoidance_active.clear()
        n = len(drones)

        for i in range(n):
            for j in range(i + 1, n):
                dist = drones[i].distance_to(drones[j])
                if dist < self.config.warning_distance_m:
                    is_critical = dist < self.config.critical_distance_m
                    alert = ProximityAlert(
                        drone_a=drones[i].id,
                        drone_b=drones[j].id,
                        distance_m=dist,
                        is_critical=is_critical,
                    )
                    self._alerts.append(alert)

                    if is_critical:
                        logger.warning(
                            "CRITICAL: Drone %d and %d at %.1fm — applying avoidance",
                            drones[i].id, drones[j].id, dist,
                        )
                        self._compute_avoidance(drones[i], drones[j])
                    else:
                        logger.info(
                            "Warning: Drone %d and %d at %.1fm (< %.0fm)",
                            drones[i].id, drones[j].id, dist,
                            self.config.warning_distance_m,
                        )

        return self._alerts

    def _compute_avoidance(self, a: PX4Drone, b: PX4Drone):
        dx = a.pos.x - b.pos.x
        dy = a.pos.y - b.pos.y
        dist_h = math.sqrt(dx * dx + dy * dy)

        if dist_h < 0.01:
            dx, dy = 1.0, 0.0
            dist_h = 1.0

        nx = dx / dist_h
        ny = dy / dist_h

        scale = self.config.repulsive_gain * (
            1.0 - dist_h / self.config.critical_distance_m
        )
        scale = max(0.0, min(scale, self.config.max_repulsive_offset_m))

        self._avoidance_active[a.id] = (nx * scale, ny * scale, 0.0)
        self._avoidance_active[b.id] = (-nx * scale, -ny * scale, 0.0)

    def get_avoidance_offset(self, drone_id: int) -> tuple[float, float, float]:
        return self._avoidance_active.get(drone_id, (0.0, 0.0, 0.0))

    def apply_avoidance_to_target(
        self, drone_id: int, x: float, y: float, z: float
    ) -> tuple[float, float, float]:
        ox, oy, oz = self.get_avoidance_offset(drone_id)
        return (x + ox, y + oy, z + oz)

    def is_waypoint_safe(
        self, x: float, y: float, z: float, drones: list[PX4Drone], exclude_id: int
    ) -> bool:
        for d in drones:
            if d.id == exclude_id or not d.pos.valid:
                continue
            dist = d.distance_to_point(x, y, z)
            if dist < self.config.critical_distance_m:
                return False
        return True

    @property
    def alerts(self) -> list[ProximityAlert]:
        return list(self._alerts)

    @property
    def has_critical(self) -> bool:
        return any(a.is_critical for a in self._alerts)
