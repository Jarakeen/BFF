from __future__ import annotations

"""Canonical-score targeted Max Health special/runtime named-gear challengers.

This is challenger discovery, not final whole-record closure.  The ordinary branch
has already established the strongest clean route signature and proved that the
three retained Max Health armor-weight signatures all contribute the same reviewed
+16% total from Juggernaut + Undaunted Mettle.  This audit therefore scores every
proof-reduced special-subset named-gear winner on:

* the winning Max Health route signature (Bone Tyrant + Green Balance + Shadow),
* one deterministic +16% armor-weight witness, and
* all eight Divines/Infused + Health-glyph states.

Special conditions are not reimplemented here.  The canonical resource evaluator
materializes runtime-condition witnesses, gear condition context, Max Health runtime
passives, and Twice-Born Star's second-Mundus execution through the existing
production services.
"""

import argparse
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_resource_attribute_projection_service import (
    ExtremeResourceAttributeProjectionService,
)
from services.extreme_resource_race_projection_service import (
    ExtremeResourceRaceProjectionService,
)
from services.extreme_structural_core_stat_record_service import (
    ExtremeCanonicalStructuralStatEvaluator,
)
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate


OBJECTIVE = "max_health"
INCUMBENT = 147307.0
WINNING_ROUTE_SIGNATURE = ("bone_tyrant", "green_balance", "shadow")
# All three retained signatures produce the same reviewed +16% health multiplier.
DISCOVERY_WEIGHT_SIGNATURE = (3, 5)  # (armor_type_count, heavy_pieces)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--incumbent", type=float, default=INCUMBENT)
    parser.add_argument("--top", type=int, default=20)
    return parser


def _realization_identity(realization) -> tuple[object, ...]:
    return (
        tuple(int(value) for value in realization.set_ids),
        tuple(int(value) for value in realization.counts),
        realization.weapon_shape.value,
        tuple((row.slot, int(row.set_id), row.weapon_type) for row in realization.assignments),
    )


def _armor_identity(state) -> tuple[object, ...]:
    return tuple(state.identity)


def _sets_label(realization) -> str:
    return ", ".join(
        f"{name} {count}pc"
        for name, count in zip(realization.set_names, realization.counts)
    )


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    started = perf_counter()

    universe = ExtremeGlobalSearchUniverseService(database).build()
    route_projection = ExtremeMaxHealthClassRouteProjectionService(database).build(
        tuple(universe.class_routes)
    )
    route_rows = tuple(zip(route_projection.routes, route_projection.signatures))
    selected_route = next(
        (
            (route, tuple(signature))
            for route, signature in route_rows
            if tuple(signature) == WINNING_ROUTE_SIGNATURE
        ),
        None,
    )
    if selected_route is None or not route_projection.projection_complete:
        raise RuntimeError("Winning Max Health route signature is not proof-reduced and available")
    route, route_signature = selected_route

    race_projection = ExtremeResourceRaceProjectionService(database).build(
        OBJECTIVE, tuple(universe.races)
    )
    attribute_projection = ExtremeResourceAttributeProjectionService.build(
        OBJECTIVE, tuple(universe.attribute_allocations)
    )
    if not race_projection.projection_complete or not race_projection.races:
        raise RuntimeError("Max Health race projection is incomplete")
    if not attribute_projection.projection_complete or not attribute_projection.allocations:
        raise RuntimeError("Max Health attribute projection is incomplete")
    race = race_projection.races[0]
    attributes = attribute_projection.allocations[0]

    repository = GearSetRepository(database)
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(
        OBJECTIVE, breakpoints
    )
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    ordinary_service = ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    candidate_search = ExtremeMaxHealthNamedGearCandidateSearchService(
        ordinary_service=ordinary_service,
        eligibility=eligibility,
    ).search(topology)
    if not candidate_search.candidate_reduction_proven:
        raise RuntimeError(
            "Max Health named-gear candidate reduction is incomplete: "
            + "; ".join(candidate_search.unresolved)
        )

    special_by_identity = {}
    winning_subsets = 0
    for subset in candidate_search.special_subsets:
        if not subset.winner_found:
            continue
        winning_subsets += 1
        for realization in subset.realizations:
            special_by_identity.setdefault(_realization_identity(realization), realization)
    special_rows = tuple(special_by_identity[key] for key in sorted(special_by_identity))
    if not special_rows:
        raise RuntimeError("No legal Max Health special/runtime named-gear challengers were produced")

    trait_glyph_service = ExtremeArmorResourceTraitGlyphStateService(database)
    armor_catalog = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        OBJECTIVE,
        trait_glyph_service=trait_glyph_service,
    ).build(OBJECTIVE)
    armor_frontier = ExtremeMaxHealthArmorScoringFrontierService.build(armor_catalog)
    if not armor_frontier.reduction_proven:
        raise RuntimeError(
            "Max Health armor frontier is incomplete: "
            + "; ".join(armor_frontier.unresolved)
        )
    armor_rows = tuple(
        sorted(
            (
                row
                for row in armor_frontier.states
                if (
                    int(row.armor_type_count),
                    int(row.weight_state.heavy_pieces),
                )
                == DISCOVERY_WEIGHT_SIGNATURE
            ),
            key=_armor_identity,
        )
    )
    expected_trait_states = len(armor_catalog.trait_glyph_catalog.states)
    if len(armor_rows) != expected_trait_states or expected_trait_states <= 0:
        raise RuntimeError(
            "Max Health special discovery did not preserve one representative +16% "
            "weight witness for every trait/glyph state"
        )

    jewelry_catalog = ExtremeJewelryResourceStaticTraitStateService(database).build(OBJECTIVE)
    jewelry_state = jewelry_catalog.states[0] if jewelry_catalog.states else None
    if not jewelry_catalog.denominator_proven or jewelry_state is None:
        raise RuntimeError("Max Health jewelry denominator is incomplete")

    optimizer = ExtremeOptimizationService(database_path=database)
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=optimizer,
        progression_service=ExtremeHypotheticalUndauntedProgressionService(database),
    )
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
        jewelry_state=jewelry_state,
    )

    candidate = ExtremeStructuralCandidate(
        race=race,
        class_route=route,
        attributes=attributes,
        active_bar="front",
    )

    scored: list[tuple[float, tuple[object, ...], object, object, dict, tuple[str, ...]]] = []
    score_calls = 0
    unresolved_calls = 0
    for realization in special_rows:
        for armor_state in armor_rows:
            scorer = factory(realization, armor_state)
            value, payload, unresolved = scorer(OBJECTIVE, candidate)
            score_calls += 1
            unresolved_tuple = tuple(
                dict.fromkeys(str(item) for item in unresolved if str(item))
            )
            if unresolved_tuple:
                unresolved_calls += 1
            identity = (_realization_identity(realization), _armor_identity(armor_state))
            scored.append(
                (
                    float(value),
                    identity,
                    realization,
                    armor_state,
                    dict(payload),
                    unresolved_tuple,
                )
            )

    scored.sort(key=lambda row: (-row[0], row[1]))
    best = scored[0]
    best_value, _identity, best_gear, best_armor, best_payload, best_unresolved = best

    print("EXTREME MAX HEALTH SPECIAL/RUNTIME CHALLENGERS")
    print(f"database={database}")
    print("mode=proof_reduced_special_subsets+winning_route+representative_16pct_armor+canonical_finite_axes")
    print(f"ordinary_incumbent={float(args.incumbent):.3f}")
    print(f"source_class_routes={route_projection.source_route_count}")
    print(f"route_signatures_proven={len(route_projection.routes)}")
    print(f"route_signature_scored={route_signature!r}")
    print(f"special_branches={len(candidate_search.classified_special.branches)}")
    print(f"special_subset_rows={len(candidate_search.special_subsets)}")
    print(f"winning_special_subsets={winning_subsets}")
    print(f"unique_special_realizations={len(special_rows)}")
    print(f"armor_source_weight_signatures={armor_frontier.source_weight_signature_count}")
    print(f"armor_discovery_weight_signature={DISCOVERY_WEIGHT_SIGNATURE!r}")
    print(f"armor_trait_glyph_states_scored={len(armor_rows)}")
    print(f"canonical_score_calls={score_calls}")
    print(f"canonical_calls_with_unresolved={unresolved_calls}")
    print(f"elapsed_seconds={perf_counter() - started:.3f}")
    print()

    print("TOP SPECIAL/RUNTIME CHALLENGERS")
    for row in scored[: max(1, int(args.top))]:
        value, _key, realization, armor_state, payload, unresolved = row
        print(
            f"  value={value:.3f} margin_vs_incumbent={value - float(args.incumbent):+.3f} "
            f"divines={armor_state.divines_count} infused={armor_state.infused_count} "
            f"unresolved={len(unresolved)}"
        )
        print(f"    sets={_sets_label(realization)}")
        print(
            f"    mundus={payload.get('mundus')!r} second_mundus={payload.get('second_mundus')!r} "
            f"food={payload.get('food')!r} potion={payload.get('potion')!r}"
        )
        active_conditions = payload.get("resource_runtime_active_conditions")
        if active_conditions:
            print(f"    runtime_conditions={active_conditions!r}")

    print()
    print("BEST SPECIAL/RUNTIME CHALLENGER")
    print(f"value={best_value:.3f}")
    print(f"margin_vs_incumbent={best_value - float(args.incumbent):+.3f}")
    print(f"sets={_sets_label(best_gear)}")
    print(
        f"armor_types={best_armor.armor_type_count} "
        f"heavy={best_armor.weight_state.heavy_pieces} "
        f"divines={best_armor.divines_count} infused={best_armor.infused_count}"
    )
    print(f"mundus={best_payload.get('mundus')!r}")
    print(f"second_mundus={best_payload.get('second_mundus')!r}")
    print(f"food={best_payload.get('food')!r}")
    print(f"potion={best_payload.get('potion')!r}")
    print(f"active_buffs={best_payload.get('active_buffs', ())!r}")
    print(f"raw_unresolved={len(best_unresolved)}")
    for item in best_unresolved[:20]:
        print(f"  unresolved: {item}")
    if len(best_unresolved) > 20:
        print(f"  ... {len(best_unresolved) - 20} more")
    if best_value > float(args.incumbent) + 1e-9:
        print("NEXT_STEP=promote this challenger to the Max Health incumbent, then proof-close route/armor equivalence and warning neutralization")
    else:
        print("NEXT_STEP=ordinary 147307 remains the discovery incumbent; proof-close special denominator plus route/armor equivalence and warning neutralization")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
