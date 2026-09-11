from __future__ import annotations

"""Gear-aware from-scratch Extreme records for executable core stat objectives.

This layer closes named gear and selected reviewed equipment families only when
their canonical denominator is proven. Max-resource objectives additionally search
proof-reduced resource armor, reviewed static jewelry traits, reviewed passive
progression, and reviewed max-resource active-bar witnesses. Canonical jewelry
glyphs and weapon trait/enchantment families may be proven irrelevant to a max
resource, but unknown or relevant evidence stays explicit and fails closed.
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
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphStateService,
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
from services.extreme_hypothetical_undaunted_progression_service import (
    ExtremeHypotheticalUndauntedProgressionService,
)
from services.extreme_jewelry_resource_glyph_relevance_service import (
    ExtremeJewelryResourceGlyphRelevanceService,
)
from services.extreme_jewelry_resource_static_trait_state_service import (
    ExtremeJewelryResourceStaticTraitStateService,
)
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
from services.extreme_weapon_resource_relevance_service import (
    ExtremeWeaponResourceRelevanceService,
)


_GEAR_DEFERRED_AXIS = "gear and legal set/package topology"
_EQUIPMENT_TRAIT_DEFERRED_AXIS = "armor, jewelry, and weapon traits"
_GLYPH_DEFERRED_AXIS = "glyphs/enchants"
_PASSIVE_DEFERRED_AXIS = "class/skill/armor/weapon/guild passive ranks"
_SKILL_BAR_DEFERRED_AXIS = "skill-bar choices and morphs"
_REMAINING_EQUIPMENT_TRAIT_AXIS = (
    "glyph-dependent/runtime armor traits plus jewelry and weapon traits"
)
_RESOURCE_REMAINING_EQUIPMENT_TRAIT_AXIS = (
    "non-resource/runtime armor traits plus remaining glyph-dependent/unreviewed jewelry traits and weapon traits"
)
_RESOURCE_REMAINING_EQUIPMENT_TRAIT_AFTER_WEAPON_AXIS = (
    "non-resource/runtime armor traits plus remaining glyph-dependent/unreviewed jewelry traits"
)
_RESOURCE_REMAINING_GLYPH_AXIS = "jewelry and weapon glyphs/enchants"
_RESOURCE_REMAINING_GLYPH_AFTER_JEWELRY_AXIS = "weapon glyphs/enchants"
_RESOURCE_REMAINING_PASSIVE_AXIS = (
    "remaining class/skill/armor/weapon/guild passive ranks excluding reviewed max-rank Undaunted Mettle"
)
_RESOURCE_REMAINING_PASSIVE_AFTER_JUGGERNAUT_AXIS = (
    "remaining class/skill/armor/weapon/guild passive ranks excluding reviewed max-rank Undaunted Mettle and Juggernaut"
)
_RESOURCE_REMAINING_PASSIVE_AFTER_REVIEWED_BAR_AXIS = (
    "remaining class/skill/armor/weapon/guild passive ranks excluding reviewed max-rank Undaunted Mettle and the objective's canonically applied reviewed resource passives"
)
_RESOURCE_REMAINING_SKILL_BAR_AXIS = (
    "remaining skill-bar choices and morphs excluding reviewed max-resource passive witness bars"
)
_GEAR_SCOPE = (
    "all objective-surviving canonical named gear-set breakpoint assignments "
    "with proven active-snapshot physical slot witnesses"
)
_REVIEWED_ARMOR_SCOPE = (
    "all reviewed seven-piece Light/Medium/Heavy armor weight and static-trait states "
    "(None, Divines, Reinforced, Nirnhoned, Invigorating)"
)
_RESOURCE_ARMOR_SCOPE = (
    "all legal seven-piece Light/Medium/Heavy armor-weight continuations, proof-reduced "
    "by distinct armor-type count, crossed with proof-reduced Divines/Infused plus "
    "objective-relevant CP160 Truly Superb armor-glyph states"
)
_RESOURCE_JEWELRY_STATIC_TRAIT_SCOPE = (
    "all CP160 Gold reviewed static jewelry trait loadouts (Arcane, Healthy, Robust, "
    "Triune, Protective, or empty), proof-reduced to the strongest max-resource continuation"
)
_RESOURCE_JEWELRY_GLYPH_IRRELEVANCE_SCOPE = (
    "all canonical jewelry glyphs reviewed and proven unable to directly modify the requested max resource"
)
_RESOURCE_WEAPON_IRRELEVANCE_SCOPE = (
    "all canonical weapon traits and weapon enchantments reviewed and proven unable to modify the requested max resource"
)
_RESOURCE_UNDAUNTED_SCOPE = (
    "reviewed canonical max-rank Undaunted Mettle applied through shared passive mechanics"
)
_RESOURCE_JUGGERNAUT_SCOPE = (
    "reviewed canonical max-rank Juggernaut applied through shared Heavy Armor piece-count mechanics"
)
_RESOURCE_ACTIVE_BAR_SCOPE = (
    "reviewed six-slot active-bar witness reduction for Dark Vigor, Magicka Flood, and Magicka Controller using the canonical active-skill inventory and legal selected class route"
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

        resource_armor = key in ExtremeArmorResourceWeightTraitGlyphStateService.SUPPORTED_OBJECTIVES
        reviewed_armor = key in ExtremeArmorWeightTraitStateService.REVIEWED_OBJECTIVES
        gear_realization = self._gear_realization(key)
        progression_service = (
            ExtremeHypotheticalUndauntedProgressionService(self.database_path)
            if resource_armor
            else ExtremeHypotheticalClassProgressionService(self.database_path)
        )
        canonical = ExtremeCanonicalStructuralStatEvaluator(
            optimizer=self.optimizer,
            progression_service=progression_service,
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
        jewelry_trait_catalog = None
        jewelry_glyph_audit = None
        weapon_audit = None
        jewelry_state = None

        if resource_armor:
            trait_glyph_service = ExtremeArmorResourceTraitGlyphStateService(self.database_path)
            armor_catalog = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
                key,
                trait_glyph_service=trait_glyph_service,
            ).build(key)
            jewelry_trait_catalog = ExtremeJewelryResourceStaticTraitStateService(
                self.database_path
            ).build(key)
            jewelry_glyph_audit = ExtremeJewelryResourceGlyphRelevanceService(
                self.database_path
            ).build(key)
            weapon_audit = ExtremeWeaponResourceRelevanceService(
                self.database_path
            ).build(key)
            if jewelry_trait_catalog.states:
                jewelry_state = jewelry_trait_catalog.states[0]
            factory = ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory(
                canonical_evaluator=canonical,
                mundus_repository=mundus_repository,
                provisioning_repository=provisioning_repository,
                potion_repository=potion_repository,
                jewelry_state=jewelry_state,
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
            searched_parts.extend(
                (_RESOURCE_ARMOR_SCOPE, _RESOURCE_UNDAUNTED_SCOPE, _RESOURCE_ACTIVE_BAR_SCOPE)
            )
            if key == "max_health":
                searched_parts.append(_RESOURCE_JUGGERNAUT_SCOPE)
            if jewelry_state is not None:
                searched_parts.append(_RESOURCE_JEWELRY_STATIC_TRAIT_SCOPE)
            if jewelry_glyph_audit and jewelry_glyph_audit.objective_irrelevance_proven:
                searched_parts.append(_RESOURCE_JEWELRY_GLYPH_IRRELEVANCE_SCOPE)
            if weapon_audit and weapon_audit.objective_irrelevance_proven:
                searched_parts.append(_RESOURCE_WEAPON_IRRELEVANCE_SCOPE)
        elif reviewed_armor:
            searched_parts.append(_REVIEWED_ARMOR_SCOPE)
        searched_parts.extend((_MUNDUS_SCOPE, _FOOD_SCOPE, _POTION_SCOPE))
        searched = tuple(searched_parts)

        closed_axes = {_MUNDUS_DEFERRED_AXIS, _FOOD_DEFERRED_AXIS, _POTION_DEFERRED_AXIS}
        if evaluator.gear_denominator_proven:
            closed_axes.add(_GEAR_DEFERRED_AXIS)

        omitted_rows: list[str] = []
        jewelry_glyph_irrelevant = bool(
            resource_armor
            and jewelry_glyph_audit is not None
            and jewelry_glyph_audit.objective_irrelevance_proven
        )
        weapon_irrelevant = bool(
            resource_armor
            and weapon_audit is not None
            and weapon_audit.objective_irrelevance_proven
        )
        for axis in result.deferred_dynamic_axes:
            if axis in closed_axes:
                continue
            if axis == _EQUIPMENT_TRAIT_DEFERRED_AXIS:
                if resource_armor:
                    omitted_rows.append(
                        _RESOURCE_REMAINING_EQUIPMENT_TRAIT_AFTER_WEAPON_AXIS
                        if weapon_irrelevant
                        else _RESOURCE_REMAINING_EQUIPMENT_TRAIT_AXIS
                    )
                    continue
                if reviewed_armor:
                    omitted_rows.append(_REMAINING_EQUIPMENT_TRAIT_AXIS)
                    continue
            if axis == _GLYPH_DEFERRED_AXIS and resource_armor:
                if jewelry_glyph_irrelevant and weapon_irrelevant:
                    continue
                omitted_rows.append(
                    _RESOURCE_REMAINING_GLYPH_AFTER_JEWELRY_AXIS
                    if jewelry_glyph_irrelevant
                    else _RESOURCE_REMAINING_GLYPH_AXIS
                )
                continue
            if axis == _PASSIVE_DEFERRED_AXIS and resource_armor:
                omitted_rows.append(_RESOURCE_REMAINING_PASSIVE_AFTER_REVIEWED_BAR_AXIS)
                continue
            if axis == _SKILL_BAR_DEFERRED_AXIS and resource_armor:
                omitted_rows.append(_RESOURCE_REMAINING_SKILL_BAR_AXIS)
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
        jewelry_trait_denominator_proven = bool(
            not resource_armor
            or (
                jewelry_trait_catalog is not None
                and jewelry_trait_catalog.denominator_proven
                and len(jewelry_trait_catalog.states) == 1
            )
        )
        jewelry_glyph_denominator_proven = bool(
            not resource_armor
            or (
                jewelry_glyph_audit is not None
                and jewelry_glyph_audit.denominator_proven
            )
        )
        weapon_denominator_proven = bool(
            not resource_armor
            or (
                weapon_audit is not None
                and weapon_audit.denominator_proven
            )
        )
        denominator_proven = bool(
            result.structural_denominator_proven
            and evaluator.gear_denominator_proven
            and reviewed_armor_denominator_proven
            and resource_armor_denominator_proven
            and jewelry_trait_denominator_proven
            and jewelry_glyph_denominator_proven
            and weapon_denominator_proven
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
        jewelry_trait_unresolved = (
            tuple(jewelry_trait_catalog.unresolved)
            if jewelry_trait_catalog is not None
            else ()
        )
        jewelry_glyph_unresolved = (
            tuple(jewelry_glyph_audit.unresolved)
            if jewelry_glyph_audit is not None
            else ()
        )
        weapon_unresolved = (
            tuple(weapon_audit.unresolved)
            if weapon_audit is not None
            else ()
        )
        aggregate_unresolved = tuple(
            dict.fromkeys(
                str(item)
                for item in (
                    *gear_realization.unresolved,
                    *armor_unresolved,
                    *jewelry_trait_unresolved,
                    *jewelry_glyph_unresolved,
                    *weapon_unresolved,
                    *result.unresolved,
                )
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
            searched_armor_phrase = " × every proof-reduced armor weight + Divines/Infused + armor-glyph state"
            if jewelry_state is not None:
                searched_armor_phrase += " × the strongest reviewed static jewelry-trait continuation"
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
            weight_catalog = armor_catalog.weight_catalog
            explanation_rows.append(
                f"Scored {armor_count:,} proof-reduced resource armor weight/trait/glyph states for each of {len(gear_candidates):,} distinct gear witnesses before Mundus/food/potion selection."
            )
            explanation_rows.append(
                f"Armor-weight legality reviewed all {weight_catalog.raw_loadouts_reviewed:,} seven-slot Light/Medium/Heavy loadouts and preserved one continuation witness for each 1/2/3 armor-type count. Reviewed max-rank Undaunted Mettle is applied canonically to those witnesses; other passive ranks remain separate."
            )
            if key == "max_health":
                explanation_rows.append(
                    "Reviewed max-rank Juggernaut is applied canonically through the shared Heavy Armor piece-count resolver for every searched max-Health armor witness."
                )
            active_skills_reviewed = int(payload.get("resource_active_skills_reviewed") or 0)
            if key == "max_health":
                explanation_rows.append(
                    f"Reviewed {active_skills_reviewed:,} canonical active skills and proof-reduced the legal six-slot bar to the strongest Dark Vigor witness ({int(payload.get('resource_active_bar_shadow_slots') or 0)} Shadow slots); shared Nightblade passive math applies the scored bonus."
                )
            elif key == "max_magicka":
                explanation_rows.append(
                    f"Reviewed {active_skills_reviewed:,} canonical active skills and jointly reduced the legal six-slot bar for Magicka Flood plus Magicka Controller ({int(payload.get('resource_active_bar_siphoning_slots') or 0)} Siphoning, {int(payload.get('resource_active_bar_mages_guild_slots') or 0)} Mages Guild slots); shared passive resolvers apply the scored bonus."
                )
            elif key == "max_stamina":
                explanation_rows.append(
                    f"Reviewed {active_skills_reviewed:,} canonical active skills and proof-reduced the legal six-slot bar to the one-slot Magicka Flood trigger ({int(payload.get('resource_active_bar_siphoning_slots') or 0)} Siphoning slot); shared Nightblade passive math applies the scored bonus."
                )
            if jewelry_trait_catalog is not None:
                explanation_rows.append(
                    f"Jewelry static-trait review covered {jewelry_trait_catalog.raw_loadouts_reviewed:,} CP160 Gold Necklace/Ring/Ring loadouts and retained the strongest resource continuation at {jewelry_state.direct_delta if jewelry_state is not None else 0:g} flat resource. Glyph-dependent/unreviewed jewelry traits remain separate."
                )
            if jewelry_glyph_audit is not None:
                if jewelry_glyph_audit.objective_irrelevance_proven:
                    explanation_rows.append(
                        f"Reviewed all {jewelry_glyph_audit.glyphs_reviewed:,} canonical jewelry glyph names; none directly modifies {key}, so jewelry glyphs are proven irrelevant to this objective."
                    )
                elif jewelry_glyph_audit.relevant_glyphs:
                    explanation_rows.append(
                        "Jewelry glyph review found objective-relevant glyphs that are not yet searched: "
                        + ", ".join(jewelry_glyph_audit.relevant_glyphs)
                        + "."
                    )
            if weapon_audit is not None:
                if weapon_audit.objective_irrelevance_proven:
                    explanation_rows.append(
                        f"Reviewed all {weapon_audit.traits_reviewed:,} canonical weapon traits and {weapon_audit.enchantments_reviewed:,} canonical weapon enchantments; none can modify {key}, so both weapon families are proven irrelevant to this objective."
                    )
                elif weapon_audit.relevant_traits or weapon_audit.relevant_enchantments:
                    rows = (*weapon_audit.relevant_traits, *weapon_audit.relevant_enchantments)
                    explanation_rows.append(
                        "Weapon review found objective-relevant sources that are not yet searched: "
                        + ", ".join(rows)
                        + "."
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
                "Residual equipment traits/enchants, unreviewed skill-bar/morph interactions, Champion Points, remaining passives, and runtime-only axes remain separate unless coverage says otherwise.",
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
