from __future__ import annotations

"""Score the current legal Max Magicka winner with Emperor state removed only.

This is an apples-to-apples companion audit for the 108,319 legal Emperor witness.
It keeps the same named gear, race/class/attributes, Mundus/food/potion search, armor
frontier, jewelry, Champion Points, and bar search.  The only change is clearing the
fixed Extreme Emperor snapshot marker before evaluation.
"""

from pathlib import Path
import re
import sys

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
from services.extreme_best_named_gear_resource_armor_mundus_food_potion_structural_stat_evaluator import ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_hypothetical_racial_progression_service import ExtremeHypotheticalRacialProgressionService
from services.extreme_hypothetical_undaunted_progression_service import ExtremeHypotheticalUndauntedProgressionService
from services.extreme_jewelry_resource_static_trait_state_service import ExtremeJewelryResourceStaticTraitStateService
from services.extreme_max_resource_armor_scoring_frontier_service import ExtremeMaxResourceArmorScoringFrontierService
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealizationService
from services.extreme_named_gear_set_slot_eligibility_service import ExtremeNamedGearSetSlotEligibilityService
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_resource_attribute_projection_service import ExtremeResourceAttributeProjectionService
from services.extreme_resource_class_route_dominance_projection_service import ExtremeResourceClassRouteDominanceProjectionService
from services.extreme_resource_race_projection_service import ExtremeResourceRaceProjectionService
from services.extreme_resource_racial_boundary_relevance_service import ExtremeResourceRacialBoundaryRelevanceService
from services.extreme_structural_core_stat_record_service import ExtremeCanonicalStructuralStatEvaluator
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate
from services.extreme_weapon_resource_relevance_service import ExtremeWeaponResourceRelevanceService

OBJECTIVE = "max_magicka"
EMPEROR_SCORE = 108319.0
WINNING_PACKAGE = (
    ("Crafty Alfiq", 5),
    ("Grace of the Ancients", 3),
    ("Armor of the Trainee", 2),
    ("Infernal Guardian", 1),
    ("Nightflame", 1),
)

_ARMOR_BASE_WARNING = re.compile(r"^(Head|Shoulders|Chest|Hands|Waist|Legs|Feet) armor base: CP160 Gold required")
_WEAPON_BASE_WARNING = re.compile(r"^(Front Bar|Back Bar) weapon base: CP160 Gold required")
_RACIAL_BOUNDARY_PREFIXES = (
    "Non-combat racial passive outside combat capability audit:",
    "Racial passive restores current resources or alters mitigation without changing maximum resources:",
    "Racial passive changes consumable duration or skill-line experience without changing maximum resources:",
)


def _armor_resolved(build_payload: dict, slot: str) -> bool:
    row = dict((build_payload.get("Armor") or {}).get(slot) or {})
    return (
        str(row.get("Level") or "").strip().casefold() == "cp160"
        and str(row.get("Quality") or "").strip().casefold() == "gold"
    )


def _reconcile(database: Path, unresolved, *, build_payload: dict, weapon_irrelevance: bool):
    effective: list[str] = []
    neutralized: list[str] = []
    racial: list[str] = []
    for raw in unresolved:
        msg = str(raw or "").strip()
        if not msg:
            continue
        armor = _ARMOR_BASE_WARNING.match(msg)
        if armor and _armor_resolved(build_payload, armor.group(1)):
            neutralized.append(msg)
            continue
        if _WEAPON_BASE_WARNING.match(msg) and weapon_irrelevance:
            neutralized.append(msg)
            continue
        if msg.startswith(_RACIAL_BOUNDARY_PREFIXES):
            racial.append(msg)
            continue
        effective.append(msg)
    if racial:
        report = ExtremeResourceRacialBoundaryRelevanceService(database).build(OBJECTIVE, tuple(racial))
        neutralized.extend(report.proven_irrelevant)
        effective.extend(report.unresolved)
    return tuple(dict.fromkeys(effective)), tuple(dict.fromkeys(neutralized))


def main() -> int:
    database = ROOT / "data" / "eso.db"
    repository = GearSetRepository(database)
    topology_catalog = ExtremeGearSetTopologyCatalogService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    eligibility_by_name = {str(row.name).casefold(): row for row in eligibility.sets}

    counts = tuple(count for _name, count in WINNING_PACKAGE)
    topology = next((row for row in topology_catalog.topologies if tuple(row.counts) == counts), None)
    if topology is None:
        raise RuntimeError(f"Canonical topology unavailable for counts={counts!r}")

    named = []
    for name, _count in WINNING_PACKAGE:
        row = eligibility_by_name.get(name.casefold())
        if row is None:
            raise RuntimeError(f"Canonical slot eligibility unavailable for set: {name}")
        named.append(row)
    realization = ExtremeNamedGearSetRealizationService.find_witness(topology, tuple(named))
    if realization is None:
        raise RuntimeError("Current 108,319 Max Magicka package has no legal physical witness")

    universe = ExtremeGlobalSearchUniverseService(database).build()
    race_projection = ExtremeResourceRaceProjectionService(database).build(OBJECTIVE, tuple(universe.races))
    route_projection = ExtremeResourceClassRouteDominanceProjectionService(database).build(OBJECTIVE, tuple(universe.class_routes))
    attribute_projection = ExtremeResourceAttributeProjectionService.build(OBJECTIVE, tuple(universe.attribute_allocations))
    if not (race_projection.projection_complete and route_projection.projection_complete and attribute_projection.projection_complete):
        raise RuntimeError("Structural Max Magicka witnesses are not proof-complete")

    canonical_race = ExtremeHypotheticalRacialProgressionService._canonical_skill_line_race(race_projection.races[0])
    route = route_projection.routes[0]
    attributes = attribute_projection.allocations[0]
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=ExtremeOptimizationService(database_path=database),
        progression_service=ExtremeHypotheticalUndauntedProgressionService(database),
    )
    jewelry_catalog = ExtremeJewelryResourceStaticTraitStateService(database).build(OBJECTIVE)
    jewelry_state = jewelry_catalog.states[0] if jewelry_catalog.states else None
    factory = ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory(
        canonical_evaluator=canonical,
        mundus_repository=MundusRepository(database, game_update=U50_GAME_UPDATE, initialize=False),
        provisioning_repository=ProvisioningStaticRepository(database),
        potion_repository=PotionAvailabilityRepository(database, game_update=GameUpdate.U50),
        jewelry_state=jewelry_state,
    )

    armor_catalog = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        OBJECTIVE,
        trait_glyph_service=ExtremeArmorResourceTraitGlyphStateService(database),
    ).build(OBJECTIVE)
    armor_frontier = ExtremeMaxResourceArmorScoringFrontierService.build(OBJECTIVE, armor_catalog)
    armor_states = tuple(armor_frontier.states) if armor_frontier.reduction_proven else tuple(armor_catalog.states)
    weapon = ExtremeWeaponResourceRelevanceService(database).build(OBJECTIVE)

    scored = []
    for bar in ("front", "back"):
        structural = ExtremeStructuralCandidate(
            race=canonical_race,
            class_route=route,
            attributes=attributes,
            active_bar=bar,
        )
        for armor in armor_states:
            evaluator = factory(realization, armor)
            # The production Extreme factory defaults to the legal 6-home-keep Emperor
            # ceiling.  Clear only that fixed marker for this companion benchmark.
            evaluator.base_active_buffs = ()
            value, payload, raw = evaluator(OBJECTIVE, structural)
            effective, neutralized = _reconcile(
                database,
                tuple(raw),
                build_payload=dict(payload.get("build") or {}),
                weapon_irrelevance=weapon.objective_irrelevance_proven,
            )
            scored.append((float(value), bar, armor, dict(payload), tuple(raw), effective, neutralized))

    scored.sort(key=lambda row: (-row[0], len(row[5]), row[1], row[2].identity))
    value, bar, armor, payload, raw, effective, neutralized = scored[0]

    print("EXTREME MAX MAGICKA CURRENT WINNER WITHOUT EMPEROR")
    print(f"database={database}")
    print("scenario=same_108319_winning_build_emperor_marker_removed")
    print(f"emperor_reference={EMPEROR_SCORE:.3f}")
    print(f"non_emperor_value={value:.3f}")
    print(f"emperor_difference={EMPEROR_SCORE - value:.3f}")
    print(f"emperor_relative_gain={(EMPEROR_SCORE / value - 1.0) * 100.0:.3f}%")
    print("sets=" + ", ".join(f"{name} {count}pc" for name, count in zip(realization.set_names, realization.counts)))
    print(f"active_bar={bar}")
    print(f"armor=types:{armor.armor_type_count} divines:{armor.divines_count} infused:{armor.infused_count}")
    print(f"mundus={payload.get('mundus')!r}")
    print(f"food={payload.get('food')!r}")
    print(f"potion={payload.get('potion')!r}")
    print(f"active_buffs={payload.get('active_buffs')!r}")
    print(f"raw_unresolved={len(raw)}")
    print(f"proof_neutralized_unresolved={len(neutralized)}")
    print(f"effective_unresolved={len(effective)}")
    for item in effective:
        print(f"  unresolved: {item}")
    print("non_emperor_benchmark_usable=" + str(not effective))
    return 0 if not effective else 1


if __name__ == "__main__":
    raise SystemExit(main())
