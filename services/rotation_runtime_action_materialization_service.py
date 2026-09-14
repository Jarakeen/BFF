from __future__ import annotations

"""Materialize one proven runtime execution choice into an immutable RotationPlan.

Every upstream boundary must already have proved trigger timing, canonical capability,
active-bar availability, slot legality, target legality, and occupancy legality. This
service owns only deterministic action insertion. It does not re-resolve strategy,
invent a BAR_SWAP, move the activation time, or choose among multiple candidates.
"""

from dataclasses import dataclass

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_runtime_executable_choice_service import (
    RotationRuntimeExecutableChoice,
)


@dataclass(frozen=True)
class RotationRuntimeActionMaterialization:
    """Result of inserting, or recognizing, one proven runtime skill action."""

    plan: RotationPlan
    action: RotationAction
    inserted: bool


class RotationRuntimeActionMaterializationService:
    """Insert exactly one already-proven runtime SKILL action at activation time."""

    def materialize(
        self,
        *,
        plan: RotationPlan,
        choice: RotationRuntimeExecutableChoice,
    ) -> RotationRuntimeActionMaterialization:
        if not isinstance(plan, RotationPlan):
            raise TypeError("runtime action materialization requires RotationPlan")
        if not isinstance(choice, RotationRuntimeExecutableChoice):
            raise TypeError(
                "runtime action materialization requires RotationRuntimeExecutableChoice"
            )

        candidate = choice.candidate
        activation_time = float(candidate.activated_at_seconds)
        if activation_time > plan.duration_seconds:
            raise ValueError(
                "runtime executable choice activates after the deterministic plan duration"
            )

        existing = self._matching_existing_action(
            plan=plan,
            time_seconds=activation_time,
            skill_name=candidate.skill_name,
            bar=candidate.bar,
            target_key=candidate.target_key,
        )
        if existing is not None:
            return RotationRuntimeActionMaterialization(
                plan=plan,
                action=existing,
                inserted=False,
            )

        sequence = self._next_sequence(plan, activation_time)
        action = RotationAction(
            time_seconds=activation_time,
            sequence=sequence,
            kind=RotationActionKind.SKILL,
            name=candidate.skill_name,
            bar=candidate.bar,
            target_key=candidate.target_key,
        )
        materialized = RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=(*plan.actions, action),
            assumptions=plan.assumptions,
            unresolved=plan.unresolved,
        )
        return RotationRuntimeActionMaterialization(
            plan=materialized,
            action=action,
            inserted=True,
        )

    @staticmethod
    def _next_sequence(plan: RotationPlan, time_seconds: float) -> int:
        return max(
            (
                int(action.sequence)
                for action in plan.actions
                if abs(float(action.time_seconds) - float(time_seconds)) <= 1e-12
            ),
            default=-1,
        ) + 1

    @staticmethod
    def _matching_existing_action(
        *,
        plan: RotationPlan,
        time_seconds: float,
        skill_name: str,
        bar: str,
        target_key: str | None,
    ) -> RotationAction | None:
        wanted_name = str(skill_name).casefold()
        wanted_target = None if target_key is None else str(target_key).casefold()
        matches = tuple(
            action
            for action in plan.actions
            if abs(float(action.time_seconds) - float(time_seconds)) <= 1e-12
            and action.kind is RotationActionKind.SKILL
            and action.name is not None
            and action.name.casefold() == wanted_name
            and action.bar == bar
            and (
                None if action.target_key is None else action.target_key.casefold()
            )
            == wanted_target
        )
        if len(matches) > 1:
            raise ValueError(
                "deterministic plan already contains duplicate matching runtime actions"
            )
        return matches[0] if matches else None


__all__ = [
    "RotationRuntimeActionMaterialization",
    "RotationRuntimeActionMaterializationService",
]
