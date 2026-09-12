from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from minmax.rotation_plan import RotationAction, RotationActionKind
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateRoleOutputEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


_DAMAGE_ACTION_KINDS = {
    RotationActionKind.SKILL,
    RotationActionKind.LIGHT_ATTACK,
    RotationActionKind.HEAVY_ATTACK,
    RotationActionKind.ULTIMATE,
}


@dataclass(frozen=True)
class RotationActionDamageEvidence:
    """Canonical realized damage consequence for one exact scheduled action.

    Damage formulas, coefficient resolution, crit handling, mitigation, buffs,
    target state, periodic ticks, and proc consequences remain owned by the
    supplying combat evaluator. This record only identifies the scheduled action
    and carries its already-resolved total damage contribution to the whole plan.
    """

    time_seconds: float
    sequence: int
    damage_value: float | None
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        time_seconds = float(self.time_seconds)
        if not isfinite(time_seconds) or time_seconds < 0.0:
            raise ValueError("rotation action damage time must be finite and non-negative")
        object.__setattr__(self, "time_seconds", time_seconds)

        if self.sequence < 0:
            raise ValueError("rotation action damage sequence cannot be negative")

        if self.damage_value is not None:
            value = float(self.damage_value)
            if not isfinite(value) or value < 0.0:
                raise ValueError(
                    "rotation action damage value must be finite and non-negative"
                )
            object.__setattr__(self, "damage_value", value)

        object.__setattr__(
            self,
            "unresolved",
            tuple(str(item).strip() for item in self.unresolved if str(item).strip()),
        )


class RotationActionDamageEvidenceProvider(Protocol):
    """Resolve canonical damage consequence for one exact scheduled action."""

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence: ...


class RotationCandidateDDRoleOutputService:
    """Aggregate canonical per-action damage into whole-plan effective DPS.

    This service performs timeline aggregation only. It does not calculate ESO
    damage. Every scheduled skill, light attack, heavy attack, and Ultimate must be
    resolved by the supplied authoritative action-damage provider. If any required
    consequence is missing or unresolved, whole-plan DD output remains unknown.

    Periodic damage and proc damage must be included by the action owner that
    spawned them, within the selected plan horizon. The aggregator never guesses
    ticks from duration or manufactures proc schedules itself. Provider blockers are
    preserved verbatim but prefixed with exact scheduled-action identity so repeated
    casts cannot collapse into ambiguous whole-plan diagnostics.
    """

    def __init__(
        self,
        *,
        action_damage_evidence_provider: RotationActionDamageEvidenceProvider,
    ) -> None:
        self.action_damage_evidence_provider = action_damage_evidence_provider

    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationCandidateRoleOutputEvidence:
        plan = candidate.plan
        unresolved: list[str] = []
        total_damage = 0.0

        for action in plan.actions:
            if action.kind not in _DAMAGE_ACTION_KINDS:
                continue

            evidence = self.action_damage_evidence_provider.evaluate_action(
                candidate=candidate,
                action=action,
            )
            if (
                evidence.time_seconds != action.time_seconds
                or evidence.sequence != action.sequence
            ):
                raise ValueError(
                    "rotation action damage evidence mismatch: "
                    f"expected ({action.time_seconds:g}s, {action.sequence}), "
                    f"got ({evidence.time_seconds:g}s, {evidence.sequence})"
                )

            action_identity = self._action_identity(action)
            if evidence.unresolved:
                unresolved.extend(
                    f"{action_identity}: {message}" for message in evidence.unresolved
                )
            elif evidence.damage_value is None:
                unresolved.append(
                    f"{action_identity}: damage consequence unavailable"
                )
            else:
                total_damage += evidence.damage_value

        if plan.duration_seconds <= 0.0:
            unresolved.append("whole-plan DD output requires positive rotation duration")

        value = (
            total_damage / plan.duration_seconds
            if not unresolved and plan.duration_seconds > 0.0
            else None
        )
        return RotationCandidateRoleOutputEvidence(
            candidate_id=candidate.candidate_id,
            value=value,
            unresolved=tuple(unresolved),
        )

    @staticmethod
    def _action_identity(action: RotationAction) -> str:
        name = f" {action.name}" if action.name else ""
        return (
            f"{action.time_seconds:g}s #{action.sequence} "
            f"{action.kind.value}{name}"
        )


__all__ = [
    "RotationActionDamageEvidence",
    "RotationActionDamageEvidenceProvider",
    "RotationCandidateDDRoleOutputService",
]
