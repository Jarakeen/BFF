from __future__ import annotations

"""Gear-aware from-scratch Extreme records for executable core stat objectives.

This layer closes the named gear-set/package axis only when the canonical topology,
slot eligibility, objective relevance, and physical realization services all prove
their denominator. Reviewed stat objectives may additionally search either the
established armor weight/static-trait family or the proof-reduced max-resource
Divines/Infused + armor-glyph family beneath the existing Mundus -> food -> potion
stack and through the canonical stat pipeline.

Every searched armor family is narrower than the whole equipment-trait/enchantment
space. Residual armor, jewelry, and weapon axes remain explicit coverage gaps until
their own canonical finite searches are closed.
"""

from pathlib import Path
from typing import Any

from minmax.combat_effect_semantics import GameUpdate
from minmax.gear_set_repository import GearSetRepository
from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphStateService,
)
from services.extreme_armor_weight_trait_state_service import ExtremeArmorWeightTraitStateService
from services.extreme_best_named_gear_armor_mundus_food_potion_structural_stat_evaluator import (
    ExtremeBestNamedGearArmorMundusFoodPotionStructuralStatEvaluator,
    ExtremeNamedGearArmorFiniteAxisEvaluatorFactory,
)
from services.extreme_best_named_gear_mundus_food_potion_structural_stat_evaluator import (
    ExtremeBestNamedGearMundusFoodPotionStructuralStatEvaluator,
    ExtremeNamedGearFiniteAxisEvaluatorFactory,
)
from services.extreme_best_named_gear_resource_armor_mundus_food_potion_structural_stat_evaluator import (
    ExtremeBestNamedGearResourceArmorMundusFoodPotionStructuralStatEvaluator,
    ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory,
)
from services.extreme_core_stat_record_service import ExtremeCoreStatRecordService
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_hypothetical_class_progression_service import ExtremeHypotheticalClassProgressionService
from services.extreme_named_gear_set_slot_eligibility_service import ExtremeNamedGearSetSlotEligibilityService
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationResult,
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_record_result import (
    ExtremeRecordProofStatus,
    ExtremeRecordResult,
    ExtremeRecordSearchCoverage,
)
from services.extreme_structural_core_stat_record_service import (
    ExtremeCanonicalStructuralStatEvaluator,
    ExtremeStructuralCoreStatRecordService,
)
from services.extreme_structural_global_search_service import (
    ExtremeStructuralGlobalSearchResult,
    ExtremeStructuralGlobalSearchService,
)
from services.extreme_structural_mundus_core_stat_record_service import (
    _MUNDUS_DEFERRED_AXIS,
    _MUNDUS_SCOPE,
)
from services.extreme_structural_mundus_food_core_stat_record_service import (
    _FOOD_DEFERRED_AXIS,
    _FOOD_SCOPE,
)
from services.extreme_structural_mundus_food_potion_core_stat_record_service import (
    _POTION_DEFERRED_AXIS,
    _POTION_SCOPE,
)


_GEAR_DEFERRED_AXIS = "gear and legal set/package topology"
_EQUIPMENT_TRAIT_DEFERRED_AXIS = "armor, jewelry, and weapon traits"
_GLYPH_DEFERRED_AXIS = "glyphs/enchants"
_REMAINING_EQUIPMENT_TRAIT_AXIS = (
    "glyph-dependent/runtime armor traits plus jewelry and weapon traits"
)
_RESOURCE_REMAINING_EQUIPMENT_TRAIT_AXIS = (
    "armor weight/passive interactions and non-resource/runtime armor traits plus jewelry and weapon traits"
)
_RESOURCE_REMAINING_GLYPH_AXIS = "jewelry and weapon glyphs/enchants"
_GEAR_SCOPE = (
    "all objective-surviving canonical named gear-set breakpoint assignments "
    "with proven active-snapshot physical slot witnesses"
)
_REVIEWED_ARMOR_SCOPE = (
    "all reviewed seven-piece Light/Medium/Heavy armor weight and static-trait states "
    "(None, Divines, Reinforced, Nirnhoned, Invigorating)"
)
_RESOURCE_ARMOR_SCOPE = (
    "all proof-reduced seven-piece Divines/Infused armor trait plus objective-relevant "
    "CP160 Truly Superb armor-glyph states"
)


class ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService:
    """Return gear-aware structural/Mundus/food/potion core-stat records."""

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        optimizer: ExtremeOptimizationService | None = None,
        max_gear_assignments_per_topology: int | None = None,
    ) -> None:
        self.optimizer = optimizer or ExtremeOptimizationService(database_path=database_path)
        self.database_path = Path(database_path or self.optimizer.database_path)
        self.max_gear_assignments_per_topology = max_gear_assignments_per_topology

    def _gear_realization(
        self,
        objective_key: str,
    ) -> ExtremeObjectiveNamedGearSetCatalogRealizationResult:
        repository = GearSetRepository(self.database_path)
        topology = ExtremeGearSetTopologyCatalogService(repository).build()
        breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
        eligibility = ExtremeNamedGearSetSlotEligibilityService(self.database_path).build()
        relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(
            objective_key,
            breakpoints,
        )
        return ExtremeObjectiveNamedGearSetCatalogRealizationService(
            breakpoints=breakpoints,
            eligibility=eligibility,
            relevance=relevance,
        ).build(
            topology,
            max_assignments_per_topology=self.max_gear_assignments_per_topology,
        )

    def record(self, objective_key: str) -> ExtremeRecordResult:
        key = str(objective_key or "").strip().casefold()
        if not ExtremeCoreStatRecordService.supports(key):
            raise ValueError(
                "Extreme structural+named-gear+Mundus+food+potion core-stat search "
                f"does not support objective: {objective_key!r}"
            )

        gear_realization = self._gear_realization(key)
        canonical = ExtremeCanonicalStructuralStatEvaluator(
            optimizer=self.optimizer,
            progression_service=ExtremeHypotheticalClassProgressionService(self.database_path),
        )
        mundus_repository = MundusRepository(
            self.database_path,
            game_update=U50_GAME_UPDATE,
            initialize=False,
        )
        provisioning_repository = ProvisioningStaticRepository(self.database_path)
        potion_repository = PotionAvailabilityRepository(
            self.database_path,
            game_update=GameUpdate.U50,
        )

        armor_catalog = None
        armor_count = 1
        resource_armor = key in ExtremeArmorResourceTraitGlyphStateService.SUPPORTED_OBJECTIVES
        reviewed_armor = key in ExtremeArmorWeightTraitStateService.REVIEWED_OBJECTIVES

        if resource_armor:
            armor_catalog = ExtremeArmorResourceTraitGlyphStateService(self.database_path).build(key)
            factory = ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory(
                canonical_evaluator=canonical,
                mundus_repository=mundus_repository,
                provisioning_repository=provisioning_repository,
                potion_repository=potion_repository,
            )
            evaluator = ExtremeBestNamedGearResourceArmorMundusFoodPotionStructuralStatEvaluator(
                gear_realization=gear_realization,
                armor_catalog=armor_catalog,
                evaluator_factory=factory,
            )
            gear_candidates = evaluator.gear_realizations()
            armor_states = evaluator.armor_states()
            armor_count = len(armor_states)
        elif reviewed_armor:
            armor_catalog = ExtremeArmorWeightTraitStateService.build(key)
            factory = ExtremeNamedGearArmorFiniteAxisEvaluatorFactory(
                canonical_evaluator=canonical,
                mundus_repository=mundus_repository,
                provisioning_repository=provisioning_repository,
                potion_repository=potion_repository,
            )
            evaluator = ExtremeBestNamedGearArmorMundusFoodPotionStructuralStatEvaluator(
                gear_realization=gear_realization,
                armor_catalog=armor_catalog,
                evaluator_factory=factory,
            )
            gear_candidates = evaluator.gear_realizations()
            armor_states = evaluator.armor_states()
            armor_count = len(armor_states)
        else:
            factory = ExtremeNamedGearFiniteAxisEvaluatorFactory(
                canonical_evaluator=canonical,
                mundus_repository=mundus_repository,
                provisioning_repository=provisioning_repository,
                potion_repository=potion_repository,
            )
            evaluator = ExtremeBestNamedGearMundusFoodPotionStructuralStatEvaluator(
                gear_realization=gear_realization,
                evaluator_factory=factory,
            )
            gear_candidates = evaluator.gear_realizations()
            armor_states = ()

        universe_service = ExtremeGlobalSearchUniverseService(self.database_path)
        search_service = ExtremeStructuralGlobalSearchService(
            universe_service,
            scorer=evaluator,
        )
        result: ExtremeStructuralGlobalSearchResult[dict[str, Any]] = search_service.search(key)

        # Probe the established finite-axis evaluator only for denominator sizes.
        # Depend on the evaluator contract rather than concrete classes so test
        # doubles and future compatible implementations cannot silently zero
        # otherwise valid coverage accounting.
        mundus_count = 0
        food_count = 0
        potion_count = 0
        armor_axis_active = resource_armor or reviewed_armor
        if gear_candidates and (not armor_axis_active or armor_states):
            probe = (
                factory(gear_candidates[0], armor_states[0])
                if armor_axis_active
                else factory(gear_candidates[0])
            )
            potion_states = getattr(probe, "potion_states", None)
            food_evaluator = getattr(probe, "food_evaluator", None)
            food_choices = getattr(food_evaluator, "food_choices", None)
            mundus_evaluator = getattr(food_evaluator, "mundus_evaluator", None)
            mundus_choices = getattr(mundus_evaluator, "mundus_choices", None)
            if callable(potion_states):
                potion_count = len(tuple(potion_states()))
            if callable(food_choices):
                food_count = len(tuple(food_choices()))
            if callable(mundus_choices):
                mundus_count = len(tuple(mundus_choices()))

        searched_parts = [*result.structural_scope, _GEAR_SCOPE]
        if resource_armor:
            searched_parts.append(_RESOURCE_ARMOR_SCOPE)
        elif reviewed_armor:
            searched_parts.append(_REVIEWED_ARMOR_SCOPE)
        searched_parts.extend((_MUNDUS_SCOPE, _FOOD_SCOPE, _POTION_SCOPE))
        searched = tuple(searched_parts)

        closed_axes = {_MUNDUS_DEFERRED_AXIS, _FOOD_DEFERRED_AXIS, _POTION_DEFERRED_AXIS}
        if evaluator.gear_denominator_proven:
            closed_axes.add(_GEAR_DEFERRED_AXIS)

        omitted_rows: list[str] = []
        for axis in result.deferred_dynamic_axes:
            if axis in closed_axes:
                continue
            if axis == _EQUIPMENT_TRAIT_DEFERRED_AXIS:
                if resource_armor:
                    omitted_rows.append(_RESOURCE_REMAINING_EQUIPMENT_TRAIT_AXIS)
                    continue
                if reviewed_armor:
                    omitted_rows.append(_REMAINING_EQUIPMENT_TRAIT_AXIS)
                    continue
            if axis == _GLYPH_DEFERRED_AXIS and resource_armor:
                omitted_rows.append(_RESOURCE_REMAINING_GLYPH_AXIS)
                continue
            omitted_rows.append(axis)
        omitted = tuple(omitted_rows)

        expanded_count = (
            int(result.candidates_scored)
            * len(gear_candidates)
            * armor_count
            * mundus_count
            * food_count
            * potion_count
        )
        reviewed_armor_denominator_proven = bool(
            not reviewed_armor
            or getattr(evaluator, "reviewed_armor_denominator_proven", False)
        )
        resource_armor_denominator_proven = bool(
            not resource_armor
            or getattr(evaluator, "reviewed_resource_armor_denominator_proven", False)
        )
        denominator_proven = bool(
            result.structural_denominator_proven
            and evaluator.gear_denominator_proven
            and reviewed_armor_denominator_proven
            and resource_armor_denominator_proven
            and gear_candidates
            and armor_count
            and mundus_count
            and food_count
            and potion_count
            and not omitted
            and not result.unresolved
        )
        coverage = ExtremeRecordSearchCoverage(
            searched=searched,
            omitted=omitted,
            candidates_screened=expanded_count,
            candidates_optimized=expanded_count,
            denominator_proven=denominator_proven,
        )

        armor_unresolved = tuple(armor_catalog.unresolved) if armor_catalog is not None else ()
        aggregate_unresolved = tuple(
            dict.fromkeys(
                str(item)
                for item in (*gear_realization.unresolved, *armor_unresolved, *result.unresolved)
                if str(item)
            )
        )
        if result.best is None:
            return ExtremeRecordResult.for_objective(
                key,
                raw_value=None,
                proof_status=ExtremeRecordProofStatus.UNRESOLVED,
                unresolved=tuple(
                    dict.fromkeys(
                        (
                            "Gear-aware structural Extreme search produced no scored candidate",
                            *aggregate_unresolved,
                        )
                    )
                ),
                search_coverage=coverage,
            )

        winner = result.best
        payload = winner.payload if isinstance(winner.payload, dict) else {}
        searched_armor_phrase = ""
        if resource_armor:
            searched_armor_phrase = " × every proof-reduced Divines/Infused + armor-glyph state"
        elif reviewed_armor:
            searched_armor_phrase = " × every reviewed armor weight/static-trait state"

        explanation_rows = [
            "Searched race × legal class route × all 64-point attribute allocations × active bar × objective-surviving named gear witnesses"
            + searched_armor_phrase
            + " × every Update-50 Mundus × canonical food/drink × canonical potion snapshot.",
            f"Named gear realization reviewed {gear_realization.breakpoints_reviewed:,} set-bonus breakpoints; safely pruned {gear_realization.breakpoints_pruned_irrelevant:,} objective-irrelevant breakpoints.",
            f"Considered {gear_realization.assignments_considered:,} named set assignments; physically realized {gear_realization.assignments_realized:,} and rejected {gear_realization.assignments_rejected:,}.",
        ]
        if resource_armor:
            explanation_rows.append(
                f"Scored {armor_count:,} proof-reduced resource armor trait/glyph states for each of {len(gear_candidates):,} distinct gear witnesses before Mundus/food/potion selection."
            )
            explanation_rows.append(
                "The resource armor reducer jointly compares Divines and Infused with objective-relevant armor glyphs; armor-weight/passive interactions and jewelry/weapon equipment axes remain separate."
            )
        elif reviewed_armor:
            explanation_rows.append(
                f"Scored {armor_count:,} reviewed armor states for each of {len(gear_candidates):,} distinct gear witnesses before Mundus/food/potion selection."
            )
        else:
            explanation_rows.append(
                f"Scored {len(gear_candidates):,} distinct gear witnesses per structural candidate; this objective has no reviewed armor search yet."
            )
        explanation_rows.extend(
            (
                f"Finite axes include {mundus_count:,} Mundus, {food_count:,} food, and {potion_count:,} potion states.",
                "Residual equipment traits/enchants, skills, Champion Points, remaining passives, and runtime-only axes remain separate unless coverage says otherwise.",
            )
        )

        runtime_prerequisites = ()
        if str(payload.get("potion") or ""):
            runtime_prerequisites = (
                "Winning potion formula must be activated and its mapped effects active at the scored snapshot.",
            )

        return ExtremeRecordResult.for_objective(
            key,
            raw_value=float(winner.value),
            proof_status=(
                ExtremeRecordProofStatus.PROVEN
                if denominator_proven
                else ExtremeRecordProofStatus.LOWER_BOUND
            ),
            winning_build=winner.payload,
            unit=ExtremeStructuralCoreStatRecordService._unit(key),
            runtime_prerequisites=runtime_prerequisites,
            self_provided_conditions=tuple(payload.get("active_buffs") or ()),
            unresolved=aggregate_unresolved,
            search_coverage=coverage,
            explanation=tuple(explanation_rows),
        )
