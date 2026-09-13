from __future__ import annotations

"""Find a clean Max Health incumbent from the exact ordinary named-gear frontier.

This is incumbent discovery, not the final whole-record proof. It starts from the
production exact ordinary named-gear branch-and-bound, keeps only realizations tied
at the global best unconditional flat Max Health delta, then canonical-scores those
witnesses across the proof-reduced Max Health class-route and armor frontiers.

Mundus, provisioning, potion, jewelry, Champion Points, active-bar witnesses,
Max Health runtime passives, and the six-Home-Keep Emperor snapshot remain owned by
the existing canonical finite-axis evaluator stack.

Special/runtime named gear is intentionally deferred to the next audit. The point of
this stage is to establish a strong clean threshold without reopening exhaustive gear
assignment search.
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--top", type=int, default=10)
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
    race_projection = ExtremeResourceRaceProjectionService(database).build(
        OBJECTIVE, tuple(universe.races)
    )
    attribute_projection = ExtremeResourceAttributeProjectionService.build(
        OBJECTIVE, tuple(universe.attribute_allocations)
    )

    if not route_projection.projection_complete:
        raise RuntimeError(
            "Max Health class-route projection is incomplete: "
            + "; ".join(route_projection.unresolved)
        )
    if not race_projection.projection_complete:
        raise RuntimeError(
            "Max Health race projection is incomplete: "
            + "; ".join(race_projection.unresolved)
        )
    if not attribute_projection.projection_complete:
        raise RuntimeError(
            "Max Health attribute projection is incomplete: "
            + "; ".join(attribute_projection.unresolved)
        )

    gear_repository = GearSetRepository(database)
    topology = ExtremeGearSetTopologyCatalogService(gear_repository).build()
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
    ordinary = ordinary_service.search(topology)
    topology_winners = tuple(row for row in ordinary.topologies if row.winner_found)
    global_ordinary_delta = max(
        (float(row.best_exact_flat_delta) for row in topology_winners),
        default=float("-inf"),
    )
    ordinary_rows = tuple(
        sorted(
            (
                realization
                for row in topology_winners
                if row.best_exact_flat_delta is not None
                and abs(float(row.best_exact_flat_delta) - global_ordinary_delta) <= 1e-9
                for realization in row.realizations
            ),
            key=_realization_identity,
        )
    )
    if not ordinary_rows or global_ordinary_delta == float("-inf"):
        raise RuntimeError("Exact ordinary Max Health search returned no physical winner")

    trait_glyph = ExtremeArmorResourceTraitGlyphStateService(database)
    armor_catalog = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        OBJECTIVE,
        trait_glyph_service=trait_glyph,
    ).build(OBJECTIVE)
    if not armor_catalog.denominator_proven:
        raise RuntimeError(
            "Max Health armor denominator is incomplete: "
            + "; ".join(armor_catalog.unresolved)
        )
    armor_frontier = ExtremeMaxHealthArmorScoringFrontierService.build(armor_catalog)
    armor_rows = tuple(sorted(armor_frontier.states, key=_armor_identity))
    if not armor_frontier.reduction_proven or not armor_rows:
        raise RuntimeError(
            "Max Health armor scoring frontier is incomplete: "
            + "; ".join(armor_frontier.unresolved)
        )

    jewelry_catalog = ExtremeJewelryResourceStaticTraitStateService(database).build(OBJECTIVE)
    jewelry_state = jewelry_catalog.states[0] if jewelry_catalog.states else None
    if not jewelry_catalog.denominator_proven or jewelry_state is None:
        raise RuntimeError(
            "Max Health jewelry denominator is incomplete: "
            + "; ".join(jewelry_catalog.unresolved)
        )

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

    race = race_projection.races[0]
    attributes = attribute_projection.allocations[0]
    routes = tuple(route_projection.routes)

    scored: list[tuple[float, tuple[object, ...], object, object, object, dict, tuple[str, ...]]] = []
    score_calls = 0
    unresolved_calls = 0

    # One active snapshot is sufficient for incumbent discovery. The reviewed
    # active-bar service materializes the objective-specific witness on that bar;
    # front/back equivalence is a separate final-proof obligation.
    active_bar = "front"
    for realization in ordinary_rows:
        for armor_state in armor_rows:
            scorer = factory(realization, armor_state)
            for route, signature in zip(route_projection.routes, route_projection.signatures):
                candidate = ExtremeStructuralCandidate(
                    race=race,
                    class_route=route,
                    attributes=attributes,
                    active_bar=active_bar,
                )
                value, payload, unresolved = scorer(OBJECTIVE, candidate)
                score_calls += 1
                unresolved_tuple = tuple(dict.fromkeys(str(item) for item in unresolved if str(item)))
                if unresolved_tuple:
                    unresolved_calls += 1
                identity = (
                    _realization_identity(realization),
                    _armor_identity(armor_state),
                    tuple(signature),
                )
                scored.append(
                    (
                        float(value),
                        identity,
                        realization,
                        armor_state,
                        signature,
                        dict(payload),
                        unresolved_tuple,
                    )
                )

    scored.sort(key=lambda row: (-row[0], row[1]))
    best = scored[0]
    best_value, _identity, best_gear, best_armor, best_signature, best_payload, best_unresolved = best

    print("EXTREME MAX HEALTH ORDINARY INCUMBENT")
    print(f"database={database}")
    print("mode=exact_best_ordinary_gear+proof_reduced_routes+proof_reduced_health_armor+canonical_finite_axes")
    print(f"structural_denominator_proven={universe.structural_denominator_proven}")
    print(f"source_class_routes={route_projection.source_route_count}")
    print(f"route_signatures_scored={len(routes)}")
    print(f"route_projection_complete={route_projection.projection_complete}")
    print(f"race={race}")
    print(
        "attributes="
        f"health:{attributes.health} magicka:{attributes.magicka} stamina:{attributes.stamina}"
    )
    print(f"ordinary_denominator_proven={ordinary.ordinary_denominator_proven}")
    print(f"ordinary_best_exact_flat_delta={global_ordinary_delta}")
    print(f"ordinary_global_winning_realizations={len(ordinary_rows)}")
    print(f"armor_source_states={len(armor_catalog.states)}")
    print(f"armor_source_weight_signatures={armor_frontier.source_weight_signature_count}")
    print(f"armor_retained_weight_signatures={armor_frontier.retained_weight_signatures!r}")
    print(f"armor_best_reviewed_percent={armor_frontier.best_reviewed_percent:.6f}")
    print(f"armor_states_scored={len(armor_rows)}")
    print(f"armor_frontier_reduction_proven={armor_frontier.reduction_proven}")
    print(f"canonical_score_calls={score_calls}")
    print(f"canonical_calls_with_unresolved={unresolved_calls}")
    print(f"elapsed_seconds={perf_counter() - started:.3f}")
    print()

    print("TOP ORDINARY CANONICAL CANDIDATES")
    for row in scored[: max(1, int(args.top))]:
        value, _key, realization, armor_state, signature, payload, unresolved = row
        print(
            f"  value={value:.3f} route_signature={tuple(signature)!r} "
            f"armor_types={getattr(armor_state, 'armor_type_count', '?')} "
            f"heavy={getattr(armor_state.weight_state, 'heavy_pieces', '?')} "
            f"divines={getattr(armor_state, 'divines_count', '?')} "
            f"infused={getattr(armor_state, 'infused_count', '?')} "
            f"unresolved={len(unresolved)}"
        )
        print(f"    sets={_sets_label(realization)}")
        print(
            f"    mundus={payload.get('mundus')!r} food={payload.get('food')!r} "
            f"potion={payload.get('potion')!r}"
        )
        runtime_label = payload.get("resource_max_health_runtime_label")
        if runtime_label:
            print(f"    max_health_runtime={runtime_label!r}")

    print()
    print("BEST ORDINARY MAX HEALTH INCUMBENT")
    print(f"value={best_value:.3f}")
    print(f"route_signature={tuple(best_signature)!r}")
    print(f"sets={_sets_label(best_gear)}")
    print(
        f"armor_types={getattr(best_armor, 'armor_type_count', '?')} "
        f"heavy={getattr(best_armor.weight_state, 'heavy_pieces', '?')} "
        f"divines={getattr(best_armor, 'divines_count', '?')} "
        f"infused={getattr(best_armor, 'infused_count', '?')}"
    )
    print(f"mundus={best_payload.get('mundus')!r}")
    print(f"food={best_payload.get('food')!r}")
    print(f"potion={best_payload.get('potion')!r}")
    print(f"active_buffs={best_payload.get('active_buffs', ())!r}")
    print(
        "max_health_runtime="
        f"{best_payload.get('resource_max_health_runtime_label', '<none>')!r}"
    )
    print(f"raw_unresolved={len(best_unresolved)}")
    for item in best_unresolved[:20]:
        print(f"  unresolved: {item}")
    if len(best_unresolved) > 20:
        print(f"  ... {len(best_unresolved) - 20} more")
    print(
        "NEXT_STEP=use this ordinary canonical incumbent as the threshold for targeted "
        "Max Health special/runtime named-gear scoring"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
