from __future__ import annotations

"""Measure proof-safe structural scoring equivalence for Extreme max resources.

This diagnostic does not alter production scoring. It keeps the already-proven
class-route projection, the proof-reduced attribute witness, and active-bar identity,
then asks the canonical racial progression + racial passive repository for the exact
requested-resource contribution of each legal race. Races collapse only when that
canonical target-resource contribution is equal and both resolutions are complete.
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

    # Only the requested max-resource contribution is permitted to erase race
    # identity here. Other racial stats are outside this scalar objective and are
    # already classified by the canonical passive-coverage path.
    return ("canonical_target_resource", value)


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

    raw_candidates = [
        (race, route, attributes_row, active_bar)
        for race in universe.races
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

    signatures = Counter(
        (
            race_signatures[race],
            route_signature(route),
            int(attributes_row.health),
            int(attributes_row.magicka),
            int(attributes_row.stamina),
            str(active_bar),
        )
        for race, route, attributes_row, active_bar in raw_candidates
    )

    race_classes = Counter(race_signatures.values())
    unresolved_races = tuple(
        race for race, signature in race_signatures.items()
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
    print(f"routes_raw={len(universe.class_routes)}")
    print(f"routes_projected={len(routes)}")
    print(
        "route_projection_complete="
        f"{bool(route_projection is not None and route_projection.projection_complete)}"
    )
    print(f"attributes_raw={len(universe.attribute_allocations)}")
    print(f"attributes_projected={len(attributes)}")
    print(f"active_bars={len(universe.active_bars)}")
    print(f"structural_candidates_current={len(raw_candidates)}")
    print(f"structural_semantic_classes={len(signatures)}")
    duplicates = len(raw_candidates) - len(signatures)
    print(f"structural_duplicate_candidates={duplicates}")
    reduction = 100.0 * duplicates / len(raw_candidates) if raw_candidates else 0.0
    print(f"structural_equivalence_reduction_percent={reduction:.3f}")
    print(f"structural_largest_equivalence_class={max(signatures.values(), default=0)}")

    print("race_signatures=")
    for race in universe.races:
        print(f"  {race}: {race_signatures[race]!r}")

    return 0


def route_projection_service_line(value: object) -> str:
    # Keep this import local so the diagnostic shares the same canonical line
    # normalizer as the route projection service without creating another rule.
    from services.extreme_heal_class_route_service import canonical_class_skill_line_id

    return canonical_class_skill_line_id(value)


if __name__ == "__main__":
    raise SystemExit(main())
