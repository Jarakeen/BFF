from __future__ import annotations

from pathlib import Path

from engine.config import DEFAULT_DATABASE
from minmax.local_refresh_cadence_duration_scheduler import (
    LocalRefreshCadenceDurationRotationScheduler,
    PriorityAwareLocalRefreshCadenceDurationRotationScheduler,
)
from minmax.refresh_cadence_duration_scheduler import RotationRefreshIntervalPolicy
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationPlan
from services.rotation_duration_analysis_service import RotationDurationAnalysisService
from services.rotation_duration_refinement_service import RotationDurationRefinement


class RotationLocalCadenceDurationRefinementService:
    """Refine one cadence family without rescheduling unrelated duration skills.

    The seed plan may already contain accepted cadence changes from earlier local-search
    iterations. Canonical duration rules for every skill are still resolved so unrelated
    duration skills cannot be mistaken for filler actions. Only the skill(s) named by
    the current cadence policies are active refresh obligations in this refinement pass.
    Final duration evidence is then recomputed from the complete refined plan.
    """

    def __init__(
        self,
        database_path: Path = DEFAULT_DATABASE,
        *,
        duration_analysis: RotationDurationAnalysisService | None = None,
    ) -> None:
        self.duration_analysis = duration_analysis or RotationDurationAnalysisService(
            database_path
        )

    def refine(
        self,
        plan: RotationPlan,
        *,
        priorities: AbilityPriorityList | None = None,
        refresh_cadences: tuple[RotationRefreshIntervalPolicy, ...] = (),
    ) -> RotationDurationRefinement:
        cadence_policies = tuple(refresh_cadences)
        if not cadence_policies:
            raise ValueError("local cadence refinement requires at least one refresh cadence policy")

        seed_projection = self.duration_analysis.analyze(plan)
        protected_keys = tuple(
            (rule.skill_name.casefold(), rule.bar)
            for rule in seed_projection.rules
        )

        if priorities is not None:
            scheduler = PriorityAwareLocalRefreshCadenceDurationRotationScheduler(
                priorities,
                cadence_policies,
                protected_duration_keys=protected_keys,
            )
        else:
            scheduler = LocalRefreshCadenceDurationRotationScheduler(
                cadence_policies,
                protected_duration_keys=protected_keys,
            )

        refined = scheduler.refine(plan, seed_projection.rules)
        unresolved = self._dedupe(
            tuple(refined.unresolved) + tuple(seed_projection.unresolved)
        )
        if unresolved != refined.unresolved:
            refined = self._with_unresolved(refined, unresolved)

        final_projection = self.duration_analysis.analyze(refined)
        final_unresolved = self._dedupe(
            tuple(refined.unresolved) + tuple(final_projection.unresolved)
        )
        if final_unresolved != refined.unresolved:
            refined = self._with_unresolved(refined, final_unresolved)

        return RotationDurationRefinement(
            plan=refined,
            duration_projection=final_projection,
        )

    @staticmethod
    def _with_unresolved(
        plan: RotationPlan,
        unresolved: tuple[str, ...],
    ) -> RotationPlan:
        return RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=plan.actions,
            assumptions=plan.assumptions,
            unresolved=unresolved,
        )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)


__all__ = ["RotationLocalCadenceDurationRefinementService"]
