from __future__ import annotations

from dataclasses import replace

from services.extreme_actual_heal_champion_point_candidate_service import (
    ExtremeActualHealChampionPointCandidateService,
)
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationService,
)
from services.extreme_canonical_healing_event_service import (
    ExtremeCanonicalHealingEventService,
)
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService


class ExtremeCanonicalActualHealOptimizationService(ExtremeActualHealOptimizationService):
    """Standing Actual Heal optimizer with canonical heal-event aggregation.

    ``ExtremeActualHealOptimizationService`` owns the mature whole-build search.
    This subtype changes its default healing-event evaluator so standing
    optimization uses the same reviewed recipient/time identity semantics as the
    conditional Extreme path, and adds the E2 legal Champion Point loadout seam.

    CP legality is score-neutral here: candidate bars are materialized first and
    the ordinary whole-build healing evaluator decides which legal bar wins.
    Mixed flat/percent/critical CP values are never compared as if they shared a
    unit. Any heal-relevant CP coverage gap remains explicit unresolved evidence.

    Explicitly injected optimizers, healing-event evaluators, and CP candidate
    services remain authoritative for focused tests and specialist callers.
    """

    CP_SEARCH_SCOPE = "legal heal-relevant Champion Point loadout search"

    def __init__(
        self,
        *,
        optimizer: ExtremeCompleteOptimizationService | None = None,
        healing_events=None,
        champion_point_candidates: ExtremeActualHealChampionPointCandidateService | None = None,
        **kwargs,
    ) -> None:
        core_optimizer = optimizer or ExtremeCompleteOptimizationService()
        canonical_events = healing_events or ExtremeCanonicalHealingEventService(
            database_path=core_optimizer.database_path
        )
        super().__init__(
            optimizer=core_optimizer,
            healing_events=canonical_events,
            **kwargs,
        )
        self.champion_point_candidates = (
            champion_point_candidates
            or ExtremeActualHealChampionPointCandidateService(
                core_optimizer.database_path
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
