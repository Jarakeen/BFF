from __future__ import annotations

"""Measure semantic and production structural frontiers for Extreme max resources.

The diagnostic intentionally reports two different layers:

* semantic equivalence classes, which answer how many distinct canonical target-
  resource race signatures exist; and
* the production dominance frontier, which uses the proof-owned race projection to
  retain only the strongest legal racial witness for a scalar maximum objective.

Class routes still use the proof-owned route projection, attributes use the proven
single maximum allocation, and active-bar identity remains explicit. No production
scoring rule is reimplemented here.
"""

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.character_progression import CharacterProgression
from minmax.racial_passive_stat_repository import RacialPassiveStatRepository
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_hypothetical_racial_progression_service import (
    ExtremeHypotheticalRacialProgressionService,
)
from services.extreme_resource_attribute_projection_service import (
    ExtremeResourceAttributeProjectionService,
)
from services.extreme_resource_class_route_projection_service import (
    ExtremeResourceClassRouteProjectionService,
)
from services.extreme_resource_race_projection_service import (
    ExtremeResourceRaceProjectionService,
)


OBJECTIVES = ("max_magicka", "max_stamina", "max_health")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument("--objective", choices=OBJECTIVES, default="max_magicka")
    return parser


def _race_signature(
    race: str,
    objective_key: str,
    *,
    progression_service: ExtremeHypotheticalRacialProgressionService,
    repository: RacialPassiveStatRepository,
) -> tuple[object, ...]:
    try:
        progression = progression_service.normalize(CharacterProgression(), race)
        canonical_race = progression_service._canonical_skill_line_race(race)
        resolution = repository.resolve(canonical_race, progression)
    except Exception as exc:  # diagnostic must fail closed, never merge on error
        return ("identity_required", race, f"exception:{type(exc).__name__}:{exc}")

    if resolution.unresolved:
        return (
            "identity_required",
            race,
            "unresolved",
            tuple(resolution.unresolved),
        )

    try:
        value = float(resolution.stats.get(objective_key, 0.0) or 0.0)
    except (TypeError, ValueError):
        return ("identity_required", race, "invalid_target_value")

    return ("canonical_target_resource", value)


def route_projection_service_line(value: object) -> str:
    from services.extreme_heal_class_route_service import canonical_class_skill_line_id

    return canonical_class_skill_line_id(value)


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    key = str(args.objective).strip().casefold()

    universe = ExtremeGlobalSearchUniverseService(database).build()

    routes = tuple(universe.class_routes)
    route_projection = None
    if key in ExtremeResourceClassRouteProjectionService.SUPPORTED_OBJECTIVES:
        route_projection = ExtremeResourceClassRouteProjectionService(database).build(key, routes)
        if route_projection.projection_complete:
            routes = tuple(route_projection.routes)

    attribute_projection = ExtremeResourceAttributeProjectionService.build(
        key, tuple(universe.attribute_allocations)
    )
    attributes = (
        tuple(attribute_projection.allocations)
        if attribute_projection.projection_complete
        else tuple(universe.attribute_allocations)
    )

    progression_service = ExtremeHypotheticalRacialProgressionService(database)
    racial_repository = RacialPassiveStatRepository(database)
    race_signatures = {
        race: _race_signature(
            race,
            key,
            progression_service=progression_service,
            repository=racial_repository,
        )
        for race in universe.races
    }

    race_projection = ExtremeResourceRaceProjectionService(
        database,
        progression_service=progression_service,
        racial_repository=racial_repository,
    ).build(key, tuple(universe.races))
    production_races = (
        tuple(race_projection.races)
        if race_projection.projection_complete
        else tuple(universe.races)
    )

    semantic_candidates = [
        (race, route, attributes_row, active_bar)
        for race in universe.races
        for route in routes
        for attributes_row in attributes
        for active_bar in universe.active_bars
    ]
    production_candidates = [
        (race, route, attributes_row, active_bar)
        for race in production_races
        for route in routes
        for attributes_row in attributes
        for active_bar in universe.active_bars
    ]

    def route_signature(route) -> tuple[object, ...]:
        if route_projection is not None and route_projection.projection_complete:
            relevant = tuple(route_projection.relevant_class_lines)
            selected = {
                route_projection_service_line(line)
                for line in route.equipped_skill_lines
            }
            return tuple(line for line in relevant if line in selected)
        return (
            str(route.base_class.value),
            bool(route.is_subclassed),
            tuple(route.equipped_skill_lines),
        )

    semantic_signatures = Counter(
        (
            race_signatures[race],
            route_signature(route),
            int(attributes_row.health),
            int(attributes_row.magicka),
            int(attributes_row.stamina),
            str(active_bar),
        )
        for race, route, attributes_row, active_bar in semantic_candidates
    )

    race_classes = Counter(race_signatures.values())
    unresolved_races = tuple(
        race
        for race, signature in race_signatures.items()
        if signature and signature[0] == "identity_required"
    )

    print("EXTREME RESOURCE STRUCTURAL SCORING FRONTIER")
    print(f"objective={key}")
    print(f"races_raw={len(universe.races)}")
    print(f"race_semantic_classes={len(race_classes)}")
    print(f"race_largest_equivalence_class={max(race_classes.values(), default=0)}")
    print(f"race_unresolved={len(unresolved_races)}")
    if unresolved_races:
        print("race_unresolved_names=" + ",".join(unresolved_races))
    print(f"race_dominance_projection_complete={race_projection.projection_complete}")
    print(f"race_production_witnesses={len(production_races)}")
    if race_projection.projection_complete:
        print(f"race_production_witness={race_projection.races[0]}")
        print(f"race_production_target_resource={race_projection.signatures[0]:g}")

    print(f"routes_raw={len(universe.class_routes)}")
    print(f"routes_projected={len(routes)}")
    print(
        "route_projection_complete="
        f"{bool(route_projection is not None and route_projection.projection_complete)}"
    )
    print(f"attributes_raw={len(universe.attribute_allocations)}")
    print(f"attributes_projected={len(attributes)}")
    print(f"active_bars={len(universe.active_bars)}")

    print(f"structural_candidates_semantic_input={len(semantic_candidates)}")
    print(f"structural_semantic_classes={len(semantic_signatures)}")
    semantic_duplicates = len(semantic_candidates) - len(semantic_signatures)
    print(f"structural_semantic_duplicate_candidates={semantic_duplicates}")
    semantic_reduction = (
        100.0 * semantic_duplicates / len(semantic_candidates)
        if semantic_candidates
        else 0.0
    )
    print(f"structural_semantic_equivalence_reduction_percent={semantic_reduction:.3f}")
    print(
        "structural_semantic_largest_equivalence_class="
        f"{max(semantic_signatures.values(), default=0)}"
    )

    raw_structural = (
        len(universe.races)
        * len(routes)
        * len(attributes)
        * len(universe.active_bars)
    )
    print(f"structural_candidates_before_race_dominance={raw_structural}")
    print(f"structural_candidates_production={len(production_candidates)}")
    production_pruned = raw_structural - len(production_candidates)
    print(f"structural_candidates_pruned_by_race_dominance={production_pruned}")
    production_reduction = (
        100.0 * production_pruned / raw_structural if raw_structural else 0.0
    )
    print(f"structural_race_dominance_reduction_percent={production_reduction:.3f}")

    print("race_signatures=")
    for race in universe.races:
        print(f"  {race}: {race_signatures[race]!r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
