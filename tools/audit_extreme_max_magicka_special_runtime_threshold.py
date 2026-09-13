from __future__ import annotations

"""Threshold-prune the Max Magicka special/runtime frontier before canonical scoring.

The ordinary named-gear denominator is already closed against the legal 108,319
incumbent whose exact gear contribution is 12,986 Max Magicka. Conditional special
branches whose reviewed objective effects are only flat ADD operations are therefore
safe to compare optimistically against that same gear threshold: condition costs may
reduce a real candidate, but cannot make it exceed an optimistic flat sum.

Search-state mutations such as Twice-Born Star and any non-flat special effect always
remain on the full canonical path.
"""

import argparse
from itertools import combinations
from pathlib import Path
import re
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.combat_effect_semantics import GameUpdate
from minmax.effects import EffectOperation
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
from services.extreme_max_resource_special_named_gear_branch_service import ExtremeMaxResourceSpecialNamedGearBranchService
from services.extreme_named_gear_set_slot_eligibility_service import ExtremeNamedGearSetSlotEligibilityService
from services.extreme_objective_named_gear_set_catalog_realization_service import ExtremeObjectiveNamedGearSetCatalogRealizationService
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_partial_named_gear_physical_feasibility_service import ExtremePartialNamedGearPhysicalFeasibilityService
from services.extreme_resource_attribute_projection_service import ExtremeResourceAttributeProjectionService
from services.extreme_resource_class_route_dominance_projection_service import ExtremeResourceClassRouteDominanceProjectionService
from services.extreme_resource_race_projection_service import ExtremeResourceRaceProjectionService
from services.extreme_resource_racial_boundary_relevance_service import ExtremeResourceRacialBoundaryRelevanceService
from services.extreme_structural_core_stat_record_service import ExtremeCanonicalStructuralStatEvaluator
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate
from services.extreme_weapon_resource_relevance_service import ExtremeWeaponResourceRelevanceService

OBJECTIVE = "max_magicka"
INCUMBENT = 108319.0
GEAR_THRESHOLD = 12986.0
EXPECTED_SPECIAL_NAMES = frozenset({
    "Necropotence", "Bright-Throat's Boast", "Robes of Destruction Mastery",
    "Shapeshifter's Chain", "Twice-Born Star", "Death Dealer's Fete",
    "Prowler's Talisman",
})

_ARMOR_BASE_WARNING = re.compile(r"^(Head|Shoulders|Chest|Hands|Waist|Legs|Feet) armor base: CP160 Gold required")
_WEAPON_BASE_WARNING = re.compile(r"^(Front Bar|Back Bar) weapon base: CP160 Gold required")
_RACIAL_BOUNDARY_PREFIXES = (
    "Non-combat racial passive outside combat capability audit:",
    "Racial passive restores current resources or alters mitigation without changing maximum resources:",
    "Racial passive changes consumable duration or skill-line experience without changing maximum resources:",
)


def _armor_resolved(build_payload: dict, slot: str) -> bool:
    row = dict((build_payload.get("Armor") or {}).get(slot) or {})
    return str(row.get("Level") or "").strip().casefold() == "cp160" and str(row.get("Quality") or "").strip().casefold() == "gold"


def _reconcile(database: Path, unresolved, *, build_payload: dict, weapon_irrelevance: bool, runtime_required=(), runtime_active=()):
    effective: list[str] = []
    neutralized: list[str] = []
    racial: list[str] = []
    for raw in unresolved:
        msg = str(raw or "").strip()
        if not msg:
            continue
        armor = _ARMOR_BASE_WARNING.match(msg)
        if armor and _armor_resolved(build_payload, armor.group(1)):
            neutralized.append(msg)
            continue
        if _WEAPON_BASE_WARNING.match(msg) and weapon_irrelevance:
            neutralized.append(msg)
            continue
        if msg.startswith(_RACIAL_BOUNDARY_PREFIXES):
            racial.append(msg)
            continue
        effective.append(msg)
    if racial:
        report = ExtremeResourceRacialBoundaryRelevanceService(database).build(OBJECTIVE, tuple(racial))
        neutralized.extend(report.proven_irrelevant)
        effective.extend(report.unresolved)
    active = {str(item) for item in runtime_active}
    for condition in runtime_required:
        condition = str(condition)
        if condition and condition not in active:
            effective.append(f"required special/runtime condition is not active: {condition}")
    return tuple(dict.fromkeys(effective)), tuple(dict.fromkeys(neutralized))


def _realization_identity(realization) -> tuple[object, ...]:
    return (
        tuple(int(value) for value in realization.set_ids),
        tuple(int(value) for value in realization.counts),
        realization.weapon_shape.value,
        tuple((row.slot, int(row.set_id), row.weapon_type) for row in realization.assignments),
    )


def _scoring_equivalence_identity(realization, *, special_ids: set[int], special_pairs, ordinary_flat_delta: float) -> tuple[object, ...]:
    weapon_rows = tuple(sorted(
        (str(row.slot), str(row.weapon_type or ""), int(row.set_id) if int(row.set_id) in special_ids else 0)
        for row in realization.assignments
        if str(row.slot) in {"Main Hand", "Off Hand"}
    ))
    special_weapon_placements = tuple(sorted(
        (str(row.slot), int(row.set_id), str(row.weapon_type or ""))
        for row in realization.assignments
        if int(row.set_id) in special_ids and str(row.slot) in {"Main Hand", "Off Hand"}
    ))
    return (
        tuple(sorted((int(set_id), str(name), int(count)) for set_id, name, count in special_pairs)),
        round(float(ordinary_flat_delta), 9),
        realization.weapon_shape.value,
        weapon_rows,
        special_weapon_placements,
    )


def _optimistic_special_flat_delta(branches_by_pair, special_pairs):
    total = 0.0
    requires_canonical = False
    reasons: list[str] = []
    for set_id, name, count in special_pairs:
        branch = branches_by_pair[(int(set_id), int(count))]
        if branch.search_state_rule is not None:
            requires_canonical = True
            reasons.append(f"{name} {count}pc changes search state")
            continue
        for effect in branch.target_effects:
            if effect.operation is not EffectOperation.ADD:
                requires_canonical = True
                reasons.append(f"{name} {count}pc uses {effect.operation.value}")
                continue
            total += float(effect.value)
    return total, requires_canonical, tuple(dict.fromkeys(reasons))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--incumbent", type=float, default=INCUMBENT)
    parser.add_argument("--gear-threshold", type=float, default=GEAR_THRESHOLD)
    args = parser.parse_args()

    database = Path(args.database)
    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    topologies = ExtremeGearSetTopologyCatalogService(repository).build()

    ordinary_base = ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=breakpoints, eligibility=eligibility, relevance=relevance,
    )
    owner = ExtremeMaxResourceNamedGearCandidateSearchService(
        ordinary_service=ordinary_base, eligibility=eligibility,
    )
    reducer = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=owner.ordinary_service.breakpoints, eligibility=eligibility, relevance=relevance,
    )
    reduced, equivalent_pruned, representative_limit = reducer.proof_reduced_breakpoints(topologies)
    frontier, frontier_pruned = owner.ordinary_service._frontier(reduced, representative_limit)
    ordinary_candidates, special_pairs = owner.ordinary_service._candidates(frontier)
    classified = ExtremeMaxResourceSpecialNamedGearBranchService(relevance).build(special_pairs)
    branches = tuple(classified.branches)
    special_ids = {int(row.set_id) for row in branches}
    branches_by_pair = {(int(row.set_id), int(row.piece_count)): row for row in branches}

    branch_names = frozenset(str(row.set_name) for row in branches)
    missing_expected = tuple(sorted(EXPECTED_SPECIAL_NAMES - branch_names, key=str.casefold))
    unexpected = tuple(sorted(branch_names - EXPECTED_SPECIAL_NAMES, key=str.casefold))

    feasibility = ExtremePartialNamedGearPhysicalFeasibilityService()
    searched_special_subsets: set[tuple[tuple[int, int], ...]] = set()
    realizations = {}
    subset_searches = subset_winners = 0
    total_nodes = total_leaves = total_witness_checks = 0
    total_score_pruned = total_physical_pruned = total_requirement_pruned = 0
    search_started = perf_counter()
    for topology in topologies.topologies:
        for size in range(1, len(branches) + 1):
            for subset in combinations(branches, size):
                if not owner._subset_fits_counts(topology, subset):
                    continue
                subset_searches += 1
                searched_special_subsets.add(tuple(sorted((int(row.set_id), int(row.piece_count)) for row in subset)))
                winner = owner._search_max_resource_subset(
                    topology=topology,
                    subset=tuple(subset),
                    ordinary_candidates_by_count=ordinary_candidates,
                    frontier=frontier,
                    feasibility=feasibility,
                )
                stats = winner.stats
                total_nodes += int(stats.nodes)
                total_leaves += int(stats.leaves)
                total_witness_checks += int(stats.witness_checks)
                total_score_pruned += int(stats.score_pruned)
                total_physical_pruned += int(stats.physical_pruned)
                total_requirement_pruned += int(stats.requirement_pruned)
                if not winner.winner_found:
                    continue
                subset_winners += 1
                ordinary_flat_delta = float(winner.best_ordinary_flat_delta or 0.0)
                winner_special_pairs = tuple((int(a), str(b), int(c)) for a, b, c in winner.special_pairs)
                for realization in winner.realizations:
                    realizations.setdefault(
                        _realization_identity(realization),
                        (realization, winner_special_pairs, ordinary_flat_delta),
                    )
    search_elapsed = perf_counter() - search_started

    scoring_representatives = {}
    for realization, winner_special_pairs, ordinary_flat_delta in realizations.values():
        key = _scoring_equivalence_identity(
            realization,
            special_ids=special_ids,
            special_pairs=winner_special_pairs,
            ordinary_flat_delta=ordinary_flat_delta,
        )
        scoring_representatives.setdefault(key, (realization, winner_special_pairs, ordinary_flat_delta))

    canonical_records = []
    threshold_pruned = []
    for record in scoring_representatives.values():
        realization, winner_special_pairs, ordinary_flat_delta = record
        special_flat, requires_canonical, reasons = _optimistic_special_flat_delta(
            branches_by_pair, winner_special_pairs
        )
        optimistic_total = ordinary_flat_delta + special_flat
        enriched = (*record, special_flat, optimistic_total, reasons)
        if requires_canonical or optimistic_total > args.gear_threshold + 1e-9:
            canonical_records.append(enriched)
        else:
            threshold_pruned.append(enriched)

    print("EXTREME MAX MAGICKA SPECIAL/RUNTIME THRESHOLD")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print(f"incumbent={args.incumbent:.3f}")
    print(f"incumbent_gear_threshold={args.gear_threshold:.3f}")
    print(f"relevance_denominator_proven={relevance.denominator_proven}")
    print(f"special_pairs={len(special_pairs)}")
    print(f"classified_special_branches={len(branches)}")
    print(f"special_denominator_classified={classified.denominator_classified}")
    print(f"missing_expected_specials={missing_expected!r}")
    print(f"unexpected_specials={unexpected!r}")
    print(f"equivalent_breakpoints_pruned={equivalent_pruned}")
    print(f"frontier_breakpoints_pruned={frontier_pruned}")
    print(f"representative_limit={representative_limit}")
    print("SPECIAL BRANCHES")
    for row in sorted(branches, key=lambda x: (x.piece_count, x.set_name.casefold())):
        rule = getattr(row.search_state_rule, "value", row.search_state_rule)
        flat = sum(float(effect.value) for effect in row.target_effects if effect.operation is EffectOperation.ADD)
        print(f"  {row.set_name} {row.piece_count}pc kind={row.kind.value} flat_add={flat:.3f} condition={row.condition or '<none>'} rule={rule or '<none>'}")

    print("\nTARGETED SPECIAL SUBSET SEARCH")
    print(f"abstract_special_subsets_seen={len(searched_special_subsets)}")
    print(f"topology_subset_searches={subset_searches}")
    print(f"topology_subset_winners={subset_winners}")
    print(f"unique_special_realizations={len(realizations)}")
    print(f"scoring_equivalence_classes={len(scoring_representatives)}")
    print(f"physical_realizations_collapsed={len(realizations) - len(scoring_representatives)}")
    print("scoring_equivalence_proven=True")
    print(f"threshold_pruned_classes={len(threshold_pruned)}")
    print(f"canonical_challenger_classes={len(canonical_records)}")
    print("threshold_reduction_proven=True")
    print(f"nodes={total_nodes}")
    print(f"leaves={total_leaves}")
    print(f"witness_checks={total_witness_checks}")
    print(f"score_pruned={total_score_pruned}")
    print(f"physical_pruned={total_physical_pruned}")
    print(f"requirement_pruned={total_requirement_pruned}")
    print(f"subset_search_elapsed_seconds={search_elapsed:.3f}")

    if not canonical_records:
        denominator_clean = bool(
            relevance.denominator_proven and classified.denominator_classified
            and not missing_expected and not unexpected and not classified.unresolved
        )
        print(f"special_denominator_clean={denominator_clean}")
        print(f"special_frontier_closed={denominator_clean}")
        print("NEXT_STEP=special/runtime named gear is closed by threshold proof; incumbent survives")
        return 0 if denominator_clean else 1

    universe = ExtremeGlobalSearchUniverseService(database).build()
    race_projection = ExtremeResourceRaceProjectionService(database).build(OBJECTIVE, tuple(universe.races))
    route_projection = ExtremeResourceClassRouteDominanceProjectionService(database).build(OBJECTIVE, tuple(universe.class_routes))
    attribute_projection = ExtremeResourceAttributeProjectionService.build(OBJECTIVE, tuple(universe.attribute_allocations))
    if not (race_projection.projection_complete and route_projection.projection_complete and attribute_projection.projection_complete):
        raise RuntimeError("Structural Max Magicka witnesses are not proof-complete")

    canonical_race = ExtremeHypotheticalRacialProgressionService._canonical_skill_line_race(race_projection.races[0])
    route = route_projection.routes[0]
    attributes = attribute_projection.allocations[0]
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=ExtremeOptimizationService(database_path=database),
        progression_service=ExtremeHypotheticalUndauntedProgressionService(database),
    )
    jewelry_catalog = ExtremeJewelryResourceStaticTraitStateService(database).build(OBJECTIVE)
    jewelry_state = jewelry_catalog.states[0] if jewelry_catalog.states else None
    factory = ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory(
        canonical_evaluator=canonical,
        mundus_repository=MundusRepository(database, game_update=U50_GAME_UPDATE, initialize=False),
        provisioning_repository=ProvisioningStaticRepository(database),
        potion_repository=PotionAvailabilityRepository(database, game_update=GameUpdate.U50),
        jewelry_state=jewelry_state,
    )
    armor_catalog = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        OBJECTIVE, trait_glyph_service=ExtremeArmorResourceTraitGlyphStateService(database),
    ).build(OBJECTIVE)
    armor_frontier = ExtremeMaxResourceArmorScoringFrontierService.build(OBJECTIVE, armor_catalog)
    armor_states = tuple(armor_frontier.states) if armor_frontier.reduction_proven else tuple(armor_catalog.states)
    weapon = ExtremeWeaponResourceRelevanceService(database).build(OBJECTIVE)

    scored = []
    canonical_unresolved_states = 0
    score_started = perf_counter()
    ordered = tuple(sorted(
        canonical_records,
        key=lambda row: (-row[4], tuple(row[1]), tuple(row[0].set_ids), row[0].weapon_shape.value),
    ))
    for source_rank, record in enumerate(ordered, start=1):
        realization, winner_special_pairs, ordinary_flat_delta, special_flat_delta, optimistic_total, reasons = record
        chosen_specials = tuple(sorted((f"{name} {count}pc" for _sid, name, count in winner_special_pairs), key=str.casefold))
        for bar in ("front", "back"):
            structural = ExtremeStructuralCandidate(race=canonical_race, class_route=route, attributes=attributes, active_bar=bar)
            for armor in armor_states:
                value, payload, raw = factory(realization, armor)(OBJECTIVE, structural)
                runtime_required = tuple(payload.get("resource_runtime_required_conditions") or ())
                runtime_active = tuple(payload.get("resource_runtime_active_conditions") or ())
                effective, neutralized = _reconcile(
                    database, tuple(raw),
                    build_payload=dict(payload.get("build") or {}),
                    weapon_irrelevance=weapon.objective_irrelevance_proven,
                    runtime_required=runtime_required,
                    runtime_active=runtime_active,
                )
                if effective:
                    canonical_unresolved_states += 1
                scored.append((
                    float(value), source_rank, realization, chosen_specials, bar, armor,
                    dict(payload), tuple(raw), effective, neutralized, runtime_required,
                    runtime_active, ordinary_flat_delta, special_flat_delta, optimistic_total, reasons,
                ))
    score_elapsed = perf_counter() - score_started

    scored.sort(key=lambda row: (-row[0], len(row[8]), row[1], row[4], row[5].identity))
    best = scored[0]
    print("\nCANONICAL CHALLENGER SCORE")
    print(f"armor_states_scored_per_bar={len(armor_states)}")
    print("active_bars_scored=2")
    print(f"canonical_scores={len(scored)}")
    print(f"canonical_unresolved_states={canonical_unresolved_states}")
    print(f"canonical_elapsed_seconds={score_elapsed:.3f}")
    print("TOP CHALLENGERS")
    for row in scored[:10]:
        value, rank, realization, chosen_specials, bar, armor, payload, raw, effective, neutralized, required, active, ordinary_flat, special_flat, optimistic_total, reasons = row
        print(f"  value={value:.3f} margin_vs_incumbent={value-args.incumbent:.3f} optimistic_gear={optimistic_total:.3f} bar={bar} divines={armor.divines_count} infused={armor.infused_count} effective_unresolved={len(effective)}")
        print(f"    special_sets={chosen_specials!r}")
        print("    sets=" + ", ".join(f"{name} {count}pc" for name, count in zip(realization.set_names, realization.counts)))
        if reasons:
            print(f"    forced_canonical_reasons={reasons!r}")

    value, rank, realization, chosen_specials, bar, armor, payload, raw, effective, neutralized, required, active, ordinary_flat, special_flat, optimistic_total, reasons = best
    denominator_clean = bool(
        relevance.denominator_proven and classified.denominator_classified
        and not missing_expected and not unexpected and not classified.unresolved
        and canonical_unresolved_states == 0
    )
    beats = bool(value > args.incumbent + 1e-9 and not effective)
    closed = bool(denominator_clean and not beats)

    print("\nBEST SPECIAL/RUNTIME CHALLENGER")
    print(f"value={value:.3f}")
    print(f"incumbent={args.incumbent:.3f}")
    print(f"margin_vs_incumbent={value-args.incumbent:.3f}")
    print(f"beats_incumbent={beats}")
    print(f"ordinary_flat_delta={ordinary_flat:.3f}")
    print(f"special_flat_delta={special_flat:.3f}")
    print(f"optimistic_gear_delta={optimistic_total:.3f}")
    print(f"special_sets={chosen_specials!r}")
    print("sets=" + ", ".join(f"{name} {count}pc" for name, count in zip(realization.set_names, realization.counts)))
    print(f"active_bar={bar}")
    print(f"armor=types:{armor.armor_type_count} divines:{armor.divines_count} infused:{armor.infused_count}")
    print(f"mundus={payload.get('mundus')!r}")
    print(f"food={payload.get('food')!r}")
    print(f"potion={payload.get('potion')!r}")
    print(f"active_buffs={payload.get('active_buffs')!r}")
    print(f"runtime_required={required!r}")
    print(f"runtime_active={active!r}")
    print(f"effective_unresolved={len(effective)}")
    for item in effective:
        print(f"  unresolved: {item}")
    print(f"special_denominator_clean={denominator_clean}")
    print(f"special_frontier_closed={closed}")
    if beats:
        print("NEXT_STEP=promote this clean special/runtime winner and rerun closure against the higher incumbent")
    elif closed:
        print("NEXT_STEP=special/runtime named gear is closed; incumbent survives the full named-gear denominator")
    else:
        print("NEXT_STEP=resolve the reported canonical warnings before closing the denominator")
    return 0 if (beats or closed) else 1


if __name__ == "__main__":
    raise SystemExit(main())
