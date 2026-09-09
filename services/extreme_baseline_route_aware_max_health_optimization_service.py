from __future__ import annotations

from models.build_model import PlayerBuild
from services.extreme_optimization_service import ExtremeOptimizationResult
from services.extreme_route_aware_whole_build_max_health_optimization_service import (
    ExtremeRouteAwareWholeBuildMaxHealthOptimizationService,
)
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


class ExtremeBaselineRouteAwareMaxHealthOptimizationService(
    ExtremeRouteAwareWholeBuildMaxHealthOptimizationService
):
    """Evaluate canonical route-aware Max Health without mutation search."""

    SCREENING_SCOPE = (
        "baseline-only canonical Max Health route screening",
        "zero whole-build mutation passes",
    )
    SCREENING_OMITTED = (
        "whole-build Max Health mutation optimization intentionally omitted during route screening",
    )

    def optimize(
        self,
        baseline_build: PlayerBuild,
        objective_key: str,
        *,
        active_bar: str = "front",
        max_passes: int = 0,
        progression_override=None,
    ) -> ExtremeOptimizationResult:
        _ = max_passes
        objective = self.objective(objective_key)
        if objective.key != "max_health":
            raise ValueError("Baseline route screening optimizer supports only max_health")

        resolution = MinmaxCharacterProgressionAdapter(
            self.build_service.canonical.catalog_service
        ).resolve(baseline_build)
        if not resolution.resolved:
            raise ValueError("; ".join(resolution.unresolved))

        build_id = (
            str(getattr(baseline_build, "BuildId", "") or "").strip()
            or str(baseline_build.BuildName or "").strip()
            or "saved-build"
        )
        current = PlayerBuild.from_dict(baseline_build.to_dict())
        self._route_progression_override = progression_override
        try:
            value, unresolved = self._evaluate(
                current,
                progression=resolution.progression,
                character_id=resolution.character_id,
                build_id=f"{build_id}:extreme-max-health:screen",
                objective=objective,
                active_bar=active_bar,
            )
        finally:
            self._route_progression_override = None

        return ExtremeOptimizationResult(
            objective=objective,
            baseline_build=PlayerBuild.from_dict(baseline_build.to_dict()),
            optimized_build=current,
            baseline_value=float(value),
            optimized_value=float(value),
            steps=(),
            unresolved=tuple(unresolved),
            search_scope=self.SCREENING_SCOPE,
            omitted_scope=self.SCREENING_OMITTED,
        )
