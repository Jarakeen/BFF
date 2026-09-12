from __future__ import annotations

"""Report proof-reduced search pressure for Extreme max-resource ceilings.

This audit deliberately does not score builds. It constructs the same finite source
catalogs and proof reducers used by the production Extreme record path so we can see
which remaining axis is actually expensive before adding another optimization.
"""

import argparse
from pathlib import Path

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


def _gear_identity(row) -> tuple[object, ...]:
    return (
        tuple(row.set_ids),
        tuple(row.counts),
        row.weapon_shape.value,
        tuple((assignment.slot, assignment.set_id, assignment.weapon_type) for assignment in row.assignments),
    )


def _fmt(value: int) -> str:
    return f"{int(value):,}"


def audit(database: Path, objective: str) -> None:
    universe = ExtremeGlobalSearchUniverseService(database).build()
    projection = ExtremeResourceAttributeProjectionService.build(
        objective,
        tuple(universe.attribute_allocations),
    )

    record_service = ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService(
        database_path=database,
    )
    gear = record_service._gear_realization(objective)
    raw_realizations = []
    for topology in gear.realization.topologies:
        raw_realizations.extend(topology.realizations)
    unique_realizations = {
        _gear_identity(row): row
        for row in raw_realizations
    }
    dual = ExtremeDualBarGearStateCatalogService.build(
        tuple(unique_realizations[key] for key in sorted(unique_realizations)),
        source_denominator_proven=bool(gear.denominator_proven),
        unresolved=tuple(gear.unresolved),
    )

    trait_glyph = ExtremeArmorResourceTraitGlyphStateService(database)
    armor = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        objective,
        trait_glyph_service=trait_glyph,
    ).build(objective)

    provisioning_repository = ProvisioningStaticRepository(database)
    provisioning = ExtremeResourceProvisioningProjectionService(
        provisioning_repository
    ).build(objective)

    potion_repository = PotionAvailabilityRepository(database)
    potion = ExtremeResourcePotionProjectionService(potion_repository).build(objective)

    mundus = MundusRepository(
        database,
        game_update=U50_GAME_UPDATE,
        initialize=False,
    )
    mundus_count = len(mundus.list_names()) + 1  # include no-Mundus baseline

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

    provisioning_raw = len(provisioning_repository.list_names()) + 1
    provisioning_reduced = len(provisioning.choices)
    potion_raw = len(potion_repository.catalog().formulas) + 1
    potion_reduced = 1 if potion.objective_irrelevance_proven else potion_raw

    front_candidates = len(dual.front_admissible_realizations)
    back_candidates = len(dual.back_admissible_realizations)
    active_snapshot_candidates = max(front_candidates, back_candidates)

    finite_per_structural = (
        max(active_snapshot_candidates, 1)
        * max(len(armor.states), 1)
        * max(mundus_count, 1)
        * max(provisioning_reduced, 1)
        * max(potion_reduced, 1)
    )

    print(f"\n{objective.upper()}")
    print(f"races={_fmt(len(universe.races))}")
    print(f"class_routes={_fmt(len(universe.class_routes))}")
    print(
        "attributes="
        f"{_fmt(len(universe.attribute_allocations))} -> {_fmt(len(projection.allocations))} "
        f"projection_complete={projection.projection_complete}"
    )
    print(f"active_bars={_fmt(len(universe.active_bars))}")
    print(f"structural_candidates={_fmt(structural_raw)} -> {_fmt(structural_reduced)}")
    print(f"named_gear_unique_realizations={_fmt(len(unique_realizations))}")
    print(
        "dual_bar_gear="
        f"states={_fmt(len(dual.states))} front={_fmt(front_candidates)} back={_fmt(back_candidates)} "
        f"denominator_proven={dual.denominator_proven}"
    )
    print(
        "resource_armor_states="
        f"{_fmt(len(armor.states))} denominator_proven={armor.denominator_proven}"
    )
    print(f"mundus_states_including_none={_fmt(mundus_count)}")
    print(
        "provisioning="
        f"{_fmt(provisioning_raw)} raw -> {_fmt(provisioning_reduced)} witnesses "
        f"food={provisioning.food_witness!r} drink={provisioning.drink_witness!r} "
        f"projection_complete={provisioning.projection_complete}"
    )
    print(
        "potions="
        f"{_fmt(potion_raw)} raw -> {_fmt(potion_reduced)} scored states "
        f"irrelevance_proven={potion.objective_irrelevance_proven}"
    )
    print(f"finite_axis_pressure_per_structural_candidate={_fmt(finite_per_structural)}")
    print(
        "estimated_reduced_score_pressure="
        f"{_fmt(structural_reduced * finite_per_structural)}"
    )

    unresolved = tuple(
        dict.fromkeys(
            (
                *gear.unresolved,
                *dual.unresolved,
                *armor.unresolved,
                *projection.unresolved,
                *provisioning.unresolved,
                *potion.unresolved,
            )
        )
    )
    if unresolved:
        print("unresolved=")
        for row in unresolved:
            print(f"  - {row}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument(
        "--objective",
        choices=(*_OBJECTIVES, "all"),
        default="all",
    )
    args = parser.parse_args()

    database = Path(args.database)
    objectives = _OBJECTIVES if args.objective == "all" else (args.objective,)
    print("EXTREME RESOURCE SEARCH PRESSURE")
    print(f"Database: {database}")
    print("No build scoring is performed by this audit.")
    for objective in objectives:
        audit(database, objective)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
