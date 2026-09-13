from __future__ import annotations

"""Caller-owned target Health observations for runtime rotation decisions.

The timeline never invents interpolation.  An observation is exact at its timestamp
unless the caller explicitly supplies ``valid_until_seconds`` as evidence that the
same Health fact remains valid through that interval.  Gaps resolve to ``None``.
"""

from dataclasses import dataclass
import math

from minmax.combat_state_snapshot import CombatantSnapshot, CombatStateSnapshot


@dataclass(frozen=True)
class RotationTargetHealthObservation:
    time_seconds: float
    target_identity: str
    current_health: float
    maximum_health: float
    valid_until_seconds: float | None = None
    evidence: str = ""

    def __post_init__(self) -> None:
        if not math.isfinite(self.time_seconds) or self.time_seconds < 0:
            raise ValueError("target Health observation time must be finite and non-negative")
        target = str(self.target_identity or "").strip()
        if not target:
            raise ValueError("target Health observation requires target_identity")
        if not math.isfinite(self.current_health) or self.current_health < 0:
            raise ValueError("current Health must be finite and non-negative")
        if not math.isfinite(self.maximum_health) or self.maximum_health <= 0:
            raise ValueError("maximum Health must be finite and positive")
        if self.current_health > self.maximum_health:
            raise ValueError("current Health cannot exceed maximum Health")
        if self.valid_until_seconds is not None:
            if not math.isfinite(self.valid_until_seconds):
                raise ValueError("target Health validity end must be finite")
            if self.valid_until_seconds < self.time_seconds:
                raise ValueError("target Health validity end cannot precede observation time")
        object.__setattr__(self, "target_identity", target)
        object.__setattr__(self, "evidence", str(self.evidence or "").strip())

    @property
    def health_fraction(self) -> float:
        return float(self.current_health) / float(self.maximum_health)

    def covers(self, time_seconds: float, *, tolerance: float = 1e-9) -> bool:
        time = float(time_seconds)
        if abs(time - float(self.time_seconds)) <= tolerance:
            return True
        if self.valid_until_seconds is None:
            return False
        return (
            time >= float(self.time_seconds) - tolerance
            and time <= float(self.valid_until_seconds) + tolerance
        )


@dataclass(frozen=True)
class RotationTargetHealthTimeline:
    target_identity: str
    observations: tuple[RotationTargetHealthObservation, ...]

    def __post_init__(self) -> None:
        target = str(self.target_identity or "").strip()
        if not target:
            raise ValueError("target Health timeline requires target_identity")
        ordered = tuple(sorted(self.observations, key=lambda row: row.time_seconds))
        for row in ordered:
            if row.target_identity != target:
                raise ValueError("all target Health observations must use the timeline target identity")
        for left, right in zip(ordered, ordered[1:]):
            left_end = (
                float(left.valid_until_seconds)
                if left.valid_until_seconds is not None
                else float(left.time_seconds)
            )
            if left_end > float(right.time_seconds) + 1e-9:
                raise ValueError("target Health observation validity intervals must not overlap")
        object.__setattr__(self, "target_identity", target)
        object.__setattr__(self, "observations", ordered)


class RotationTargetHealthTimelineService:
    """Resolve exact/caller-bounded Health observations into combat snapshots."""

    def snapshot_resolver(
        self,
        timeline: RotationTargetHealthTimeline,
        *,
        player_identity: str = "rotation_player",
    ):
        player = str(player_identity or "").strip()
        if not player:
            raise ValueError("player identity is required for target Health snapshots")

        def resolve(time_seconds: float) -> CombatStateSnapshot | None:
            matches = tuple(
                row for row in timeline.observations if row.covers(float(time_seconds))
            )
            if len(matches) != 1:
                return None
            row = matches[0]
            return CombatStateSnapshot(
                time_seconds=float(time_seconds),
                player=CombatantSnapshot(identity=player),
                targets=(
                    CombatantSnapshot(
                        identity=timeline.target_identity,
                        current_health=float(row.current_health),
                        maximum_health=float(row.maximum_health),
                    ),
                ),
            )

        return resolve


__all__ = [
    "RotationTargetHealthObservation",
    "RotationTargetHealthTimeline",
    "RotationTargetHealthTimelineService",
]
