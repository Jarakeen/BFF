from __future__ import annotations

"""Construct a Max Magicka high-water mark from independently strongest components.

This diagnostic deliberately does not enumerate named-gear assignments. It asks the
existing proof-owned services for the strongest reviewed witness on each independent
Max Magicka axis, ranks positive named-set breakpoints, and exposes the small set of
remaining interactions that must be assembled into a legal final candidate.

The output is a constructive input ledger, not a global-record proof. Final candidate
scoring still belongs to the canonical Extreme calculation pipeline.
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
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_jewelry_resource_static_trait_state_service import (
    ExtremeJewelryResourceStaticTraitStateService,
)
from services.extreme_resource_attribute_projection_service import (
    ExtremeResourceAttributeProjectionService,
)
from services.extreme_resource_champion_point_state_service import (
    ExtremeResourceChampionPointStateService,
)
from services.extreme_resource_class_route_dominance_projection_service import (
    ExtremeResourceClassRouteDominanceProjectionService,
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


OBJECTIVE = "max_magicka"
TARGET_STAT = StatId.MAX_MAGICKA


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
    parser.add_argument("--target", type=float, default=100000.0)
    parser.add_argument("--gear-limit", type=int, default=30)
    args = parser.parse_args()

    database = Path(args.database)
    universe = ExtremeGlobalSearchUniverseService(database).build()

    race = ExtremeResourceRaceProjectionService(database).build(
        OBJECTIVE,
        tuple(universe.races),
    )
    route = ExtremeResourceClassRouteDominanceProjectionService(database).build(
        OBJECTIVE,
        tuple(universe.class_routes),
    )
    attributes = ExtremeResourceAttributeProjectionService.build(
        OBJECTIVE,
        tuple(universe.attribute_allocations),
    )

    mundus_repository = MundusRepository(
        database,
        game_update=U50_GAME_UPDATE,
        initialize=False,
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
    gear = ExtremeGearSetObjectiveRelevanceService(gear_repository).build(
        OBJECTIVE,
        breakpoints,
    )
    ranked_gear = tuple(
        sorted(
            (
                row
                for row in gear.relevant
                if float(row.reviewed_delta) > 0.0
            ),
            key=lambda row: (
                -float(row.reviewed_delta),
                int(row.piece_count),
                row.set_name.casefold(),
                row.set_name,
            ),
        )
    )
    special_gear = tuple(
        row
        for row in gear.relevant
        if row.search_state_rule is not None or row.candidate.unresolved
    )

    race_name = race.races[0] if race.projection_complete else None
    race_delta = float(race.signatures[0]) if race.projection_complete else 0.0
    route_witness = route.routes[0] if route.projection_complete else None
    attribute_delta = (
        float(attributes.target_points) * float(attributes.per_point_value)
        if attributes.projection_complete
        else 0.0
    )
    food_delta = _provisioning_delta(
        provisioning_repository,
        provisioning.food_witness,
    )
    drink_delta = _provisioning_delta(
        provisioning_repository,
        provisioning.drink_witness,
    )
    mundus_delta = _mundus_delta(mundus_repository, mundus.witness)
    armor_delta = float(best_armor.direct_glyph_delta) if best_armor is not None else 0.0
    jewelry_delta = float(best_jewelry.direct_delta) if best_jewelry is not None else 0.0
    cp_delta = float(champion.reviewed_delta)

    # This subtotal intentionally includes only independently additive reviewed pieces.
    # It is not the final Max Magicka score: base resource, percentage multipliers,
    # Divines amplification, set interactions, and active-bar/runtime passives still
    # belong to canonical final-candidate scoring.
    additive_subtotal = sum(
        (
            race_delta,
            attribute_delta,
            food_delta,
            mundus_delta,
            armor_delta,
            jewelry_delta,
            cp_delta,
        )
    )

    print("EXTREME MAX MAGICKA CONSTRUCTIVE COMPONENT AUDIT")
    print(f"database={database}")
    print(f"target={args.target:g}")
    print("mode=constructive_components_not_exhaustive_search")
    print()

    print("PROVEN / DIRECT COMPONENTS")
    print(
        f"race={race_name or '<unresolved>'} delta={race_delta:g} "
        f"projection_complete={race.projection_complete}"
    )
    if route_witness is not None:
        print(
            "class_route="
            f"{route_witness.base_class.value} subclassed={route_witness.is_subclassed} "
            f"lines={route.signature!r} projection_complete=True"
        )
    else:
        print("class_route=<unresolved> projection_complete=False")
    print(
        f"attributes={attributes.target_points if attributes.projection_complete else 0} "
        f"points delta={attribute_delta:g} projection_complete={attributes.projection_complete}"
    )
    print(
        f"mundus={mundus.witness or '<unresolved>'} base_delta={mundus_delta:g} "
        f"projection_complete={mundus.projection_complete}"
    )
    print(
        f"food={provisioning.food_witness or '<none>'} delta={food_delta:g}"
    )
    print(
        f"drink={provisioning.drink_witness or '<none>'} delta={drink_delta:g}"
    )
    print(f"provisioning_projection_complete={provisioning.projection_complete}")
    print(
        f"potion_relevant_formulas={len(potion.relevant_formulas)} "
        f"objective_irrelevance_proven={potion.objective_irrelevance_proven}"
    )
    print(
        f"armor_best_direct_glyph_delta={armor_delta:g} "
        f"divines={best_armor.divines_count if best_armor else 0} "
        f"infused={best_armor.infused_count if best_armor else 0} "
        f"frontier_states={len(armor.states)} denominator_proven={armor.denominator_proven}"
    )
    if best_armor is not None:
        print("armor_best_direct_state=")
        for piece in best_armor.pieces:
            print(
                f"  {piece.slot}: {piece.trait or '<none>'} / "
                f"{piece.enchant or '<none>'} -> {piece.direct_delta:g}"
            )
    print(
        f"jewelry_static_delta={jewelry_delta:g} "
        f"denominator_proven={jewelry.denominator_proven}"
    )
    if best_jewelry is not None:
        print(f"jewelry_traits={best_jewelry.traits!r}")
    print(
        f"champion_points_delta={cp_delta:g} "
        f"denominator_proven={champion.denominator_proven}"
    )
    print(f"independent_additive_subtotal={additive_subtotal:g}")
    print(
        "NOTE: subtotal is deliberately not a final score; base resource and legal "
        "multipliers/interactions are not double-counted or guessed here."
    )
    print()

    print("RANKED POSITIVE MAX-MAGICKA GEAR BREAKPOINTS")
    print(
        f"gear_breakpoints_reviewed={len(gear.evidence)} "
        f"denominator_proven={gear.denominator_proven}"
    )
    for row in ranked_gear[: max(0, int(args.gear_limit))]:
        special = " special" if row.search_state_rule is not None or row.candidate.unresolved else ""
        print(
            f"  {row.reviewed_delta:10.3f}  {row.piece_count:2d}pc  "
            f"{row.set_name}{special}"
        )
    if len(ranked_gear) > max(0, int(args.gear_limit)):
        print(f"  ... {len(ranked_gear) - max(0, int(args.gear_limit))} more positive breakpoints")

    print()
    print("SPECIAL / INTERACTION-SENSITIVE GEAR TO RETAIN")
    if special_gear:
        for row in special_gear:
            rule = getattr(row.search_state_rule, "value", row.search_state_rule)
            print(
                f"  {row.piece_count}pc {row.set_name}: reviewed_delta={row.reviewed_delta:g} "
                f"search_state_rule={rule or '<none>'} unresolved={len(row.candidate.unresolved)}"
            )
    else:
        print("  <none>")

    unresolved = tuple(
        dict.fromkeys(
            str(item)
            for item in (
                *race.unresolved,
                *route.unresolved,
                *attributes.unresolved,
                *mundus.unresolved,
                *provisioning.unresolved,
                *potion.unresolved,
                *armor.unresolved,
                *jewelry.unresolved,
                *champion.unresolved,
                *gear.unresolved,
            )
            if str(item)
        )
    )
    print()
    print(f"unresolved_count={len(unresolved)}")
    for item in unresolved[:20]:
        print(f"  unresolved: {item}")
    if len(unresolved) > 20:
        print(f"  ... {len(unresolved) - 20} more")

    print()
    print("NEXT_CONSTRUCTIVE_STEP=assemble only legal combinations from these strongest witnesses and interaction-sensitive gear, then canonical-score those candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
