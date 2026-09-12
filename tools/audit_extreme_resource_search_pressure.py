from __future__ import annotations

"""Report proof-reduced search pressure for Extreme max-resource ceilings.

This audit deliberately does not score builds. It constructs the same finite source
catalogs and proof reducers used by the production Extreme record path so we can see
which remaining axis is actually expensive before adding another optimization.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphStateService,
)
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphStateService,
)
from services.extreme_dual_bar_gear_state_catalog_service import (
    ExtremeDualBarGearStateCatalogService,
)
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_resource_attribute_projection_service import (
    ExtremeResourceAttributeProjectionService,
)
from services.extreme_resource_potion_projection_service import (
    ExtremeResourcePotionProjectionService,
)
from services.extreme_resource_provisioning_projection_service import (
    ExtremeResourceProvisioningProjectionService,
)
from services.extreme_structural_named_gear_mundus_food_potion_core_stat_record_service import (
    ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
)

_OBJECTIVES = ("max_magicka", "max_stamina")


def _flatten_realizations(result) -> tuple:
    unique = {}
    realization_result = getattr(result, "realization", None)
    for topology in tuple(getattr(realization_result, "topologies", ()) or ()):
        for realization in tuple(getattr(topology, "realizations", ()) or ()):
            identity = (
                tuple(getattr(realization, "set_ids", ()) or ()),
                tuple(getattr(realization, "counts", ()) or ()),
                str(getattr(getattr(realization, "weapon_shape", None), "value", "")),
                tuple(
                    (
                        str(getattr(row, "slot", "")),
                        int(getattr(row, "set_id", 0) or 0),
                        str(getattr(row, "weapon_type", "")),
                    )
                    for row in tuple(getattr(realization, "assignments", ()) or ())
                ),
            )
            unique.setdefault(identity, realization)
    return tuple(unique[key] for key in sorted(unique))


def _print_objective(database: Path, objective: str) -> None:
    print()
    print(objective.upper())

    universe = ExtremeGlobalSearchUniverseService(database).build()
    projection = ExtremeResourceAttributeProjectionService.build(
        objective,
        tuple(universe.attribute_allocations),
    )

    record_service = ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService(
        database_path=database,
    )
    gear = record_service._gear_realization(objective)
    raw_realizations = _flatten_realizations(gear)
    dual_bar = ExtremeDualBarGearStateCatalogService.build(
        raw_realizations,
        source_denominator_proven=bool(getattr(gear, "denominator_proven", False)),
        unresolved=tuple(getattr(gear, "unresolved", ()) or ()),
    )

    trait_glyph_service = ExtremeArmorResourceTraitGlyphStateService(database)
    armor = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        objective,
        trait_glyph_service=trait_glyph_service,
    ).build(objective)

    mundus = MundusRepository(
        database,
        game_update=U50_GAME_UPDATE,
        initialize=False,
    )
    mundus_count = len(tuple(mundus.list_names())) + 1

    provisioning_repository = ProvisioningStaticRepository(database)
    provisioning = ExtremeResourceProvisioningProjectionService(
        provisioning_repository
    ).build(objective)
    raw_provisioning = len(tuple(provisioning_repository.list_names())) + 1
    retained_provisioning = len(tuple(provisioning.choices))

    potion_repository = PotionAvailabilityRepository(database)
    potion_catalog = potion_repository.catalog()
    potion = ExtremeResourcePotionProjectionService(potion_repository).build(objective)
    raw_potions = len(tuple(potion_catalog.formulas)) + 1
    retained_potions = 1 if potion.objective_irrelevance_proven else raw_potions

    structural_raw = (
        len(universe.races)
        * len(universe.class_routes)
        * len(universe.attribute_allocations)
        * len(universe.active_bars)
    )
    structural_reduced = (
        len(universe.races)
        * len(universe.class_routes)
        * len(projection.allocations)
        * len(universe.active_bars)
    )

    front = tuple(dual_bar.front_admissible_realizations)
    back = tuple(dual_bar.back_admissible_realizations)
    active_gear = max(len(front), len(back))

    finite_axis_pressure = (
        max(active_gear, 1)
        * max(len(armor.states), 1)
        * max(mundus_count, 1)
        * max(retained_provisioning, 1)
        * max(retained_potions, 1)
    )
    reduced_score_pressure = structural_reduced * finite_axis_pressure

    print(f"races={len(universe.races):,}")
    print(f"class_routes={len(universe.class_routes):,}")
    print(
        f"attributes={len(universe.attribute_allocations):,}->{len(projection.allocations):,} "
        f"projection_complete={projection.projection_complete}"
    )
    print(f"active_bars={len(universe.active_bars):,}")
    print(f"structural_pressure={structural_raw:,}->{structural_reduced:,}")
    print(f"named_gear_unique_realizations={len(raw_realizations):,}")
    print(f"dual_bar_states={len(dual_bar.states):,}")
    print(f"front_admissible_gear={len(front):,}")
    print(f"back_admissible_gear={len(back):,}")
    print(f"resource_armor_states={len(armor.states):,}")
    print(f"mundus_states_including_none={mundus_count:,}")
    print(
        f"provisioning_states={raw_provisioning:,}->{retained_provisioning:,} "
        f"projection_complete={provisioning.projection_complete}"
    )
    print(f"  food_witness={provisioning.food_witness or '<none>'}")
    print(f"  drink_witness={provisioning.drink_witness or '<none>'}")
    print(
        f"potion_states={raw_potions:,}->{retained_potions:,} "
        f"objective_irrelevance_proven={potion.objective_irrelevance_proven}"
    )
    print(f"finite_axis_pressure_per_structural_candidate={finite_axis_pressure:,}")
    print(f"estimated_reduced_score_pressure={reduced_score_pressure:,}")

    unresolved = tuple(
        dict.fromkeys(
            str(item)
            for item in (
                *tuple(getattr(gear, "unresolved", ()) or ()),
                *tuple(dual_bar.unresolved),
                *tuple(armor.unresolved),
                *tuple(provisioning.unresolved),
                *tuple(potion.unresolved),
            )
            if str(item)
        )
    )
    print(f"unresolved_count={len(unresolved):,}")
    for item in unresolved[:10]:
        print(f"  unresolved: {item}")
    if len(unresolved) > 10:
        print(f"  ... {len(unresolved) - 10:,} more")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report proof-reduced Extreme max-resource search pressure without scoring builds."
    )
    parser.add_argument(
        "--database",
        default=str(ROOT / "data" / "eso.db"),
        help="Path to the canonical ESO SQLite database.",
    )
    parser.add_argument(
        "--objective",
        choices=_OBJECTIVES,
        action="append",
        help="Optional objective to report; repeat for both. Defaults to both.",
    )
    args = parser.parse_args()

    database = Path(args.database)
    objectives = tuple(args.objective or _OBJECTIVES)

    print("EXTREME RESOURCE SEARCH PRESSURE")
    print(f"Database: {database}")
    print("This audit constructs proven source/reduction catalogs only; it does not score builds.")
    for objective in objectives:
        _print_objective(database, objective)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
