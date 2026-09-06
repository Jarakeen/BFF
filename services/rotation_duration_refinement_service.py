from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import DEFAULT_DATABASE
from minmax.duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from minmax.rotation_plan import RotationPlan
from services.rotation_duration_analysis_service import (
    RotationDurationAnalysisService,
    RotationDurationProjection,
)


@dataclass(frozen=True)
class RotationDurationRefinement:
    """One duration-aware refinement result with its supporting evidence."""

    plan: RotationPlan
    duration_projection: RotationDurationProjection


class RotationDurationRefinementService:
    """Resolve canonical durations, then refine one already-valid rotation plan."""

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

    def refine(self, plan: RotationPlan) -> RotationDurationRefinement:
        projection = self.duration_analysis.analyze(plan)
        refined = self.scheduler.refine(plan, projection.rules)

        unresolved = self._dedupe(
            tuple(refined.unresolved) + tuple(projection.unresolved)
        )
        if unresolved != refined.unresolved:
            refined = RotationPlan(
                character_name=refined.character_name,
                build_name=refined.build_name,
                duration_seconds=refined.duration_seconds,
                actions=refined.actions,
                assumptions=refined.assumptions,
                unresolved=unresolved,
            )

        return RotationDurationRefinement(
            plan=refined,
            duration_projection=projection,
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
