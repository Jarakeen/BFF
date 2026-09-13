from __future__ import annotations

"""Construct a proof-owned Max Health component ledger without exhaustive gear search.

This is the Max Health companion to the Max Magicka constructive audit. It asks the
existing denominator/projection services for the strongest reviewed witness on each
independent axis, ranks positive named-set breakpoints, and classifies the remaining
interaction-sensitive Max Health gear. It does not claim a global record by itself.

Unlike Max Magicka/Stamina, Max Health does not currently have a proof-safe class-route
dominance reducer. The complete legal class/subclass route universe is therefore
retained for later canonical scoring rather than being collapsed here.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.combat_effect_semantics import GameUpdate
from minmax.effects import EffectOperation
from minmax.gear_set_repository import GearSetRepository
from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from minmax.stat_ids import StatId
from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphStateService,
)
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointService,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_jewelry_resource_static_trait_state_service import (
    ExtremeJewelryResourceStaticTraitStateService,
)
from services.extreme_max_health_special_named_gear_branch_service import (
    ExtremeMaxHealthSpecialNamedGearBranchService,
)
from services.extreme_max_resource_ordinary_named_gear_search_service import (
    ExtremeMaxResourceOrdinaryNamedGearSearchService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_resource_attribute_projection_service import (
    ExtremeResourceAttributeProjectionService,
)
from services.extreme_resource_champion_point_state_service import (
    ExtremeResourceChampionPointStateService,
)
from services.extreme_resource_mundus_projection_service import (
    ExtremeResourceMundusProjectionService,
)
from services.extreme_resource_potion_projection_service import (
    ExtremeResourcePotionProjectionService,
)
from services.extreme_resource_provisioning_projection_service import (
    ExtremeResourceProvisioningProjectionService,
)
from services.extreme_resource_race_projection_service import (
    ExtremeResourceRaceProjectionService,
)

OBJECTIVE = "max_health"
TARGET_STAT = StatId.MAX_HEALTH


def _provisioning_delta(repository: ProvisioningStaticRepository, name: str | None) -> float:
    if not name:
        return 0.0
    effects, unresolved = repository.resolve(name)
    if unresolved:
        return 0.0
    return sum(
        float(effect.value)
        for effect in effects
        if effect.stat is TARGET_STAT and effect.operation is EffectOperation.ADD
    )


def _mundus_delta(repository: MundusRepository, name: str | None) -> float:
    if not name:
        return 0.0
    return sum(
        float(row.value)
        for row in repository.get_records(name)
        if str(row.stat_id).strip().casefold() == TARGET_STAT.value.casefold()
        and bool(row.supported)
        and str(row.unit).strip().casefold() == "flat"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--gear-limit", type=int, default=30)
    args = parser.parse_args()

    database = Path(args.database)
    universe = ExtremeGlobalSearchUniverseService(database).build()

    race = ExtremeResourceRaceProjectionService(database).build(
        OBJECTIVE, tuple(universe.races)
    )
    route_count = len(tuple(universe.class_routes))
    route_denominator_retained = bool(
        universe.structural_denominator_proven and route_count > 0
    )
    attributes = ExtremeResourceAttributeProjectionService.build(
        OBJECTIVE, tuple(universe.attribute_allocations)
    )

    mundus_repository = MundusRepository(
        database, game_update=U50_GAME_UPDATE, initialize=False
    )
    mundus = ExtremeResourceMundusProjectionService(mundus_repository).build(OBJECTIVE)

    provisioning_repository = ProvisioningStaticRepository(database)
    provisioning = ExtremeResourceProvisioningProjectionService(
        provisioning_repository
    ).build(OBJECTIVE)

    potion_repository = PotionAvailabilityRepository(
        database,
        game_update=GameUpdate.U50,
    )
    potion = ExtremeResourcePotionProjectionService(potion_repository).build(OBJECTIVE)

    armor = ExtremeArmorResourceTraitGlyphStateService(database).build(OBJECTIVE)
    best_armor = max(
        armor.states,
        key=lambda row: (float(row.direct_glyph_delta), -row.divines_count, row.identity),
        default=None,
    )
    jewelry = ExtremeJewelryResourceStaticTraitStateService(database).build(OBJECTIVE)
    best_jewelry = jewelry.states[0] if jewelry.states else None
    champion = ExtremeResourceChampionPointStateService(database).build(OBJECTIVE)

    gear_repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(gear_repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(gear_repository).build(
        OBJECTIVE, breakpoints
    )
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    ordinary = ExtremeMaxResourceOrdinaryNamedGearSearchService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    topology = __import__(
        "services.extreme_gear_set_topology_catalog_service",
        fromlist=["ExtremeGearSetTopologyCatalogService"],
    ).ExtremeGearSetTopologyCatalogService(gear_repository).build()
    reducer = __import__(
        "services.extreme_objective_named_gear_set_catalog_realization_service",
        fromlist=["ExtremeObjectiveNamedGearSetCatalogRealizationService"],
    ).ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    reduced, equivalent_pruned, representative_limit = reducer.proof_reduced_breakpoints(topology)
    frontier, frontier_pruned = ordinary._frontier(reduced, representative_limit)
    ordinary_candidates, special_pairs = ordinary._candidates(frontier)
    special = ExtremeMaxHealthSpecialNamedGearBranchService(relevance).build(special_pairs)

    ranked_gear = tuple(
        sorted(
            (row for row in relevance.relevant if float(row.reviewed_delta) > 0.0),
            key=lambda row: (
                -float(row.reviewed_delta),
                int(row.piece_count),
                row.set_name.casefold(),
                row.set_name,
            ),
        )
    )

    race_name = race.races[0] if race.projection_complete else None
    race_delta = float(race.signatures[0]) if race.projection_complete else 0.0
    attribute_delta = (
        float(attributes.target_points) * float(attributes.per_point_value)
        if attributes.projection_complete
        else 0.0
    )
    food_delta = _provisioning_delta(provisioning_repository, provisioning.food_witness)
    drink_delta = _provisioning_delta(provisioning_repository, provisioning.drink_witness)
    mundus_delta = _mundus_delta(mundus_repository, mundus.witness)
    armor_delta = float(best_armor.direct_glyph_delta) if best_armor is not None else 0.0
    jewelry_delta = float(best_jewelry.direct_delta) if best_jewelry is not None else 0.0
    cp_delta = float(champion.reviewed_delta)

    print("EXTREME MAX HEALTH CONSTRUCTIVE COMPONENT AUDIT")
    print(f"database={database}")
    print("mode=constructive_components_not_exhaustive_search")
    print(f"structural_denominator_proven={universe.structural_denominator_proven}")
    print()
    print("PROVEN / DIRECT COMPONENTS")
    print(
        f"race={race_name or '<unresolved>'} delta={race_delta:g} "
        f"projection_complete={race.projection_complete}"
    )
    print(
        f"class_routes_retained={route_count} "
        f"full_route_denominator_retained={route_denominator_retained} "
        "dominance_reduction_applied=False"
    )
    print(
        "class_route=<deferred to canonical Max Health scoring; route-sensitive health "
        "passives/runtime states prevent Magicka/Stamina-style dominance collapse>"
    )
    print(
        f"attributes={attributes.target_points if attributes.projection_complete else 0} "
        f"points delta={attribute_delta:g} projection_complete={attributes.projection_complete}"
    )
    print(
        f"mundus={mundus.witness or '<unresolved>'} base_delta={mundus_delta:g} "
        f"projection_complete={mundus.projection_complete}"
    )
    print(f"food={provisioning.food_witness or '<none>'} delta={food_delta:g}")
    print(f"drink={provisioning.drink_witness or '<none>'} delta={drink_delta:g}")
    print(f"provisioning_projection_complete={provisioning.projection_complete}")
    print(
        f"potion_formulas_reviewed={potion.formulas_reviewed} "
        f"relevant_formulas={len(potion.relevant_formulas)} "
        f"objective_irrelevance_proven={potion.objective_irrelevance_proven}"
    )
    print(
        f"armor_best_direct_glyph_delta={armor_delta:g} "
        f"divines={best_armor.divines_count if best_armor else 0} "
        f"infused={best_armor.infused_count if best_armor else 0} "
        f"frontier_states={len(armor.states)} denominator_proven={armor.denominator_proven}"
    )
    print(
        f"jewelry_static_delta={jewelry_delta:g} denominator_proven={jewelry.denominator_proven}"
    )
    if best_jewelry is not None:
        print(f"jewelry_traits={best_jewelry.traits!r}")
    print(
        f"champion_points_delta={cp_delta:g} denominator_proven={champion.denominator_proven}"
    )
    print()

    print("RANKED POSITIVE MAX-HEALTH GEAR BREAKPOINTS")
    print(
        f"gear_breakpoints_reviewed={len(relevance.evidence)} "
        f"relevance_denominator_proven={relevance.denominator_proven}"
    )
    for row in ranked_gear[: max(0, int(args.gear_limit))]:
        print(
            f"  {row.reviewed_delta:10.3f}  {row.piece_count:2d}pc  {row.set_name}"
        )
    if len(ranked_gear) > max(0, int(args.gear_limit)):
        print(f"  ... {len(ranked_gear) - max(0, int(args.gear_limit))} more positive breakpoints")

    print()
    print("PRODUCTION GEAR REDUCTION")
    print(f"equivalent_breakpoints_pruned={equivalent_pruned}")
    print(f"frontier_breakpoints_pruned={frontier_pruned}")
    print(f"representative_limit={representative_limit}")
    print(f"ordinary_candidate_pairs={sum(len(rows) for rows in ordinary_candidates.values())}")
    print(f"special_candidate_pairs={len(special_pairs)}")
    print(f"classified_special_branches={len(special.branches)}")
    print(f"special_denominator_classified={special.denominator_classified}")
    for branch in special.branches:
        condition = getattr(branch, "condition", None)
        rule = getattr(branch, "search_state_rule", None)
        kind = getattr(getattr(branch, "kind", None), "value", getattr(branch, "kind", None))
        print(
            f"  {branch.set_name} {branch.piece_count}pc kind={kind or '<unknown>'} "
            f"condition={condition or '<none>'} rule={getattr(rule, 'value', rule) or '<none>'}"
        )

    unresolved = tuple(
        dict.fromkeys(
            str(item)
            for item in (
                *race.unresolved,
                *attributes.unresolved,
                *mundus.unresolved,
                *provisioning.unresolved,
                *potion.unresolved,
                *armor.unresolved,
                *jewelry.unresolved,
                *champion.unresolved,
                *relevance.unresolved,
                *special.unresolved,
            )
            if str(item)
        )
    )
    print()
    print(f"unresolved_count={len(unresolved)}")
    for item in unresolved[:30]:
        print(f"  unresolved: {item}")
    if len(unresolved) > 30:
        print(f"  ... {len(unresolved) - 30} more")
    print("NEXT_STEP=construct and canonical-score the strongest legal Max Health gear witnesses across the full retained class-route denominator, then promote the best clean incumbent into exact ordinary + targeted special closure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
