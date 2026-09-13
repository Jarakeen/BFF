from __future__ import annotations

"""Apply only canonically proven execute upgrades to ordinary filler slots.

This service owns no execute mechanics and no damage formulas. Opportunities are
produced by the execute opportunity layer and damage values by the canonical action
damage comparison layer. Mutation happens only when a comparison resolves and proves
strictly greater execute damage.

When multiple execute candidates compete for one exact filler slot, the greatest
resolved execute damage wins. Equal best damage from different executes is left
unresolved rather than inventing a hidden tie-break preference.
"""

from dataclasses import dataclass, replace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_execute_filler_damage_comparison_service import (
    RotationExecuteFillerDamageComparison,
    RotationExecuteFillerDamageComparisonService,
)
from services.rotation_execute_filler_opportunity_service import (
    RotationExecuteFillerOpportunity,
)


@dataclass(frozen=True)
class RotationExecuteFillerMutation:
    time_seconds: float
    sequence: int
    bar: str
    replaced_skill_name: str
    execute_skill_name: str
    current_damage: float
    execute_damage: float


@dataclass(frozen=True)
class RotationExecuteFillerMutationResult:
    candidate: GeneratedRotationCandidate
    comparisons: tuple[RotationExecuteFillerDamageComparison, ...] = ()
    mutations: tuple[RotationExecuteFillerMutation, ...] = ()
    unresolved: tuple[str, ...] = ()


class RotationExecuteFillerMutationService:
    """Replace filler skills only with strictly better, resolved execute actions."""

    def __init__(
        self,
        *,
        comparison_service: RotationExecuteFillerDamageComparisonService,
    ) -> None:
        self.comparison_service = comparison_service

    def apply(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        opportunities: tuple[RotationExecuteFillerOpportunity, ...],
    ) -> RotationExecuteFillerMutationResult:
        comparisons = tuple(
            self.comparison_service.compare(candidate=candidate, opportunity=opportunity)
            for opportunity in opportunities
        )
        unresolved: list[str] = []
        for comparison in comparisons:
            unresolved.extend(comparison.unresolved)

        by_slot: dict[tuple[float, str, str], list[RotationExecuteFillerDamageComparison]] = {}
        for comparison in comparisons:
            opportunity = comparison.opportunity
            key = (
                float(opportunity.time_seconds),
                opportunity.bar,
                opportunity.current_skill_name.casefold(),
            )
            by_slot.setdefault(key, []).append(comparison)

        replacements: dict[tuple[float, int], RotationExecuteFillerDamageComparison] = {}
        mutations: list[RotationExecuteFillerMutation] = []

        for (time_seconds, bar, current_key), rows in sorted(by_slot.items()):
            winning = tuple(
                row
                for row in rows
                if row.replace_with_execute
                and not row.unresolved
                and row.current_damage is not None
                and row.execute_damage is not None
            )
            if not winning:
                continue

            best_damage = max(float(row.execute_damage) for row in winning)
            best = tuple(
                row
                for row in winning
                if abs(float(row.execute_damage) - best_damage) <= 1e-9
            )
            if len(best) != 1:
                names = ", ".join(
                    sorted({row.opportunity.execute_skill_name for row in best})
                )
                unresolved.append(
                    f"execute replacement at {time_seconds:g}s on {bar} bar has an unresolved "
                    f"equal-damage tie between: {names}"
                )
                continue

            chosen = best[0]
            matches = tuple(
                action
                for action in candidate.plan.actions
                if action.kind is RotationActionKind.SKILL
                and action.name
                and action.name.casefold() == current_key
                and action.bar == bar
                and abs(float(action.time_seconds) - time_seconds) <= 1e-9
            )
            if len(matches) != 1:
                unresolved.append(
                    "execute mutation expected one exact scheduled filler action at "
                    f"{time_seconds:g}s on {bar} bar; found {len(matches)}"
                )
                continue
            action = matches[0]
            replacements[(float(action.time_seconds), int(action.sequence))] = chosen

        actions: list[RotationAction] = []
        for action in candidate.plan.actions:
            chosen = replacements.get((float(action.time_seconds), int(action.sequence)))
            if chosen is None:
                actions.append(action)
                continue
            opportunity = chosen.opportunity
            replacement = RotationAction(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                kind=action.kind,
                name=opportunity.execute_skill_name,
                bar=action.bar,
            )
            actions.append(replacement)
            mutations.append(
                RotationExecuteFillerMutation(
                    time_seconds=float(action.time_seconds),
                    sequence=int(action.sequence),
                    bar=str(action.bar),
                    replaced_skill_name=str(action.name),
                    execute_skill_name=opportunity.execute_skill_name,
                    current_damage=float(chosen.current_damage),
                    execute_damage=float(chosen.execute_damage),
                )
            )

        if not mutations:
            return RotationExecuteFillerMutationResult(
                candidate=candidate,
                comparisons=comparisons,
                mutations=(),
                unresolved=tuple(self._dedupe(unresolved)),
            )

        assumptions = list(candidate.plan.assumptions)
        for mutation in mutations:
            assumptions.append(
                f"execute phase replaced '{mutation.replaced_skill_name}' with "
                f"'{mutation.execute_skill_name}' at {mutation.time_seconds:g}s on {mutation.bar} bar "
                "because canonical exact-slot damage was strictly greater"
            )

        plan = RotationPlan(
            character_name=candidate.plan.character_name,
            build_name=candidate.plan.build_name,
            duration_seconds=candidate.plan.duration_seconds,
            actions=tuple(actions),
            assumptions=tuple(self._dedupe(assumptions)),
            unresolved=candidate.plan.unresolved,
        )
        return RotationExecuteFillerMutationResult(
            candidate=replace(candidate, plan=plan),
            comparisons=comparisons,
            mutations=tuple(mutations),
            unresolved=tuple(self._dedupe(unresolved)),
        )

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result


__all__ = [
    "RotationExecuteFillerMutation",
    "RotationExecuteFillerMutationResult",
    "RotationExecuteFillerMutationService",
]
