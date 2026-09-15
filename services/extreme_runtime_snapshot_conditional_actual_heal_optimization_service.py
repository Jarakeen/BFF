from __future__ import annotations

"""Snapshot-aware bridge for conditional Extreme actual-heal optimization.

The underlying conditional optimizer still owns healer-specific legality and scoring.
This adapter migrates reviewed scenario windows onto E1's role-neutral runtime timeline
and composes E2's legal Champion Point search with that same production path.
"""

from dataclasses import replace

from services.extreme_actual_heal_champion_point_candidate_service import (
    ExtremeActualHealChampionPointCandidateService,
)
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot


RESTORATION_HEAVY_POST_COMPLETION_CONDITION = (
    "restoration_staff_heavy_post_completion_window"
)
SACRED_GROUND_CONDITION = "sacred_ground_window"


class ExtremeRuntimeSnapshotConditionalActualHealOptimizationService(
    ExtremeConditionalActualHealOptimizationService
):
    """Compose unified runtime truth with legal heal-relevant CP search."""

    CP_SEARCH_SCOPE = "legal heal-relevant Champion Point loadout search"

    def __init__(
        self,
        *,
        runtime_snapshot: ExtremeRuntimeSnapshot | None = None,
        fully_charged_restoration_heavy_attack_completed: bool = False,
        sacred_ground_window_active: bool = False,
        champion_point_candidates: ExtremeActualHealChampionPointCandidateService | None = None,
        **kwargs,
    ) -> None:
        active_conditions = (
            frozenset()
            if runtime_snapshot is None
            else frozenset(runtime_snapshot.active_condition_ids)
        )
        super().__init__(
            runtime_snapshot=runtime_snapshot,
            fully_charged_restoration_heavy_attack_completed=(
                bool(fully_charged_restoration_heavy_attack_completed)
                or RESTORATION_HEAVY_POST_COMPLETION_CONDITION in active_conditions
            ),
            sacred_ground_window_active=(
                bool(sacred_ground_window_active)
                or SACRED_GROUND_CONDITION in active_conditions
            ),
            **kwargs,
        )
        self.champion_point_candidates = (
            champion_point_candidates
            or ExtremeActualHealChampionPointCandidateService(
                self.optimizer.database_path
            )
        )
        self._champion_point_search_unresolved: tuple[str, ...] = ()

    def optimize(self, *args, **kwargs):
        self._champion_point_search_unresolved = ()
        result = super().optimize(*args, **kwargs)
        unresolved = tuple(
            dict.fromkeys(
                (
                    *result.unresolved,
                    *self._champion_point_search_unresolved,
                )
            )
        )
        search_scope = (
            result.search_scope
            if self.CP_SEARCH_SCOPE in result.search_scope
            else (*result.search_scope, self.CP_SEARCH_SCOPE)
        )
        return replace(
            result,
            unresolved=unresolved,
            search_scope=search_scope,
        )

    def _additional_candidates(
        self,
        baseline_build,
        *,
        progression,
        character_id: str,
        baseline_build_id: str,
        entity_id: str,
        active_bar: str,
    ):
        inherited = super()._additional_candidates(
            baseline_build,
            progression=progression,
            character_id=character_id,
            baseline_build_id=baseline_build_id,
            entity_id=entity_id,
            active_bar=active_bar,
        )
        result = self.champion_point_candidates.build_candidates(
            baseline_build,
            character_id=character_id,
            baseline_build_id=baseline_build_id,
        )
        self._champion_point_search_unresolved = tuple(
            dict.fromkeys(
                (
                    *self._champion_point_search_unresolved,
                    *result.unresolved,
                )
            )
        )
        return (*inherited, *result.candidates)


__all__ = [
    "ExtremeRuntimeSnapshotConditionalActualHealOptimizationService",
    "RESTORATION_HEAVY_POST_COMPLETION_CONDITION",
    "SACRED_GROUND_CONDITION",
]
