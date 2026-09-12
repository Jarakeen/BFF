from __future__ import annotations

"""Report proof-reduced search pressure for Extreme max-resource ceilings.

This audit deliberately does not score builds and does not enumerate named-gear
assignments. It constructs only cheap source/proof catalogs and reports the raw vs
proof-retained cardinality of each major search axis.
"""

import argparse
from collections import Counter
from math import comb
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
from services.extreme_gear_search_completeness_audit_service import (
    ExtremeGearSearchCompletenessAuditService,
)
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointService,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalogService,
)
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityCatalog,
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_resource_attribute_projection_service import (
    ExtremeResourceAttributeProjectionService,
)
from services.extreme_resource_potion_projection_service import (
    ExtremeResourcePotionProjectionService,
)
from services.extreme_resource_provisioning_projection_service import (
    ExtremeResourceProvisioningProjectionService,
)

_OBJECTIVES = ("max_magicka", "max_stamina")


def _objective_candidate_ids_by_count(
    relevance: ExtremeGearSetObjectiveRelevanceCatalog,
    eligibility: ExtremeNamedGearSetSlotEligibilityCatalog,
) -> dict[int, tuple[int, ...]]:
    """Return objective-surviving physical set ids for each breakpoint count."""

    eligibility_by_id = {int(row.set_id): row for row in eligibility.sets}
    values: dict[int, set[int]] = {}
    for evidence in relevance.evidence:
        if evidence.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
            continue
        count = int(evidence.piece_count)
        set_id = int(evidence.set_id)
        row = eligibility_by_id.get(set_id)
        if row is None or not row.has_physical_slot_evidence:
            continue
        if count > int(row.max_equip_count):
            continue
        values.setdefault(count, set()).add(set_id)
    return {count: tuple(sorted(set_ids)) for count, set_ids in sorted(values.items())}


def _topology_assignment_upper_bound(
    topology: ExtremeGearSetCountTopology,
    candidate_ids_by_count: dict[int, tuple[int, ...]],
) -> int:
    """Cheap pre-enumeration upper bound for one gear topology."""

    multiplicities = Counter(int(value) for value in topology.counts)
    total = 1
    for count, needed in multiplicities.items():
        available = len(candidate_ids_by_count.get(count, ()))
        if available < needed:
            return 0
        total *= comb(available, needed)
    return int(total)


def _print_objective(
    database: Path,
    objective: str,
    *,
    universe,
    repository: GearSetRepository,
    topology,
    breakpoints,
    eligibility,
) -> None:
    print()
    print(objective.upper())

    projection = ExtremeResourceAttributeProjectionService.build(
        objective,
        tuple(universe.attribute_allocations),
    )

    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(
        objective,
        breakpoints,
    )
    gear_audit = ExtremeGearSearchCompletenessAuditService.build(
        topology=topology,
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    candidate_ids_by_count = _objective_candidate_ids_by_count(relevance, eligibility)
    topology_pressure = tuple(
        sorted(
            (
                (_topology_assignment_upper_bound(row, candidate_ids_by_count), row.signature)
                for row in topology.topologies
            ),
            reverse=True,
        )
    )
    named_assignment_upper_bound = sum(value for value, _ in topology_pressure)

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

    # This is intentionally a pressure upper bound, not an execution-count claim.
    # Named-gear branch-and-bound and physical feasibility can reduce it further.
    finite_non_gear_pressure = (
        max(len(armor.states), 1)
        * max(mundus_count, 1)
        * max(retained_provisioning, 1)
        * max(retained_potions, 1)
    )
    estimated_naive_reduced_pressure = (
        structural_reduced
        * max(named_assignment_upper_bound, 1)
        * finite_non_gear_pressure
    )

    print(f"races={len(universe.races):,}")
    print(f"class_routes={len(universe.class_routes):,}")
    print(
        f"attributes={len(universe.attribute_allocations):,}->{len(projection.allocations):,} "
        f"projection_complete={projection.projection_complete}"
    )
    print(f"active_bars={len(universe.active_bars):,}")
    print(f"structural_pressure={structural_raw:,}->{structural_reduced:,}")

    print("named_gear_candidate_sets_by_piece_count=")
    for count, set_ids in candidate_ids_by_count.items():
        print(f"  {count}-piece: {len(set_ids):,}")
    print(f"named_gear_denominator_proven={gear_audit.denominator_proven}")
    print(f"named_assignment_upper_bound_total={named_assignment_upper_bound:,}")
    print("named_assignment_upper_bound_largest_topologies=")
    for value, signature in topology_pressure[:8]:
        print(f"  {signature}: {value:,}")
    if len(topology_pressure) > 8:
        print(f"  ... {len(topology_pressure) - 8:,} more topologies")

    print(f"resource_armor_states={len(armor.states):,}")
    print(f"resource_armor_denominator_proven={armor.denominator_proven}")
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
    print(f"finite_non_gear_pressure_per_structural_candidate={finite_non_gear_pressure:,}")
    print(
        "estimated_naive_reduced_pressure_upper_bound="
        f"{estimated_naive_reduced_pressure:,}"
    )
    print(
        "NOTE: named_assignment_upper_bound is pre-branch-and-bound diagnostic pressure, "
        "not the number of canonical scores production will execute."
    )

    unresolved = tuple(
        dict.fromkeys(
            str(item)
            for item in (
                *tuple(getattr(gear_audit, "unresolved", ()) or ()),
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
        description=(
            "Report proof-reduced Extreme max-resource search pressure without "
            "scoring builds or enumerating named-gear assignments."
        )
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

    universe = ExtremeGlobalSearchUniverseService(database).build()
    repository = GearSetRepository(database)
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()

    print("EXTREME RESOURCE SEARCH PRESSURE")
    print(f"Database: {database}")
    print(
        "This audit constructs proof/source metadata only; it does not score builds "
        "or enumerate named-gear assignments."
    )
    for objective in objectives:
        _print_objective(
            database,
            objective,
            universe=universe,
            repository=repository,
            topology=topology,
            breakpoints=breakpoints,
            eligibility=eligibility,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
