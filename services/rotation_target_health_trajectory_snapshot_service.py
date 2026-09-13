from __future__ import annotations

"""Resolve exact target-Health snapshots from an explicit raid-damage trajectory.

The underlying ``FightDamageTrajectoryProjection`` is already caller-evidence backed:
encounter maximum Health is canonical persisted guide data and every raid-DPS segment
is explicit. This service only integrates those supplied segments at one exact runtime
point. It never extends a finite final segment or invents damage through a gap.
"""

import math

from minmax.combat_state_snapshot import CombatStateSnapshot, CombatantSnapshot
from minmax.fight_damage_trajectory import FightDamageTrajectoryProjection


class RotationTargetHealthTrajectorySnapshotService:
    """Project one exact target Health snapshot from reviewed/caller-owned evidence."""

    def __init__(
        self,
        *,
        trajectory: FightDamageTrajectoryProjection,
        target_identity: str,
        player_identity: str = "rotation_player",
    ) -> None:
        target = str(target_identity or "").strip()
        player = str(player_identity or "").strip()
        if not target:
            raise ValueError("target Health trajectory requires a target identity")
        if not player:
            raise ValueError("target Health trajectory requires a player identity")
        self.trajectory = trajectory
        self.target_identity = target
        self.player_identity = player

    def snapshot_at(
        self,
        time_seconds: float,
        sequence: int | None = None,
    ) -> CombatStateSnapshot | None:
        del sequence
        time_value = float(time_seconds)
        if not math.isfinite(time_value) or time_value < 0.0:
            raise ValueError("target Health snapshot time must be finite and non-negative")

        damage = self._damage_at(time_value)
        if damage is None:
            return None

        maximum_health = float(self.trajectory.maximum_health)
        current_health = max(0.0, maximum_health - damage)
        return CombatStateSnapshot(
            time_seconds=time_value,
            player=CombatantSnapshot(identity=self.player_identity),
            targets=(
                CombatantSnapshot(
                    identity=self.target_identity,
                    current_health=current_health,
                    maximum_health=maximum_health,
                ),
            ),
        )

    def _damage_at(self, time_seconds: float) -> float | None:
        segments = tuple(self.trajectory.segments)
        if not segments:
            return None

        accumulated = 0.0
        for segment in segments:
            start = float(segment.start_seconds)
            end = None if segment.end_seconds is None else float(segment.end_seconds)

            if time_seconds < start - 1e-9:
                return None

            if end is None:
                accumulated += max(0.0, time_seconds - start) * float(
                    segment.damage_per_second
                )
                return accumulated

            if time_seconds <= end + 1e-9:
                elapsed = min(max(0.0, time_seconds - start), end - start)
                accumulated += elapsed * float(segment.damage_per_second)
                return accumulated

            accumulated += (end - start) * float(segment.damage_per_second)

        # All supplied segments were finite and the requested time lies beyond them.
        return None


__all__ = ["RotationTargetHealthTrajectorySnapshotService"]
