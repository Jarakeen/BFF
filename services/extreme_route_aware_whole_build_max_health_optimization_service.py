from __future__ import annotations

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_whole_build_max_health_optimization_service import (
    ExtremeWholeBuildMaxHealthOptimizationService,
)


class ExtremeRouteAwareWholeBuildMaxHealthOptimizationService(
    ExtremeWholeBuildMaxHealthOptimizationService
):
    """Use an explicit hypothetical progression snapshot during Max Health search.

    The ordinary whole-build Max Health optimizer correctly resolves progression
    from a saved build. Extreme class-route search is different: the candidate
    build may represent a hypothetical subclass route whose equipped class-line
    passives have already been normalized independently. This adapter preserves
    that exact snapshot through every candidate reevaluation without changing the
    shared base optimizer API.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._route_progression_override: CharacterProgression | None = None

    def optimize(
        self,
        baseline_build: PlayerBuild,
        objective_key: str,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
        progression_override: CharacterProgression | None = None,
    ):
        self._route_progression_override = progression_override
        try:
            return super().optimize(
                baseline_build,
                objective_key,
                active_bar=active_bar,
                max_passes=max_passes,
            )
        finally:
            self._route_progression_override = None

    def _evaluate(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        character_id: str,
        build_id: str,
        objective,
        active_bar: str,
    ):
        effective_progression = self._route_progression_override or progression
        return super()._evaluate(
            build,
            progression=effective_progression,
            character_id=character_id,
            build_id=build_id,
            objective=objective,
            active_bar=active_bar,
        )
