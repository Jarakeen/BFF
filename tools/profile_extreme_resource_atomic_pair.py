from __future__ import annotations

"""Profile one warmed Extreme max-resource gear+armor atomic score.

This intentionally profiles only a single post-warmup finite-axis score so cProfile
reports canonical scoring cost without the massive distortion seen when profiling the
full combinatorial search.
"""

import argparse
import cProfile
import io
from pathlib import Path
import pstats
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.combat_effect_semantics import GameUpdate
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument("--objective", choices=("max_magicka", "max_stamina", "max_health"), default="max_magicka")
    parser.add_argument("--gear-index", type=int, default=407)
    parser.add_argument("--armor-index", type=int, default=1)
    parser.add_argument("--limit", type=int, default=40)
    return parser


def _render(profile: cProfile.Profile, *, limit: int) -> str:
    output = io.StringIO()
    stats = pstats.Stats(profile, stream=output).strip_dirs()
    output.write("\n=== TOP BY CUMULATIVE TIME ===\n")
    stats.sort_stats("cumulative").print_stats(limit)
    output.write("\n=== TOP BY SELF TIME ===\n")
    stats.sort_stats("tottime").print_stats(limit)
    output.write("\n=== SQLITE-RELATED CALLS ===\n")
    stats.sort_stats("cumulative").print_stats("sqlite", limit)
    return output.getvalue()


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    key = args.objective

    record_service = ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService(database_path=database)
    gear_realization = record_service._gear_realization(key)
    optimizer = record_service.optimizer
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=optimizer,
        progression_service=ExtremeHypotheticalUndauntedProgressionService(database),
    )
    factory = ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory(
        canonical_evaluator=canonical,
        mundus_repository=MundusRepository(database, game_update=U50_GAME_UPDATE, initialize=False),
        provisioning_repository=ProvisioningStaticRepository(database),
        potion_repository=PotionAvailabilityRepository(database, game_update=GameUpdate.U50),
        jewelry_state=(lambda catalog: catalog.states[0] if catalog.states else None)(
            ExtremeJewelryResourceStaticTraitStateService(database).build(key)
        ),
    )
    evaluator = ExtremeBestNamedGearResourceArmorMundusFoodPotionStructuralStatEvaluator(
        gear_realization=gear_realization,
        armor_catalog=ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
            key,
            trait_glyph_service=ExtremeArmorResourceTraitGlyphStateService(database),
        ).build(key),
        evaluator_factory=factory,
    )

    gear_rows = evaluator.gear_realizations(active_bar="front")
    armor_rows = evaluator.armor_states()
    if not gear_rows or not armor_rows:
        raise RuntimeError("Extreme atomic pair profile requires gear and armor candidates")

    universe = ExtremeGlobalSearchUniverseService(database).build()
    projection = ExtremeResourceClassRouteProjectionService(database).build(key, tuple(universe.class_routes))
    routes = tuple(projection.routes) if projection.projection_complete else tuple(universe.class_routes)
    attribute_projection = evaluator.structural_attribute_projection(key, tuple(universe.attribute_allocations))
    attributes = tuple(attribute_projection.allocations) if attribute_projection.projection_complete else tuple(universe.attribute_allocations)
    candidate = ExtremeStructuralCandidate(
        race=universe.races[0],
        class_route=routes[0],
        attributes=attributes[0],
        active_bar="front",
    )

    gear_index = max(0, min(int(args.gear_index), len(gear_rows) - 1))
    armor_index = max(0, min(int(args.armor_index), len(armor_rows) - 1))

    # Warm the exact canonical stack using one neighboring pair. This excludes lazy
    # repository/service initialization from the measured pair while retaining the
    # ordinary steady-state code path.
    warm_scorer = factory(gear_rows[0], armor_rows[0])
    warm_scorer(key, candidate)

    scorer = factory(gear_rows[gear_index], armor_rows[armor_index])
    profile = cProfile.Profile()
    started = perf_counter()
    profile.enable()
    value, _payload, unresolved = scorer(key, candidate)
    profile.disable()
    elapsed = perf_counter() - started

    print("EXTREME RESOURCE ATOMIC PAIR PROFILE")
    print(f"objective={key}")
    print(f"gear_index={gear_index}")
    print(f"armor_index={armor_index}")
    print(f"elapsed_seconds={elapsed:.6f}")
    print(f"value={float(value):.3f}")
    print(f"unresolved={len(unresolved)}")
    print(_render(profile, limit=max(1, int(args.limit))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
