from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import DEFAULT_DATABASE
from minmax.duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from minmax.priority_aware_duration_scheduler import PriorityAwareDurationRotationScheduler
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationPlan
from services.rotation_duration_analysis_service import (
    RotationDurationAnalysisService,
    RotationDurationProjection,
)


@dataclass(frozen=True)
class RotationDurationRefinement:
    """One duration-aware refinement result with evidence from the final schedule."""

    plan: RotationPlan
    duration_projection: RotationDurationProjection


class RotationDurationRefinementService:
    """Resolve canonical durations, refine a plan, then analyze the final schedule."""

    def __init__(
        self,
        database_path: Path = DEFAULT_DATABASE,
        *,
        duration_analysis: RotationDurationAnalysisService | None = None,
        scheduler: DurationAwareRotationScheduler | None = None,
    ) -> None:
        self.duration_analysis = duration_analysis or RotationDurationAnalysisService(
            database_path
        )
        self.scheduler = scheduler or DurationAwareRotationScheduler()

    def refine(
        self,
        plan: RotationPlan,
        *,
        priorities: AbilityPriorityList | None = None,
    ) -> RotationDurationRefinement:
        # The first projection supplies canonical duration rules used to refine
        # the seed schedule. It is not returned as final evidence because its
        # uptime/gap measurements describe the pre-refinement plan.
        seed_projection = self.duration_analysis.analyze(plan)
        scheduler = (
            PriorityAwareDurationRotationScheduler(priorities)
            if priorities is not None
            else self.scheduler
        )
        refined = scheduler.refine(plan, seed_projection.rules)

        unresolved = self._dedupe(
            tuple(refined.unresolved) + tuple(seed_projection.unresolved)
        )
        if unresolved != refined.unresolved:
            refined = self._with_unresolved(refined, unresolved)

        # Re-analyze the actual refined actions so callers receive duration,
        # recast, uptime, and gap evidence for the same plan they render/evaluate.
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
