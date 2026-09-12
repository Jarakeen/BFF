from __future__ import annotations

"""Coarsely time Max Resource stages without cProfile overhead.

This diagnostic isolates named-gear realization from downstream canonical scoring and
samples individual named-gear + armor finite-axis scorers. It deliberately does not
call the outer scorer for a full structural candidate because that would rescan every
surviving gear/armor pair and merely reproduce the expensive production stage we are
trying to measure. It does not alter search behavior or database state.
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
from services.extreme_armor_resource_trait_glyph_state_service import ExtremeArmorResourceTraitGlyphStateService
from services.extreme_armor_resource_weight_trait_glyph_state_service import ExtremeArmorResourceWeightTraitGlyphStateService
from services.extreme_best_named_gear_resource_armor_mundus_food_potion_structural_stat_evaluator import (
    ExtremeBestNamedGearResourceArmorMundusFoodPotionStructuralStatEvaluator,
    ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory,
)
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_hypothetical_undaunted_progression_service import ExtremeHypotheticalUndauntedProgressionService
from services.extreme_jewelry_resource_static_trait_state_service import ExtremeJewelryResourceStaticTraitStateService
from services.extreme_resource_class_route_projection_service import ExtremeResourceClassRouteProjectionService
from services.extreme_structural_core_stat_record_service import ExtremeCanonicalStructuralStatEvaluator
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate
from services.extreme_structural_named_gear_mundus_food_potion_core_stat_record_service import (
    ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
)


OBJECTIVES = ("max_magicka", "max_stamina", "max_health")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument("--objective", choices=OBJECTIVES, default="max_magicka")
    parser.add_argument("--sample", type=int, default=4)
    return parser


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    key = args.objective

    record_service = ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService(database_path=database)

    started = perf_counter()
    gear_realization = record_service._gear_realization(key)
    gear_seconds = perf_counter() - started

    optimizer = record_service.optimizer
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=optimizer,
        progression_service=ExtremeHypotheticalUndauntedProgressionService(database),
    )
    mundus_repository = MundusRepository(database, game_update=U50_GAME_UPDATE, initialize=False)
    provisioning_repository = ProvisioningStaticRepository(database)
    potion_repository = PotionAvailabilityRepository(database, game_update=GameUpdate.U50)

    trait_glyph_service = ExtremeArmorResourceTraitGlyphStateService(database)
    armor_catalog = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        key, trait_glyph_service=trait_glyph_service
    ).build(key)
    jewelry_catalog = ExtremeJewelryResourceStaticTraitStateService(database).build(key)
    jewelry_state = jewelry_catalog.states[0] if jewelry_catalog.states else None

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

    started = perf_counter()
    gear_rows_front = evaluator.gear_realizations(active_bar="front")
    gear_rows_back = evaluator.gear_realizations(active_bar="back")
    armor_rows = evaluator.armor_states()
    catalog_seconds = perf_counter() - started

    universe = ExtremeGlobalSearchUniverseService(database).build()
    route_projection = ExtremeResourceClassRouteProjectionService(database).build(
        key, tuple(universe.class_routes)
    )
    routes = tuple(route_projection.routes) if route_projection.projection_complete else tuple(universe.class_routes)
    attribute_projection = evaluator.structural_attribute_projection(key, tuple(universe.attribute_allocations))
    attributes = tuple(attribute_projection.allocations) if attribute_projection.projection_complete else tuple(universe.attribute_allocations)

    structural_candidates = tuple(
        ExtremeStructuralCandidate(race=race, class_route=route, attributes=attribute, active_bar=active_bar)
        for race in universe.races
        for route in routes
        for attribute in attributes
        for active_bar in universe.active_bars
    )

    print("EXTREME RESOURCE SCORING STAGES")
    print(f"objective={key}")
    print(f"gear_realization_seconds={gear_seconds:.3f}")
    print(f"gear_candidates_front={len(gear_rows_front)}")
    print(f"gear_candidates_back={len(gear_rows_back)}")
    print(f"armor_states={len(armor_rows)}")
    print(f"gear_armor_pairs_front={len(gear_rows_front) * len(armor_rows)}")
    print(f"gear_armor_pairs_back={len(gear_rows_back) * len(armor_rows)}")
    print(f"catalog_materialization_seconds={catalog_seconds:.3f}")
    print(f"races={len(universe.races)}")
    print(f"routes={len(routes)}")
    print(f"attributes={len(attributes)}")
    print(f"active_bars={len(universe.active_bars)}")
    print(f"structural_candidates={len(structural_candidates)}")

    if not structural_candidates or not gear_rows_front or not armor_rows:
        print("atomic_samples=none")
        return 0

    sample_count = max(0, int(args.sample))
    sample_candidate = structural_candidates[0]
    sample_gear = gear_rows_front
    pair_count = len(sample_gear) * len(armor_rows)
    sample_pairs = []
    for gear_index, realization in enumerate(sample_gear):
        for armor_index, armor_state in enumerate(armor_rows):
            sample_pairs.append((gear_index, armor_index, realization, armor_state))
            if len(sample_pairs) >= sample_count:
                break
        if len(sample_pairs) >= sample_count:
            break

    print("atomic_pair_scores=")
    total = 0.0
    for index, (gear_index, armor_index, realization, armor_state) in enumerate(sample_pairs, start=1):
        scorer = factory(realization, armor_state)
        started = perf_counter()
        value, _payload, unresolved = scorer(key, sample_candidate)
        elapsed = perf_counter() - started
        total += elapsed
        print(
            f"  {index}: seconds={elapsed:.6f} value={float(value):.3f} "
            f"gear_index={gear_index} armor_index={armor_index} unresolved={len(unresolved)}"
        )

    if sample_pairs:
        average = total / len(sample_pairs)
        print(f"atomic_pair_average_seconds={average:.6f}")
        print(f"projected_one_structural_candidate_seconds={average * pair_count:.3f}")
        print(
            f"naive_projected_all_structural_scoring_seconds="
            f"{average * pair_count * len(structural_candidates):.3f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
