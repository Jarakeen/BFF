from __future__ import annotations

"""Aggregate proof-safe per-action damage ceilings into one rotation DPS ceiling.

This service owns arithmetic only. It does not calculate ESO damage, infer skill
coefficients, invent proc schedules, or guess DoT cadence. Callers must provide one
proven optimistic total-damage ceiling for every damage-bearing scheduled action,
including all periodic/triggered consequences attributable to that action within the
plan horizon.
"""

from dataclasses import dataclass
from math import isfinite

from minmax.rotation_plan import RotationAction, RotationPlan
from services.rotation_candidate_dd_role_output_service import DD_DAMAGE_ACTION_KINDS


@dataclass(frozen=True)
class ExtremeSustainedDPSActionUpperBound:
    time_seconds: float
    sequence: int
    upper_bound_damage: float | None
    proven_safe: bool
    covers_periodic_and_triggered: bool
    source: str
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        time_seconds = float(self.time_seconds)
        if not isfinite(time_seconds) or time_seconds < 0.0:
            raise ValueError("action upper-bound time must be finite and non-negative")
        if int(self.sequence) < 0:
            raise ValueError("action upper-bound sequence cannot be negative")
        object.__setattr__(self, "time_seconds", time_seconds)
        object.__setattr__(self, "sequence", int(self.sequence))

        if self.upper_bound_damage is not None:
            value = float(self.upper_bound_damage)
            if not isfinite(value) or value < 0.0:
                raise ValueError(
                    "action upper-bound damage must be finite and non-negative"
                )
            object.__setattr__(self, "upper_bound_damage", value)

        object.__setattr__(self, "source", str(self.source or "").strip())
        object.__setattr__(
            self,
            "unresolved",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.unresolved
                    if str(item).strip()
                )
            ),
        )

    @property
    def coordinate(self) -> tuple[float, int]:
        return (self.time_seconds, self.sequence)


@dataclass(frozen=True)
class ExtremeSustainedDPSRotationUpperBound:
    duration_seconds: float
    upper_bound_damage: float | None
    upper_bound_dps: float | None
    damage_action_count: int
    covered_action_count: int
    proven_safe: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSRotationUpperBoundService:
    """Build a proof-safe whole-plan ceiling from externally supplied action bounds."""

    @classmethod
    def evaluate(
        cls,
        plan: RotationPlan,
        *,
        action_bounds: tuple[ExtremeSustainedDPSActionUpperBound, ...],
    ) -> ExtremeSustainedDPSRotationUpperBound:
        duration = float(plan.duration_seconds)
        if not isfinite(duration) or duration <= 0.0:
            raise ValueError("rotation upper-bound plan duration must be positive and finite")

        damage_actions = tuple(
            action
            for action in plan.actions
            if action.kind in DD_DAMAGE_ACTION_KINDS
        )
        action_by_coordinate = {
            (float(action.time_seconds), int(action.sequence)): action
            for action in damage_actions
        }
        if len(action_by_coordinate) != len(damage_actions):
            raise ValueError(
                "rotation upper-bound plan contains duplicate damage-action coordinates"
            )

        supplied: dict[tuple[float, int], ExtremeSustainedDPSActionUpperBound] = {}
        unresolved: list[str] = []
        for bound in tuple(action_bounds):
            coordinate = bound.coordinate
            if coordinate in supplied:
                raise ValueError(
                    "duplicate sustained-DPS action upper bound at "
                    f"{coordinate[0]:g}s sequence {coordinate[1]}"
                )
            supplied[coordinate] = bound
            if coordinate not in action_by_coordinate:
                unresolved.append(
                    "Upper-bound evidence does not match a damage-bearing scheduled action: "
                    f"{coordinate[0]:g}s sequence {coordinate[1]}"
                )

        total = 0.0
        covered = 0
        for coordinate, action in action_by_coordinate.items():
            bound = supplied.get(coordinate)
            label = cls._action_label(action)
            if bound is None:
                unresolved.append(f"{label}: optimistic damage upper bound is missing")
                continue
            if bound.upper_bound_damage is None:
                unresolved.append(f"{label}: optimistic damage upper bound is unresolved")
                unresolved.extend(f"{label}: {item}" for item in bound.unresolved)
                continue
            if not bound.proven_safe:
                unresolved.append(f"{label}: optimistic damage upper bound is not proven safe")
                unresolved.extend(f"{label}: {item}" for item in bound.unresolved)
                continue
            if not bound.covers_periodic_and_triggered:
                unresolved.append(
                    f"{label}: upper bound does not cover all periodic/triggered consequences"
                )
                unresolved.extend(f"{label}: {item}" for item in bound.unresolved)
                continue
            total += float(bound.upper_bound_damage)
            covered += 1

        deduped_unresolved = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in unresolved
                if str(item).strip()
            )
        )
        proven = (
            covered == len(damage_actions)
            and len(supplied) == len(damage_actions)
            and not deduped_unresolved
        )

        upper_damage = total if proven else None
        upper_dps = (total / duration) if proven else None
        evidence = (
            f"Rotation duration: {duration:g}s",
            f"Damage-bearing scheduled actions: {len(damage_actions)}",
            f"Fully covered action ceilings: {covered}",
            "Whole-plan ceiling sums only externally proven per-action optimistic totals",
            "Each accepted action ceiling must include direct, periodic, and triggered consequences within the plan horizon",
        )
        return ExtremeSustainedDPSRotationUpperBound(
            duration_seconds=duration,
            upper_bound_damage=upper_damage,
            upper_bound_dps=upper_dps,
            damage_action_count=len(damage_actions),
            covered_action_count=covered,
            proven_safe=proven,
            evidence=evidence,
            unresolved=deduped_unresolved,
        )

    @staticmethod
    def _action_label(action: RotationAction) -> str:
        name = str(action.name or action.kind.value or "action").strip()
        return f"{name} at {float(action.time_seconds):g}s sequence {int(action.sequence)}"


__all__ = [
    "ExtremeSustainedDPSActionUpperBound",
    "ExtremeSustainedDPSRotationUpperBound",
    "ExtremeSustainedDPSRotationUpperBoundService",
]
