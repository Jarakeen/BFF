from __future__ import annotations

from dataclasses import replace

from services.extreme_actual_heal_armor_weight_candidate_service import (
    ExtremeActualHealArmorWeightCandidateService,
)
from services.extreme_actual_heal_armor_weight_legality_service import (
    ExtremeActualHealArmorWeightLegalityService,
)
from services.extreme_actual_heal_attribute_projection_service import (
    ExtremeActualHealAttributeProjectionService,
)
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
    conditional Extreme path, and adds E2 legal-character search seams.

    Champion Point legality is score-neutral here: candidate bars are materialized
    first and the ordinary whole-build healing evaluator decides which legal bar
    wins. Mixed flat/percent/critical CP values are never compared as if they
    shared a unit. Any heal-relevant CP coverage gap remains explicit unresolved
    evidence.

    The standing H1 attribute axis is proof-reduced here. The complete legal
    64-point simplex remains the denominator, but a selected heal is reduced to
    pure Magicka/Stamina endpoints only when every contributing HEAL coefficient
    is on the reviewed type-8, non-negative highest-resource path. If that proof
    fails, the inherited conservative candidate path remains active and the proof
    gap is carried as unresolved evidence.

    Armor-weight search uses canonical set-piece ``armor_type`` evidence for the
    current gear layout. It enumerates every physically legal slot-weight layout
    and keeps one deterministic witness for each H1-relevant Medium-piece-count +
    distinct-armor-type signature. Joint gear-package + weight expansion remains
    a later proof boundary; this layer does not pretend a set can change armor
    weight merely because that would score better.

    Explicitly injected optimizers, healing-event evaluators, CP candidate
    services, attribute projection services, and armor candidate services remain
    authoritative for focused tests and specialist callers.
    """

    CP_SEARCH_SCOPE = "legal heal-relevant Champion Point loadout search"

    def __init__(
        self,
        *,
        optimizer: ExtremeCompleteOptimizationService | None = None,
        healing_events=None,
        champion_point_candidates: ExtremeActualHealChampionPointCandidateService | None = None,
        attribute_projection: ExtremeActualHealAttributeProjectionService | None = None,
        armor_weight_candidates: ExtremeActualHealArmorWeightCandidateService | None = None,
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
        database_path = getattr(core_optimizer, "database_path", None)
        self.champion_point_candidates = (
            champion_point_candidates
            or (
                ExtremeActualHealChampionPointCandidateService(database_path)
                if database_path is not None
                else None
            )
        )
        self.attribute_projection = (
            attribute_projection
            or (
                ExtremeActualHealAttributeProjectionService(database_path)
                if database_path is not None
                else None
            )
        )
        self.armor_weight_candidates = armor_weight_candidates
        if self.armor_weight_candidates is None and database_path is not None:
            self.armor_weight_candidates = ExtremeActualHealArmorWeightCandidateService(
                ExtremeActualHealArmorWeightLegalityService(database_path)
            )

        self._champion_point_search_unresolved: tuple[str, ...] = ()
        self._attribute_search_unresolved: tuple[str, ...] = ()
        self._attribute_search_scope: tuple[str, ...] = ()
        self._attribute_search_entity_id = ""
        self._armor_weight_search_unresolved: tuple[str, ...] = ()
        self._armor_weight_search_scope: tuple[str, ...] = ()

    def optimize(self, baseline_build, entity_id: str, *args, **kwargs):
        self._champion_point_search_unresolved = ()
        self._attribute_search_unresolved = ()
        self._attribute_search_scope = ()
        self._attribute_search_entity_id = str(entity_id or "").strip()
        self._armor_weight_search_unresolved = ()
        self._armor_weight_search_scope = ()
        result = super().optimize(baseline_build, entity_id, *args, **kwargs)
        unresolved = tuple(
            dict.fromkeys(
                (
                    *result.unresolved,
                    *self._champion_point_search_unresolved,
                    *self._attribute_search_unresolved,
                    *self._armor_weight_search_unresolved,
                )
            )
        )
        search_scope = result.search_scope
        if self.CP_SEARCH_SCOPE not in search_scope:
            search_scope = (*search_scope, self.CP_SEARCH_SCOPE)
        for item in (*self._attribute_search_scope, *self._armor_weight_search_scope):
            if item not in search_scope:
                search_scope = (*search_scope, item)
        return replace(
            result,
            unresolved=unresolved,
            search_scope=search_scope,
        )

    def _resource_attribute_candidates(
        self,
        baseline_build,
        *,
        character_id: str,
        baseline_build_id: str,
    ):
        if self.attribute_projection is None or not self._attribute_search_entity_id:
            return super()._resource_attribute_candidates(
                baseline_build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
            )

        result = self.attribute_projection.build_candidates(
            baseline_build,
            entity_id=self._attribute_search_entity_id,
            character_id=character_id,
            baseline_build_id=baseline_build_id,
        )
        if not result.denominator_proven:
            self._attribute_search_unresolved = tuple(
                dict.fromkeys(
                    (*self._attribute_search_unresolved, *result.unresolved)
                )
            )
            return super()._resource_attribute_candidates(
                baseline_build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
            )

        self._attribute_search_scope = tuple(
            dict.fromkeys((*self._attribute_search_scope, *result.search_scope))
        )
        return result.candidates

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
        inherited = list(
            super()._additional_candidates(
                baseline_build,
                progression=progression,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
                entity_id=entity_id,
                active_bar=active_bar,
            )
        )

        if self.champion_point_candidates is not None:
            cp_result = self.champion_point_candidates.build_candidates(
                baseline_build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
            )
            self._champion_point_search_unresolved = tuple(
                dict.fromkeys(
                    (
                        *self._champion_point_search_unresolved,
                        *cp_result.unresolved,
                    )
                )
            )
            inherited.extend(cp_result.candidates)

        if self.armor_weight_candidates is not None:
            armor_result = self.armor_weight_candidates.build_candidates(
                baseline_build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
            )
            self._armor_weight_search_unresolved = tuple(
                dict.fromkeys(
                    (
                        *self._armor_weight_search_unresolved,
                        *armor_result.unresolved,
                    )
                )
            )
            if armor_result.denominator_proven:
                scope = (
                    f"physical armor-weight search for current gear layout: "
                    f"{armor_result.raw_layout_count} legal slot layouts reduced to "
                    f"{armor_result.retained_signature_count} H1-relevant signatures",
                )
                self._armor_weight_search_scope = tuple(
                    dict.fromkeys((*self._armor_weight_search_scope, *scope))
                )
                inherited.extend(armor_result.candidates)

        return tuple(inherited)
