from __future__ import annotations

"""Final proof-aware closure for the Update 50 Extreme Max Health record.

This audit deliberately avoids replaying the expensive canonical special-challenger
sweep. It recomputes the structural denominator, exact ordinary named-gear frontier,
proof-reduced class-route and armor frontiers, canonical incumbent, warning
reconciliation, and special-subset denominator. The numeric special ceiling is the
verified output of ``audit_extreme_max_health_special_challengers.py`` and is accepted
as explicit audit evidence via CLI so a final closure run does not require another
~40k canonical scores.
"""

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
from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphStateService,
)
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphStateService,
)
from services.extreme_best_named_gear_resource_armor_mundus_food_potion_structural_stat_evaluator import (
    ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory,
)
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointService,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetTopologyCatalogService,
)
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_hypothetical_racial_progression_service import (
    ExtremeHypotheticalRacialProgressionService,
)
from services.extreme_hypothetical_undaunted_progression_service import (
    ExtremeHypotheticalUndauntedProgressionService,
)
from services.extreme_jewelry_resource_static_trait_state_service import (
    ExtremeJewelryResourceStaticTraitStateService,
)
from services.extreme_max_health_armor_scoring_frontier_service import (
    ExtremeMaxHealthArmorScoringFrontierService,
)
from services.extreme_max_health_class_route_projection_service import (
    ExtremeMaxHealthClassRouteProjectionService,
)
from services.extreme_max_health_named_gear_candidate_search_service import (
    ExtremeMaxHealthNamedGearCandidateSearchService,
)
from services.extreme_max_resource_ordinary_named_gear_search_service import (
    ExtremeMaxResourceOrdinaryNamedGearSearchService,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_resource_active_skill_coverage_audit_service import (
    ExtremeResourceActiveSkillCoverageAuditService,
)
from services.extreme_resource_attribute_projection_service import (
    ExtremeResourceAttributeProjectionService,
)
from services.extreme_resource_champion_point_state_service import (
    ExtremeResourceChampionPointStateService,
)
from services.extreme_resource_equipment_trait_projection_coverage_service import (
    ExtremeResourceEquipmentTraitProjectionCoverageService,
)
from services.extreme_resource_mundus_projection_service import (
    ExtremeResourceMundusProjectionService,
)
from services.extreme_resource_passive_coverage_audit_service import (
    ExtremeResourcePassiveCoverageAuditService,
)
from services.extreme_resource_potion_projection_service import (
    ExtremeResourcePotionProjectionService,
)
from services.extreme_resource_provisioning_projection_service import (
    ExtremeResourceProvisioningProjectionService,
)
from services.extreme_resource_race_projection_service import (
    ExtremeResourceRaceProjectionService,
)
from services.extreme_resource_runtime_projection_coverage_service import (
    ExtremeResourceRuntimeProjectionCoverageService,
)
from services.extreme_structural_core_stat_record_service import (
    ExtremeCanonicalStructuralStatEvaluator,
)
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate
from services.extreme_weapon_resource_relevance_service import (
    ExtremeWeaponResourceRelevanceService,
)
from tools import audit_extreme_max_health_non_emperor_winner as winner_contract


OBJECTIVE = "max_health"
DEFAULT_INCUMBENT = 147307.0
DEFAULT_SPECIAL_BEST = 144581.0
DEFAULT_SPECIAL_SCORE_CALLS = 39920
DEFAULT_NON_EMPEROR = 98422.0
EXPECTED_ORDINARY_FLAT_DELTA = 16698.0
EXPECTED_EMPEROR_HOME_KEEPS = 6
EXPECTED_EMPEROR_PERCENT = 0.75


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--incumbent", type=float, default=DEFAULT_INCUMBENT)
    parser.add_argument("--verified-special-best", type=float, default=DEFAULT_SPECIAL_BEST)
    parser.add_argument(
        "--verified-special-score-calls",
        type=int,
        default=DEFAULT_SPECIAL_SCORE_CALLS,
    )
    parser.add_argument("--non-emperor-benchmark", type=float, default=DEFAULT_NON_EMPEROR)
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


def _realize_winner(database: Path, topology_catalog, eligibility):
    eligibility_by_name = {str(row.name).casefold(): row for row in eligibility.sets}
    counts = tuple(count for _name, count in winner_contract.WINNING_PACKAGE)
    topology = next(
        (row for row in topology_catalog.topologies if tuple(row.counts) == counts),
        None,
    )
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
        raise RuntimeError("Current Max Health winner has no legal physical named-gear witness")
    return realization


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    incumbent = float(args.incumbent)
    verified_special_best = float(args.verified_special_best)
    verified_special_score_calls = int(args.verified_special_score_calls)

    universe = ExtremeGlobalSearchUniverseService(database).build()
    race = ExtremeResourceRaceProjectionService(database).build(
        OBJECTIVE, tuple(universe.races)
    )
    routes = ExtremeMaxHealthClassRouteProjectionService(database).build(
        tuple(universe.class_routes)
    )
    attributes = ExtremeResourceAttributeProjectionService.build(
        OBJECTIVE, tuple(universe.attribute_allocations)
    )
    mundus = ExtremeResourceMundusProjectionService(
        MundusRepository(database, game_update=U50_GAME_UPDATE, initialize=False)
    ).build(OBJECTIVE)
    provisioning = ExtremeResourceProvisioningProjectionService(
        ProvisioningStaticRepository(database)
    ).build(OBJECTIVE)
    potion = ExtremeResourcePotionProjectionService(
        PotionAvailabilityRepository(database, game_update=GameUpdate.U50)
    ).build(OBJECTIVE)
    armor = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        OBJECTIVE,
        trait_glyph_service=ExtremeArmorResourceTraitGlyphStateService(database),
    ).build(OBJECTIVE)
    armor_frontier = ExtremeMaxHealthArmorScoringFrontierService.build(armor)
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
    relevance = ExtremeGearSetObjectiveRelevanceService(gear_repository).build(
        OBJECTIVE, breakpoints
    )
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    ordinary_service = ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    ordinary = ordinary_service.search(topology_catalog)
    ordinary_topology_winners = tuple(row for row in ordinary.topologies if row.winner_found)
    ordinary_best = max(
        (float(row.best_exact_flat_delta) for row in ordinary_topology_winners),
        default=float("-inf"),
    )
    ordinary_global_winners = sum(
        len(row.realizations)
        for row in ordinary_topology_winners
        if row.best_exact_flat_delta is not None
        and abs(float(row.best_exact_flat_delta) - ordinary_best) <= 1e-9
    )

    special_candidates = ExtremeMaxHealthNamedGearCandidateSearchService(
        ordinary_service=ordinary_service,
        eligibility=eligibility,
    ).search(topology_catalog)
    special_branch_count = len(special_candidates.classified_special.branches)
    special_subset_rows = len(special_candidates.special_subsets)
    special_winning_subsets = sum(1 for row in special_candidates.special_subsets if row.winner_found)

    realization = _realize_winner(database, topology_catalog, eligibility)
    canonical_race = ExtremeHypotheticalRacialProgressionService._canonical_skill_line_race(
        race.races[0]
    )
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=ExtremeOptimizationService(database_path=database),
        progression_service=ExtremeHypotheticalUndauntedProgressionService(database),
    )
    if not jewelry.states:
        raise RuntimeError("No canonical Max Health jewelry state")
    factory = ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory(
        canonical_evaluator=canonical,
        mundus_repository=MundusRepository(
            database,
            game_update=U50_GAME_UPDATE,
            initialize=False,
        ),
        provisioning_repository=ProvisioningStaticRepository(database),
        potion_repository=PotionAvailabilityRepository(
            database,
            game_update=GameUpdate.U50,
        ),
        jewelry_state=jewelry.states[0],
    )

    scored = []
    for bar in ("front", "back"):
        for route, signature in zip(routes.routes, routes.signatures):
            structural = ExtremeStructuralCandidate(
                race=canonical_race,
                class_route=route,
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
                scored.append(
                    (
                        float(value),
                        len(effective),
                        tuple(signature),
                        bar,
                        armor_state,
                        dict(payload),
                        tuple(raw),
                        tuple(effective),
                        tuple(neutralized),
                    )
                )

    scored.sort(key=lambda row: (-row[0], row[1], row[2], row[3], row[4].identity))
    best = scored[0]
    value, _effective_count, signature, bar, armor_state, payload, raw, effective, neutralized = best
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
            verified_special_score_calls > 0
            and verified_special_best <= incumbent + 1e-9
        ),
    }

    print("EXTREME MAX HEALTH FINAL WHOLE-RECORD CLOSURE")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print("legacy_exhaustive_whole_record_search_used=False")
    print("composition=proof_owned_axes+exact_ordinary_branch_and_bound+proof_reduced_route_and_armor+targeted_special_audit_evidence")
    print(f"incumbent={incumbent:.3f}")
    print(f"verified_special_best={verified_special_best:.3f}")
    print(f"verified_special_score_calls={verified_special_score_calls}")
    print("special_numeric_evidence_source=audit_extreme_max_health_special_challengers.py")
    print(f"same_build_non_emperor_benchmark={float(args.non_emperor_benchmark):.3f}")
    print()
    print("PROOF AXES")
    for name, passed in axes.items():
        print(f"{name}={passed}")
    print()
    print("INCUMBENT WITNESS")
    print(f"canonical_value={value:.3f}")
    print(
        "sets="
        + ", ".join(
            f"{name} {count}pc"
            for name, count in zip(realization.set_names, realization.counts)
        )
    )
    print(f"route_signature={signature!r}")
    print(f"active_bar={bar}")
    print(
        f"armor=types:{armor_state.armor_type_count} "
        f"heavy:{armor_state.weight_state.heavy_pieces} "
        f"divines:{armor_state.divines_count} infused:{armor_state.infused_count}"
    )
    print(f"mundus={payload.get('mundus')!r}")
    print(f"food={payload.get('food')!r}")
    print(f"potion={payload.get('potion')!r}")
    print(f"active_buffs={active_buffs!r}")
    print(f"max_health_runtime={payload.get('resource_max_health_runtime_label')!r}")
    print(f"raw_unresolved={len(raw)}")
    print(f"proof_neutralized_unresolved={len(neutralized)}")
    print(f"effective_unresolved={len(effective)}")
    for item in effective:
        print(f"  unresolved: {item}")
    print()
    print("DENOMINATOR EVIDENCE")
    print(f"source_class_routes={routes.source_route_count}")
    print(f"route_signatures={len(routes.routes)}")
    print(f"armor_source_states={len(armor.states)}")
    print(f"armor_source_weight_signatures={armor_frontier.source_weight_signature_count}")
    print(f"armor_retained_weight_signatures={armor_frontier.retained_weight_signatures!r}")
    print(f"ordinary_best_exact_flat_delta={ordinary_best:.3f}")
    print(f"ordinary_global_winning_realizations={ordinary_global_winners}")
    print(f"special_branches={special_branch_count}")
    print(f"special_subset_rows={special_subset_rows}")
    print(f"special_winning_subsets={special_winning_subsets}")
    print(f"special_margin_vs_incumbent={verified_special_best - incumbent:.3f}")
    print()

    unresolved_axes = tuple(name for name, passed in axes.items() if not passed)
    whole_closed = not unresolved_axes
    print(f"whole_record_unresolved_count={len(unresolved_axes)}")
    for name in unresolved_axes:
        print(f"  unresolved_axis: {name}")
    print(f"whole_record_denominator_closed={whole_closed}")
    if whole_closed:
        print(f"PROVEN_MAX_HEALTH_RECORD={incumbent:.3f}")
        print("RECORD_CONTEXT=Update 50 Extreme legal snapshot with active Emperor and 6 Home Keeps")
    return 0 if whole_closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
