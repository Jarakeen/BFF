from __future__ import annotations

"""Canonical-score targeted Max Stamina special/runtime named-gear challengers.

This is challenger discovery, not final whole-record closure. The ordinary branch
has established a 101,930 Max Stamina incumbent and the shared class-route proof has
reduced 3,220 legal routes to one dominant reviewed signature. Resource armor weight
states are already proof-reduced by distinct armor-type count, so discovery scores
one deterministic three-type witness across all eight Divines/Infused + Stamina-glyph
states.

Special conditions are executed by the canonical resource evaluator; this audit does
not reimplement Death Dealer's Fete, Shapeshifter's Chain, Prowler's Talisman,
Twice-Born Star, or Bone Pirate's Tatters arithmetic.
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
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_hypothetical_undaunted_progression_service import (
    ExtremeHypotheticalUndauntedProgressionService,
)
from services.extreme_jewelry_resource_static_trait_state_service import (
    ExtremeJewelryResourceStaticTraitStateService,
)
from services.extreme_max_resource_named_gear_candidate_search_service import (
    ExtremeMaxResourceNamedGearCandidateSearchService,
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
from services.extreme_resource_class_route_dominance_projection_service import (
    ExtremeResourceClassRouteDominanceProjectionService,
)
from services.extreme_resource_race_projection_service import ExtremeResourceRaceProjectionService
from services.extreme_structural_core_stat_record_service import (
    ExtremeCanonicalStructuralStatEvaluator,
)
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate


OBJECTIVE = "max_stamina"
INCUMBENT = 101930.0
DISCOVERY_ARMOR_TYPE_COUNT = 3


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
        f"{name} {count}pc" for name, count in zip(realization.set_names, realization.counts)
    )


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    started = perf_counter()

    universe = ExtremeGlobalSearchUniverseService(database).build()
    route_projection = ExtremeResourceClassRouteDominanceProjectionService(database).build(
        OBJECTIVE, tuple(universe.class_routes)
    )
    race_projection = ExtremeResourceRaceProjectionService(database).build(
        OBJECTIVE, tuple(universe.races)
    )
    attribute_projection = ExtremeResourceAttributeProjectionService.build(
        OBJECTIVE, tuple(universe.attribute_allocations)
    )
    if not route_projection.projection_complete or not route_projection.routes:
        raise RuntimeError(
            "Max Stamina class-route projection is incomplete: "
            + "; ".join(route_projection.unresolved)
        )
    if not race_projection.projection_complete or not race_projection.races:
        raise RuntimeError("Max Stamina race projection is incomplete")
    if not attribute_projection.projection_complete or not attribute_projection.allocations:
        raise RuntimeError("Max Stamina attribute projection is incomplete")

    route = route_projection.routes[0]
    route_signature = tuple(route_projection.signature)
    race = race_projection.races[0]
    attributes = attribute_projection.allocations[0]

    repository = GearSetRepository(database)
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    ordinary_service = ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    candidate_search = ExtremeMaxResourceNamedGearCandidateSearchService(
        ordinary_service=ordinary_service,
        eligibility=eligibility,
    ).search(topology)
    if not candidate_search.candidate_reduction_proven:
        raise RuntimeError(
            "Max Stamina named-gear candidate reduction is incomplete: "
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
        raise RuntimeError("No legal Max Stamina special/runtime named-gear challengers were produced")

    armor_catalog = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        OBJECTIVE,
        trait_glyph_service=ExtremeArmorResourceTraitGlyphStateService(database),
    ).build(OBJECTIVE)
    if not armor_catalog.denominator_proven:
        raise RuntimeError(
            "Max Stamina armor denominator is incomplete: " + "; ".join(armor_catalog.unresolved)
        )
    armor_rows = tuple(
        sorted(
            (row for row in armor_catalog.states if row.armor_type_count == DISCOVERY_ARMOR_TYPE_COUNT),
            key=_armor_identity,
        )
    )
    expected_trait_states = len(armor_catalog.trait_glyph_catalog.states)
    if len(armor_rows) != expected_trait_states or expected_trait_states <= 0:
        raise RuntimeError(
            "Max Stamina special discovery did not retain exactly one three-type armor "
            "witness for every trait/glyph state"
        )

    jewelry_catalog = ExtremeJewelryResourceStaticTraitStateService(database).build(OBJECTIVE)
    jewelry_state = jewelry_catalog.states[0] if jewelry_catalog.states else None
    if not jewelry_catalog.denominator_proven or jewelry_state is None:
        raise RuntimeError("Max Stamina jewelry denominator is incomplete")

    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=ExtremeOptimizationService(database_path=database),
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

    # Front-bar discovery is sufficient here. The ordinary incumbent is front/back
    # tied and final whole-record closure retains cross-bar equivalence as an explicit
    # proof obligation rather than multiplying every discovery challenger by two.
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
            unresolved_tuple = tuple(dict.fromkeys(str(item) for item in unresolved if str(item)))
            if unresolved_tuple:
                unresolved_calls += 1
            scored.append(
                (
                    float(value),
                    (_realization_identity(realization), _armor_identity(armor_state)),
                    realization,
                    armor_state,
                    dict(payload),
                    unresolved_tuple,
                )
            )

    scored.sort(key=lambda row: (-row[0], row[1]))
    best_value, _identity, best_gear, best_armor, best_payload, best_unresolved = scored[0]

    print("EXTREME MAX STAMINA SPECIAL/RUNTIME CHALLENGERS")
    print(f"database={database}")
    print("mode=proof_reduced_special_subsets+dominant_route+representative_three_type_armor+canonical_finite_axes")
    print(f"ordinary_incumbent={float(args.incumbent):.3f}")
    print(f"source_class_routes={route_projection.source_route_count}")
    print(f"projected_route_signatures={route_projection.projected_route_count}")
    print(f"route_signature_scored={route_signature!r}")
    print(f"special_branches={len(candidate_search.classified_special.branches)}")
    print(f"special_subset_rows={len(candidate_search.special_subsets)}")
    print(f"winning_special_subsets={winning_subsets}")
    print(f"unique_special_realizations={len(special_rows)}")
    print(f"armor_source_states={len(armor_catalog.states)}")
    print(f"armor_discovery_type_count={DISCOVERY_ARMOR_TYPE_COUNT}")
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
        print("NEXT_STEP=promote this challenger to the Max Stamina incumbent, then proof-close bars, armor equivalence, warning neutralization, and the special denominator")
    else:
        print("NEXT_STEP=ordinary 101930 remains the discovery incumbent; proof-close bars, armor equivalence, warning neutralization, and the special denominator")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
