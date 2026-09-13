from __future__ import annotations

"""Validate the current constructive Max Magicka high-water package.

This audit deliberately does not reopen the broad named-gear search. It takes the
current best legal package from the constructive frontier, resolves the search race
alias to the canonical racial repository identity, scores every retained Max Magicka
armor tradeoff on both bars, and reconciles only pre-pass unresolved messages that
are independently proven resolved or objective-irrelevant in the completed state.

The result is still a high-water witness rather than a global maximum proof.
"""

import argparse
from pathlib import Path
import re
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
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetTopologyCatalogService,
)
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_hypothetical_racial_progression_service import (
    ExtremeHypotheticalRacialProgressionService,
)
from services.extreme_hypothetical_undaunted_progression_service import (
    ExtremeHypotheticalUndauntedProgressionService,
)
from services.extreme_jewelry_resource_static_trait_state_service import (
    ExtremeJewelryResourceStaticTraitStateService,
)
from services.extreme_max_resource_armor_scoring_frontier_service import (
    ExtremeMaxResourceArmorScoringFrontierService,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_resource_attribute_projection_service import (
    ExtremeResourceAttributeProjectionService,
)
from services.extreme_resource_class_route_dominance_projection_service import (
    ExtremeResourceClassRouteDominanceProjectionService,
)
from services.extreme_resource_race_projection_service import (
    ExtremeResourceRaceProjectionService,
)
from services.extreme_structural_core_stat_record_service import (
    ExtremeCanonicalStructuralStatEvaluator,
)
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate
from services.extreme_weapon_resource_relevance_service import (
    ExtremeWeaponResourceRelevanceService,
)


OBJECTIVE = "max_magicka"
WINNING_PACKAGE = (
    ("Crafty Alfiq", 5),
    ("Necropotence", 4),
    ("Grace of the Ancients", 3),
)

_ARMOR_BASE_WARNING = re.compile(
    r"^(Head|Shoulders|Chest|Hands|Waist|Legs|Feet) armor base: CP160 Gold required"
)
_WEAPON_BASE_WARNING = re.compile(
    r"^(Front Bar|Back Bar) weapon base: CP160 Gold required"
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--target", type=float, default=100000.0)
    return parser


def _armor_metadata_proves_resolved(build_payload: dict, slot_name: str) -> bool:
    armor = dict(build_payload.get("Armor") or {})
    row = dict(armor.get(slot_name) or {})
    level = str(row.get("Level") or "").strip().casefold()
    quality = str(row.get("Quality") or "").strip().casefold()
    return level == "cp160" and quality == "gold"


def _reconcile_unresolved(
    unresolved: tuple[str, ...],
    *,
    build_payload: dict,
    weapon_irrelevance_proven: bool,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Separate raw warnings from warnings proven neutral in the completed state."""

    effective: list[str] = []
    neutralized: list[str] = []
    for raw in unresolved:
        message = str(raw or "").strip()
        if not message:
            continue

        armor_match = _ARMOR_BASE_WARNING.match(message)
        if armor_match and _armor_metadata_proves_resolved(build_payload, armor_match.group(1)):
            neutralized.append(message)
            continue

        if _WEAPON_BASE_WARNING.match(message) and weapon_irrelevance_proven:
            neutralized.append(message)
            continue

        effective.append(message)

    return (
        tuple(dict.fromkeys(effective)),
        tuple(dict.fromkeys(neutralized)),
    )


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)

    gear_repository = GearSetRepository(database)
    topology_catalog = ExtremeGearSetTopologyCatalogService(gear_repository).build()
    eligibility_catalog = ExtremeNamedGearSetSlotEligibilityService(database).build()
    eligibility_by_name = {
        str(row.name).casefold(): row
        for row in eligibility_catalog.sets
    }

    counts = tuple(count for _name, count in WINNING_PACKAGE)
    topology = next(
        (row for row in topology_catalog.topologies if tuple(row.counts) == counts),
        None,
    )
    if topology is None:
        raise RuntimeError(f"Canonical topology unavailable for counts={counts!r}")

    named_sets = []
    for name, _count in WINNING_PACKAGE:
        row = eligibility_by_name.get(name.casefold())
        if row is None:
            raise RuntimeError(f"Canonical slot eligibility unavailable for set: {name}")
        named_sets.append(row)

    realization = ExtremeNamedGearSetRealizationService.find_witness(
        topology,
        tuple(named_sets),
    )
    if realization is None:
        raise RuntimeError("Current Max Magicka high-water package has no legal physical witness")

    universe = ExtremeGlobalSearchUniverseService(database).build()
    race_projection = ExtremeResourceRaceProjectionService(database).build(
        OBJECTIVE,
        tuple(universe.races),
    )
    route_projection = ExtremeResourceClassRouteDominanceProjectionService(database).build(
        OBJECTIVE,
        tuple(universe.class_routes),
    )
    attribute_projection = ExtremeResourceAttributeProjectionService.build(
        OBJECTIVE,
        tuple(universe.attribute_allocations),
    )
    if not (
        race_projection.projection_complete
        and route_projection.projection_complete
        and attribute_projection.projection_complete
    ):
        raise RuntimeError("Structural Max Magicka witnesses are not proof-complete")

    search_race = race_projection.races[0]
    canonical_race = ExtremeHypotheticalRacialProgressionService._canonical_skill_line_race(
        search_race
    )
    route = route_projection.routes[0]
    attributes = attribute_projection.allocations[0]

    optimizer = ExtremeOptimizationService(database_path=database)
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=optimizer,
        progression_service=ExtremeHypotheticalUndauntedProgressionService(database),
    )
    jewelry_catalog = ExtremeJewelryResourceStaticTraitStateService(database).build(OBJECTIVE)
    jewelry_state = jewelry_catalog.states[0] if jewelry_catalog.states else None
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

    armor_catalog = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        OBJECTIVE,
        trait_glyph_service=ExtremeArmorResourceTraitGlyphStateService(database),
    ).build(OBJECTIVE)
    armor_frontier = ExtremeMaxResourceArmorScoringFrontierService.build(
        OBJECTIVE,
        armor_catalog,
    )
    armor_states = (
        tuple(armor_frontier.states)
        if armor_frontier.reduction_proven
        else tuple(armor_catalog.states)
    )
    if not armor_states:
        raise RuntimeError("No Max Magicka armor states available")

    weapon_audit = ExtremeWeaponResourceRelevanceService(database).build(OBJECTIVE)

    scored = []
    started = perf_counter()
    for active_bar in ("front", "back"):
        structural = ExtremeStructuralCandidate(
            race=canonical_race,
            class_route=route,
            attributes=attributes,
            active_bar=active_bar,
        )
        for armor_state in armor_states:
            evaluator = factory(realization, armor_state)
            value, payload, raw_unresolved = evaluator(OBJECTIVE, structural)
            build_payload = dict(payload.get("build") or {})
            effective, neutralized = _reconcile_unresolved(
                tuple(str(item) for item in raw_unresolved if str(item)),
                build_payload=build_payload,
                weapon_irrelevance_proven=weapon_audit.objective_irrelevance_proven,
            )
            scored.append(
                (
                    float(value),
                    active_bar,
                    armor_state,
                    dict(payload),
                    tuple(raw_unresolved),
                    effective,
                    neutralized,
                )
            )

    elapsed = perf_counter() - started
    scored.sort(
        key=lambda row: (
            -row[0],
            len(row[5]),
            row[1],
            row[2].identity,
        )
    )
    best = scored[0]
    value, active_bar, armor_state, payload, raw_unresolved, effective, neutralized = best

    print("EXTREME MAX MAGICKA HIGH-WATER VALIDATION")
    print(f"database={database}")
    print(f"target={args.target:g}")
    print("mode=single_legal_package_canonical_validation")
    print(f"search_race={search_race}")
    print(f"canonical_race={canonical_race}")
    print(
        f"class_route={route.base_class.value} subclassed={route.is_subclassed} "
        f"lines={tuple(route.equipped_skill_lines)!r}"
    )
    print(f"attributes={attributes!r}")
    print(
        "sets="
        + ", ".join(
            f"{name} {count}pc"
            for name, count in zip(realization.set_names, realization.counts)
        )
    )
    print(f"weapon_irrelevance_proven={weapon_audit.objective_irrelevance_proven}")
    print(f"armor_frontier_reduction_proven={armor_frontier.reduction_proven}")
    print(f"armor_states_scored_per_bar={len(armor_states)}")
    print("active_bars_scored=2")
    print(f"canonical_scores={len(scored)}")
    print(f"elapsed_seconds={elapsed:.3f}")
    print()

    print("TOP VALIDATED SCORES")
    for row in scored[:10]:
        score, bar, armor, row_payload, row_raw, row_effective, row_neutralized = row
        print(
            f"  value={score:.3f} gap_to_target={args.target - score:.3f} "
            f"bar={bar} armor_types={armor.armor_type_count} "
            f"divines={armor.divines_count} infused={armor.infused_count} "
            f"effective_unresolved={len(row_effective)} raw_unresolved={len(row_raw)}"
        )
        for key in ("mundus", "food", "potion", "active_buffs"):
            if key in row_payload:
                print(f"    {key}={row_payload[key]!r}")
        if row_effective:
            for item in row_effective[:5]:
                print(f"    unresolved: {item}")
        if row_neutralized:
            print(f"    proof_neutralized={len(row_neutralized)}")

    print()
    print("BEST VALIDATED HIGH-WATER CANDIDATE")
    print(f"value={value:.3f}")
    print(f"target={args.target:g}")
    print(f"gap_to_target={args.target - value:.3f}")
    print(f"meets_target={value >= args.target}")
    print(f"active_bar={active_bar}")
    print(
        f"armor=types:{armor_state.armor_type_count} divines:{armor_state.divines_count} "
        f"infused:{armor_state.infused_count} "
        f"direct_glyph_delta:{armor_state.trait_glyph_state.direct_glyph_delta:g}"
    )
    print(f"raw_unresolved={len(raw_unresolved)}")
    print(f"proof_neutralized_unresolved={len(neutralized)}")
    for item in neutralized:
        print(f"  neutralized: {item}")
    print(f"effective_unresolved={len(effective)}")
    for item in effective:
        print(f"  unresolved: {item}")
    print("payload_race=" + str(payload.get("race") or ""))
    print("racial_progression_applied=" + str(payload.get("racial_progression_applied")))
    print()
    print(
        "NEXT_STEP="
        + (
            "use this legal incumbent to prove omitted gear packages cannot beat it"
            if not effective
            else "resolve remaining effective warnings before using this score as a proof incumbent"
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
