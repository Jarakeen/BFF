from __future__ import annotations

"""Compare one proven execute opportunity through canonical action damage evidence.

This service owns no ESO damage formulas and does not infer that an active execute
is automatically superior. It locates the exact scheduled filler action, evaluates
that action and a same-slot execute substitute through the supplied canonical action
damage provider, and recommends replacement only when both values resolve and the
execute produces strictly greater damage.
"""

from dataclasses import dataclass

from minmax.rotation_plan import RotationAction, RotationActionKind
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageEvidenceProvider,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_execute_filler_opportunity_service import (
    RotationExecuteFillerOpportunity,
)


@dataclass(frozen=True)
class RotationExecuteFillerDamageComparison:
    opportunity: RotationExecuteFillerOpportunity
    current_damage: float | None
    execute_damage: float | None
    replace_with_execute: bool
    unresolved: tuple[str, ...] = ()


class RotationExecuteFillerDamageComparisonService:
    """Recommend execute replacement only from resolved canonical damage evidence."""

    def __init__(
        self,
        *,
        action_damage_provider: RotationActionDamageEvidenceProvider,
    ) -> None:
        self.action_damage_provider = action_damage_provider

    def compare(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        opportunity: RotationExecuteFillerOpportunity,
    ) -> RotationExecuteFillerDamageComparison:
        matches = tuple(
            action
            for action in candidate.plan.actions
            if action.kind is RotationActionKind.SKILL
            and action.name
            and action.name.casefold() == opportunity.current_skill_name.casefold()
            and action.bar == opportunity.bar
            and abs(float(action.time_seconds) - float(opportunity.time_seconds)) <= 1e-9
        )
        if len(matches) != 1:
            return RotationExecuteFillerDamageComparison(
                opportunity=opportunity,
                current_damage=None,
                execute_damage=None,
                replace_with_execute=False,
                unresolved=(
                    "execute comparison expected one exact scheduled filler action at "
                    f"{opportunity.time_seconds:g}s on {opportunity.bar} bar; found {len(matches)}",
                ),
            )

        current_action = matches[0]
        execute_action = RotationAction(
            time_seconds=current_action.time_seconds,
            sequence=current_action.sequence,
            kind=RotationActionKind.SKILL,
            name=opportunity.execute_skill_name,
            bar=current_action.bar,
        )
        current = self.action_damage_provider.evaluate_action(
            candidate=candidate,
            action=current_action,
        )
        execute = self.action_damage_provider.evaluate_action(
            candidate=candidate,
            action=execute_action,
        )

        unresolved: list[str] = []
        if current.unresolved:
            unresolved.extend(
                f"current filler {opportunity.current_skill_name!r}: {message}"
                for message in current.unresolved
            )
        elif current.damage_value is None:
            unresolved.append(
                f"current filler {opportunity.current_skill_name!r}: damage consequence unavailable"
            )

        if execute.unresolved:
            unresolved.extend(
                f"execute {opportunity.execute_skill_name!r}: {message}"
                for message in execute.unresolved
            )
        elif execute.damage_value is None:
            unresolved.append(
                f"execute {opportunity.execute_skill_name!r}: damage consequence unavailable"
            )

        if unresolved:
            return RotationExecuteFillerDamageComparison(
                opportunity=opportunity,
                current_damage=current.damage_value,
                execute_damage=execute.damage_value,
                replace_with_execute=False,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        current_damage = float(current.damage_value)
        execute_damage = float(execute.damage_value)
        return RotationExecuteFillerDamageComparison(
            opportunity=opportunity,
            current_damage=current_damage,
            execute_damage=execute_damage,
            replace_with_execute=execute_damage > current_damage,
        )


__all__ = [
    "RotationExecuteFillerDamageComparison",
    "RotationExecuteFillerDamageComparisonService",
]
