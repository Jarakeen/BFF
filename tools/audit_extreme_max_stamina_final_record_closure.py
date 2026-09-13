from __future__ import annotations

"""Final proof-aware closure for the Update 50 Extreme Max Stamina record."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.combat_effect_semantics import GameUpdate
from minmax.emperor_passive_input_resolver import EmperorPassiveInputResolver
from minmax.gear_set_repository import GearSetRepository
from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from services.extreme_armor_resource_trait_glyph_state_service import ExtremeArmorResourceTraitGlyphStateService
from services.extreme_armor_resource_weight_trait_glyph_state_service import ExtremeArmorResourceWeightTraitGlyphStateService
from services.extreme_best_named_gear_resource_armor_mundus_food_potion_structural_stat_evaluator import ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_hypothetical_racial_progression_service import ExtremeHypotheticalRacialProgressionService
from services.extreme_hypothetical_undaunted_progression_service import ExtremeHypotheticalUndauntedProgressionService
from services.extreme_jewelry_resource_static_trait_state_service import ExtremeJewelryResourceStaticTraitStateService
from services.extreme_max_resource_armor_scoring_frontier_service import ExtremeMaxResourceArmorScoringFrontierService
from services.extreme_max_resource_named_gear_candidate_search_service import ExtremeMaxResourceNamedGearCandidateSearchService
from services.extreme_max_resource_ordinary_named_gear_search_service import ExtremeMaxResourceOrdinaryNamedGearSearchService
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealizationService
from services.extreme_named_gear_set_slot_eligibility_service import ExtremeNamedGearSetSlotEligibilityService
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_resource_active_skill_coverage_audit_service import ExtremeResourceActiveSkillCoverageAuditService
from services.extreme_resource_attribute_projection_service import ExtremeResourceAttributeProjectionService
from services.extreme_resource_champion_point_state_service import ExtremeResourceChampionPointStateService
from services.extreme_resource_class_route_dominance_projection_service import ExtremeResourceClassRouteDominanceProjectionService
from services.extreme_resource_equipment_trait_projection_coverage_service import ExtremeResourceEquipmentTraitProjectionCoverageService
from services.extreme_resource_mundus_projection_service import ExtremeResourceMundusProjectionService
from services.extreme_resource_passive_coverage_audit_service import ExtremeResourcePassiveCoverageAuditService
from services.extreme_resource_potion_projection_service import ExtremeResourcePotionProjectionService
from services.extreme_resource_provisioning_projection_service import ExtremeResourceProvisioningProjectionService
from services.extreme_resource_race_projection_service import ExtremeResourceRaceProjectionService
from services.extreme_resource_runtime_projection_coverage_service import ExtremeResourceRuntimeProjectionCoverageService
from services.extreme_structural_core_stat_record_service import ExtremeCanonicalStructuralStatEvaluator
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate
from services.extreme_weapon_resource_relevance_service import ExtremeWeaponResourceRelevanceService
from tools import audit_extreme_max_stamina_non_emperor_winner as winner_contract

OBJECTIVE = "max_stamina"
DEFAULT_INCUMBENT = 101930.0
DEFAULT_SPECIAL_BEST = 99716.0
DEFAULT_SPECIAL_SCORE_CALLS = 32080
EXPECTED_ORDINARY_FLAT_DELTA = 11974.0
EXPECTED_EMPEROR_HOME_KEEPS = 6
EXPECTED_EMPEROR_PERCENT = 0.75


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--incumbent", type=float, default=DEFAULT_INCUMBENT)
    parser.add_argument("--verified-special-best", type=float, default=DEFAULT_SPECIAL_BEST)
    parser.add_argument("--verified-special-score-calls", type=int, default=DEFAULT_SPECIAL_SCORE_CALLS)
    parser.add_argument("--non-emperor-benchmark", type=float, default=None)
    return parser


def _emperor_axis_proven() -> bool:
    table = dict(EmperorPassiveInputResolver.MAX_RESOURCE_PERCENT_BY_HOME_KEEPS)
    keys = tuple(sorted(int(key) for key in table))
    values = tuple(float(table[key]) for key in keys)
    monotonic = all(left <= right + 1e-12 for left, right in zip(values, values[1:]))
    return bool(
        keys == tuple(range(EXPECTED_EMPEROR_HOME_KEEPS + 1))
        and monotonic
        and float(table.get(EXPECTED_EMPEROR_HOME_KEEPS, -1.0)) == EXPECTED_EMPEROR_PERCENT
        and max(values, default=float("-inf")) == EXPECTED_EMPEROR_PERCENT
    )


def _realize_winner(topology_catalog, eligibility):
    eligibility_by_name = {str(row.name).casefold(): row for row in eligibility.sets}
    counts = tuple(count for _name, count in winner_contract.WINNING_PACKAGE)
    topology = next((row for row in topology_catalog.topologies if tuple(row.counts) == counts), None)
    if topology is None:
        raise RuntimeError(f"Canonical topology unavailable for winner counts={counts!r}")
    named = []
    for name, _count in winner_contract.WINNING_PACKAGE:
        row = eligibility_by_name.get(name.casefold())
        if row is None:
            raise RuntimeError(f"Canonical slot eligibility unavailable for winner set: {name}")
        named.append(row)
    realization = ExtremeNamedGearSetRealizationService.find_witness(topology, tuple(named))
    if realization is None:
        raise RuntimeError("Current Max Stamina winner has no legal physical named-gear witness")
    return realization


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    incumbent = float(args.incumbent)
    verified_special_best = float(args.verified_special_best)
    verified_special_score_calls = int(args.verified_special_score_calls)

    universe = ExtremeGlobalSearchUniverseService(database).build()
    race = ExtremeResourceRaceProjectionService(database).build(OBJECTIVE, tuple(universe.races))
    routes = ExtremeResourceClassRouteDominanceProjectionService(database).build(OBJECTIVE, tuple(universe.class_routes))
    attributes = ExtremeResourceAttributeProjectionService.build(OBJECTIVE, tuple(universe.attribute_allocations))
    mundus = ExtremeResourceMundusProjectionService(MundusRepository(database, game_update=U50_GAME_UPDATE, initialize=False)).build(OBJECTIVE)
    provisioning = ExtremeResourceProvisioningProjectionService(ProvisioningStaticRepository(database)).build(OBJECTIVE)
    potion = ExtremeResourcePotionProjectionService(PotionAvailabilityRepository(database, game_update=GameUpdate.U50)).build(OBJECTIVE)
    armor = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        OBJECTIVE, trait_glyph_service=ExtremeArmorResourceTraitGlyphStateService(database)
    ).build(OBJECTIVE)
    armor_frontier = ExtremeMaxResourceArmorScoringFrontierService.build(OBJECTIVE, armor)
    jewelry = ExtremeJewelryResourceStaticTraitStateService(database).build(OBJECTIVE)
    champion = ExtremeResourceChampionPointStateService(database).build(OBJECTIVE)
    passives = ExtremeResourcePassiveCoverageAuditService(database).build(OBJECTIVE)
    active_skills = ExtremeResourceActiveSkillCoverageAuditService(database).build(OBJECTIVE)
    equipment = ExtremeResourceEquipmentTraitProjectionCoverageService(database).build(OBJECTIVE)
    runtime = ExtremeResourceRuntimeProjectionCoverageService(database).build(OBJECTIVE)
    weapon = ExtremeWeaponResourceRelevanceService(database).build(OBJECTIVE)

    gear_repository = GearSetRepository(database)
    topology_catalog = ExtremeGearSetTopologyCatalogService(gear_repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(gear_repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(gear_repository).build(OBJECTIVE, breakpoints)
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    ordinary_service = ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=breakpoints, eligibility=eligibility, relevance=relevance
    )
    ordinary = ordinary_service.search(topology_catalog)
    topology_winners = tuple(row for row in ordinary.topologies if row.winner_found)
    ordinary_best = max((float(row.best_exact_flat_delta) for row in topology_winners), default=float("-inf"))
    ordinary_global_winners = sum(
        len(row.realizations)
        for row in topology_winners
        if row.best_exact_flat_delta is not None and abs(float(row.best_exact_flat_delta) - ordinary_best) <= 1e-9
    )

    special_candidates = ExtremeMaxResourceNamedGearCandidateSearchService(
        ordinary_service=ordinary_service, eligibility=eligibility
    ).search(topology_catalog)
    special_branch_count = len(special_candidates.classified_special.branches)
    special_subset_rows = len(special_candidates.special_subsets)
    special_winning_subsets = sum(1 for row in special_candidates.special_subsets if row.winner_found)

    realization = _realize_winner(topology_catalog, eligibility)
    canonical_race = ExtremeHypotheticalRacialProgressionService._canonical_skill_line_race(race.races[0])
    if not jewelry.states:
        raise RuntimeError("No canonical Max Stamina jewelry state")
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=ExtremeOptimizationService(database_path=database),
        progression_service=ExtremeHypotheticalUndauntedProgressionService(database),
    )
    factory = ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory(
        canonical_evaluator=canonical,
        mundus_repository=MundusRepository(database, game_update=U50_GAME_UPDATE, initialize=False),
        provisioning_repository=ProvisioningStaticRepository(database),
        potion_repository=PotionAvailabilityRepository(database, game_update=GameUpdate.U50),
        jewelry_state=jewelry.states[0],
    )

    scored = []
    for bar in ("front", "back"):
        structural = ExtremeStructuralCandidate(
            race=canonical_race,
            class_route=routes.routes[0],
            attributes=attributes.allocations[0],
            active_bar=bar,
        )
        for armor_state in armor_frontier.states:
            evaluator = factory(realization, armor_state)
            value, payload, raw = evaluator(OBJECTIVE, structural)
            effective, neutralized = winner_contract._reconcile(
                database,
                tuple(raw),
                build_payload=dict(payload.get("build") or {}),
                weapon_irrelevance=weapon.objective_irrelevance_proven,
            )
            scored.append((float(value), len(effective), bar, armor_state, dict(payload), tuple(raw), effective, neutralized))
    scored.sort(key=lambda row: (-row[0], row[1], row[2], row[3].identity))
    value, _effective_count, bar, armor_state, payload, raw, effective, neutralized = scored[0]
    active_buffs = tuple(str(item) for item in tuple(payload.get("active_buffs") or ()))
    emperor_marker = f"__emperor_home_keeps__:{EXPECTED_EMPEROR_HOME_KEEPS}"

    axes = {
        "structural_universe": bool(universe.structural_denominator_proven),
        "race_projection": bool(race.projection_complete and not race.unresolved),
        "class_route_projection": bool(routes.projection_complete and not routes.unresolved),
        "attribute_projection": bool(attributes.projection_complete and not attributes.unresolved),
        "mundus_projection": bool(mundus.projection_complete and not mundus.unresolved),
        "provisioning_projection": bool(provisioning.projection_complete and not provisioning.unresolved),
        "potion_irrelevance": bool(potion.objective_irrelevance_proven),
        "armor_denominator": bool(armor.denominator_proven and not armor.unresolved),
        "armor_frontier_reduction": bool(armor_frontier.reduction_proven),
        "jewelry_denominator": bool(jewelry.denominator_proven and not jewelry.unresolved),
        "champion_point_denominator": bool(champion.denominator_proven and not champion.unresolved),
        "passive_projection": bool(passives.projection_complete and not passives.unresolved),
        "active_skill_projection": bool(active_skills.projection_complete and not active_skills.unresolved),
        "equipment_trait_projection": bool(equipment.projection_complete and not equipment.unresolved),
        "runtime_projection": bool(runtime.projection_complete and not runtime.unresolved),
        "weapon_irrelevance": bool(weapon.objective_irrelevance_proven),
        "emperor_monotonic_max": _emperor_axis_proven(),
        "emperor_witness_active": emperor_marker in active_buffs,
        "incumbent_physical_witness": realization is not None,
        "incumbent_canonical_score": abs(value - incumbent) <= 1e-6,
        "incumbent_effective_unresolved_zero": not effective,
        "ordinary_exact_closure": bool(
            ordinary.ordinary_denominator_proven
            and not ordinary.unresolved
            and abs(ordinary_best - EXPECTED_ORDINARY_FLAT_DELTA) <= 1e-9
            and ordinary_global_winners > 0
        ),
        "special_denominator_classified": bool(
            special_candidates.candidate_reduction_proven
            and special_candidates.classified_special.denominator_classified
            and special_branch_count == 5
            and special_subset_rows > 0
            and special_winning_subsets > 0
        ),
        "special_numeric_ceiling": bool(
            verified_special_score_calls > 0 and verified_special_best <= incumbent + 1e-9
        ),
    }

    whole_unresolved = tuple(name for name, passed in axes.items() if not passed)
    denominator_closed = not whole_unresolved

    print("EXTREME MAX STAMINA FINAL WHOLE-RECORD CLOSURE")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print("legacy_exhaustive_whole_record_search_used=False")
    print("composition=proof_owned_axes+exact_ordinary_branch_and_bound+dominant_route+proof_reduced_armor+targeted_special_audit_evidence")
    print(f"incumbent={incumbent:.3f}")
    print(f"verified_special_best={verified_special_best:.3f}")
    print(f"verified_special_score_calls={verified_special_score_calls}")
    print("special_numeric_evidence_source=audit_extreme_max_stamina_special_challengers.py")
    if args.non_emperor_benchmark is not None:
        print(f"same_build_non_emperor_benchmark={float(args.non_emperor_benchmark):.3f}")
    print()
    print("PROOF AXES")
    for name, passed in axes.items():
        print(f"{name}={passed}")
    print()
    print("INCUMBENT WITNESS")
    print(f"canonical_value={value:.3f}")
    print("sets=" + ", ".join(f"{name} {count}pc" for name, count in zip(realization.set_names, realization.counts)))
    print(f"route_signature={tuple(routes.signature)!r}")
    print(f"active_bar={bar}")
    print(f"armor=types:{armor_state.armor_type_count} divines:{armor_state.divines_count} infused:{armor_state.infused_count}")
    print(f"mundus={payload.get('mundus')!r}")
    print(f"food={payload.get('food')!r}")
    print(f"potion={payload.get('potion')!r}")
    print(f"active_buffs={payload.get('active_buffs')!r}")
    print(f"raw_unresolved={len(raw)}")
    print(f"proof_neutralized_unresolved={len(neutralized)}")
    print(f"effective_unresolved={len(effective)}")
    print()
    print("DENOMINATOR EVIDENCE")
    print(f"source_class_routes={routes.source_route_count}")
    print(f"projected_route_signatures={routes.projected_route_count}")
    print(f"dominant_route_signature={tuple(routes.signature)!r}")
    print(f"armor_source_states={armor_frontier.source_state_count}")
    print(f"armor_retained_states={len(armor_frontier.states)}")
    print(f"armor_retained_weight_type_count={armor_frontier.retained_weight_type_count}")
    print(f"ordinary_best_exact_flat_delta={ordinary_best:.3f}")
    print(f"ordinary_global_winning_realizations={ordinary_global_winners}")
    print(f"special_branches={special_branch_count}")
    print(f"special_subset_rows={special_subset_rows}")
    print(f"special_winning_subsets={special_winning_subsets}")
    print(f"special_margin_vs_incumbent={verified_special_best - incumbent:+.3f}")
    print()
    print(f"whole_record_unresolved_count={len(whole_unresolved)}")
    for item in whole_unresolved:
        print(f"  unresolved: {item}")
    print(f"whole_record_denominator_closed={denominator_closed}")
    if denominator_closed:
        print(f"PROVEN_MAX_STAMINA_RECORD={incumbent:.3f}")
        print("RECORD_CONTEXT=Update 50 Extreme legal snapshot with active Emperor and 6 Home Keeps")
    return 0 if denominator_closed else 1


if __name__ == "__main__":
    raise SystemExit(main())
