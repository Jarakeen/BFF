from __future__ import annotations

"""Final proof-aware closure for the Update 50 Extreme Max Magicka record.

This audit intentionally does NOT call the legacy exhaustive whole-record search.
It composes the proof-owned finite/reduced axes with the exact ordinary named-gear
branch-and-bound and the already-targeted special/runtime denominator search.

The record is published only when all of the following agree:

* canonical structural universe is complete;
* race, class route, attributes, Mundus, provisioning, armor, jewelry, Champion
  Points, passives, active skills, equipment traits, runtime conditions, potions,
  weapons, and Emperor state are proof-closed for Max Magicka;
* the current 5+3+2+1+1 named-gear witness is physically legal and canonical-scores
  to the incumbent with no effective unresolved evidence;
* exact ordinary named gear has no legal topology above the incumbent gear delta;
* classified special/runtime named gear has no canonical challenger above the
  incumbent and has no unknown proof warning.

This is the replacement for the old ``audit_extreme_resource_record_closure.py
--full`` Max Magicka path, which intentionally enumerated the complete generic
named-gear Cartesian space and is not used here.
"""

import argparse
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.combat_effect_semantics import GameUpdate
from minmax.emperor_passive_input_resolver import EmperorPassiveInputResolver
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
from services.extreme_global_search_universe_service import (
    ExtremeGlobalSearchUniverseService,
)
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
from services.extreme_resource_active_skill_coverage_audit_service import (
    ExtremeResourceActiveSkillCoverageAuditService,
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
from services.extreme_resource_equipment_trait_projection_coverage_service import (
    ExtremeResourceEquipmentTraitProjectionCoverageService,
)
from services.extreme_resource_mundus_projection_service import (
    ExtremeResourceMundusProjectionService,
)
from services.extreme_resource_passive_coverage_audit_service import (
    ExtremeResourcePassiveCoverageAuditService,
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
from services.extreme_resource_runtime_projection_coverage_service import (
    ExtremeResourceRuntimeProjectionCoverageService,
)
from services.extreme_structural_core_stat_record_service import (
    ExtremeCanonicalStructuralStatEvaluator,
)
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate
from services.extreme_weapon_resource_relevance_service import (
    ExtremeWeaponResourceRelevanceService,
)
from tools import audit_extreme_max_magicka_non_emperor_winner as winner_contract
from tools import audit_extreme_max_magicka_ordinary_exact_closure as ordinary_closure
from tools import audit_extreme_max_magicka_special_runtime_closure as special_closure


OBJECTIVE = "max_magicka"
DEFAULT_INCUMBENT = 108319.0
DEFAULT_GEAR_DELTA = 12986.0
EXPECTED_EMPEROR_HOME_KEEPS = 6
EXPECTED_EMPEROR_PERCENT = 0.75


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--incumbent", type=float, default=DEFAULT_INCUMBENT)
    parser.add_argument("--gear-threshold", type=float, default=DEFAULT_GEAR_DELTA)
    return parser


def _run_tool(module, argv: list[str]) -> tuple[int, str]:
    original_argv = list(sys.argv)
    stream = StringIO()
    try:
        sys.argv = [getattr(module, "__name__", "audit"), *argv]
        with redirect_stdout(stream):
            code = int(module.main())
    finally:
        sys.argv = original_argv
    return code, stream.getvalue()


def _bool_line(text: str, name: str) -> bool:
    return re.search(rf"(?m)^{re.escape(name)}=True\s*$", text) is not None


def _float_line(text: str, name: str) -> float | None:
    match = re.search(rf"(?m)^{re.escape(name)}=([-+0-9.]+)\s*$", text)
    return None if match is None else float(match.group(1))


def _int_line(text: str, name: str) -> int | None:
    match = re.search(rf"(?m)^{re.escape(name)}=(\d+)\s*$", text)
    return None if match is None else int(match.group(1))


def _emperor_axis_proven() -> bool:
    table = dict(EmperorPassiveInputResolver.MAX_RESOURCE_PERCENT_BY_HOME_KEEPS)
    keys = tuple(sorted(int(key) for key in table))
    values = tuple(float(table[key]) for key in keys)
    monotonic = all(left <= right + 1e-12 for left, right in zip(values, values[1:]))
    return bool(
        keys == tuple(range(EXPECTED_EMPEROR_HOME_KEEPS + 1))
        and monotonic
        and max(values, default=float("-inf")) == EXPECTED_EMPEROR_PERCENT
        and float(table.get(EXPECTED_EMPEROR_HOME_KEEPS, -1.0)) == EXPECTED_EMPEROR_PERCENT
    )


def _score_incumbent(database: Path):
    repository = GearSetRepository(database)
    topology_catalog = ExtremeGearSetTopologyCatalogService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    eligibility_by_name = {str(row.name).casefold(): row for row in eligibility.sets}

    counts = tuple(count for _name, count in winner_contract.WINNING_PACKAGE)
    topology = next(
        (row for row in topology_catalog.topologies if tuple(row.counts) == counts),
        None,
    )
    if topology is None:
        raise RuntimeError(f"Canonical topology unavailable for incumbent counts={counts!r}")

    named = []
    for name, _count in winner_contract.WINNING_PACKAGE:
        row = eligibility_by_name.get(name.casefold())
        if row is None:
            raise RuntimeError(f"Canonical slot eligibility unavailable for incumbent set: {name}")
        named.append(row)
    realization = ExtremeNamedGearSetRealizationService.find_witness(topology, tuple(named))
    if realization is None:
        raise RuntimeError("Current Max Magicka incumbent has no legal physical named-gear witness")

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
    if not (race.projection_complete and route.projection_complete and attributes.projection_complete):
        raise RuntimeError("Incumbent structural projections are not proof-complete")

    canonical_race = ExtremeHypotheticalRacialProgressionService._canonical_skill_line_race(
        race.races[0]
    )
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=ExtremeOptimizationService(database_path=database),
        progression_service=ExtremeHypotheticalUndauntedProgressionService(database),
    )
    jewelry = ExtremeJewelryResourceStaticTraitStateService(database).build(OBJECTIVE)
    if not jewelry.states:
        raise RuntimeError("No canonical Max Magicka jewelry state")

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
        jewelry_state=jewelry.states[0],
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
    weapon = ExtremeWeaponResourceRelevanceService(database).build(OBJECTIVE)

    scored = []
    for bar in ("front", "back"):
        structural = ExtremeStructuralCandidate(
            race=canonical_race,
            class_route=route.routes[0],
            attributes=attributes.allocations[0],
            active_bar=bar,
        )
        for armor in armor_states:
            evaluator = factory(realization, armor)
            value, payload, raw = evaluator(OBJECTIVE, structural)
            effective, neutralized = winner_contract._reconcile(
                database,
                tuple(raw),
                build_payload=dict(payload.get("build") or {}),
                weapon_irrelevance=weapon.objective_irrelevance_proven,
            )
            scored.append(
                (
                    float(value),
                    bar,
                    armor,
                    dict(payload),
                    tuple(raw),
                    tuple(effective),
                    tuple(neutralized),
                )
            )

    if not scored:
        raise RuntimeError("No canonical incumbent score states were produced")
    scored.sort(key=lambda row: (-row[0], len(row[5]), row[1], row[2].identity))
    return realization, armor_frontier, scored[0]


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    incumbent = float(args.incumbent)
    gear_threshold = float(args.gear_threshold)

    universe = ExtremeGlobalSearchUniverseService(database).build()
    race = ExtremeResourceRaceProjectionService(database).build(OBJECTIVE, tuple(universe.races))
    route = ExtremeResourceClassRouteDominanceProjectionService(database).build(
        OBJECTIVE,
        tuple(universe.class_routes),
    )
    attributes = ExtremeResourceAttributeProjectionService.build(
        OBJECTIVE,
        tuple(universe.attribute_allocations),
    )
    mundus = ExtremeResourceMundusProjectionService(
        MundusRepository(database, game_update=U50_GAME_UPDATE, initialize=False)
    ).build(OBJECTIVE)
    provisioning = ExtremeResourceProvisioningProjectionService(
        ProvisioningStaticRepository(database)
    ).build(OBJECTIVE)
    potion = ExtremeResourcePotionProjectionService(
        PotionAvailabilityRepository(database, game_update=GameUpdate.U50)
    ).build(OBJECTIVE)

    armor = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        OBJECTIVE,
        trait_glyph_service=ExtremeArmorResourceTraitGlyphStateService(database),
    ).build(OBJECTIVE)
    jewelry = ExtremeJewelryResourceStaticTraitStateService(database).build(OBJECTIVE)
    champion = ExtremeResourceChampionPointStateService(database).build(OBJECTIVE)
    passives = ExtremeResourcePassiveCoverageAuditService(database).build(OBJECTIVE)
    active_skills = ExtremeResourceActiveSkillCoverageAuditService(database).build(OBJECTIVE)
    equipment = ExtremeResourceEquipmentTraitProjectionCoverageService(database).build(OBJECTIVE)
    runtime = ExtremeResourceRuntimeProjectionCoverageService(database).build(OBJECTIVE)
    weapon = ExtremeWeaponResourceRelevanceService(database).build(OBJECTIVE)

    realization, armor_frontier, incumbent_row = _score_incumbent(database)
    value, bar, armor_state, payload, raw, effective, neutralized = incumbent_row
    active_buffs = tuple(str(item) for item in tuple(payload.get("active_buffs") or ()))
    emperor_marker = f"__emperor_home_keeps__:{EXPECTED_EMPEROR_HOME_KEEPS}"

    ordinary_code, ordinary_output = _run_tool(
        ordinary_closure,
        [
            "--database",
            str(database),
            "--incumbent",
            f"{incumbent:.12g}",
            "--gear-threshold",
            f"{gear_threshold:.12g}",
        ],
    )
    special_code, special_output = _run_tool(
        special_closure,
        [
            "--database",
            str(database),
            "--incumbent",
            f"{incumbent:.12g}",
        ],
    )

    ordinary_best = _float_line(ordinary_output, "best_exact_ordinary_gear_delta")
    ordinary_above = _int_line(ordinary_output, "topologies_above_threshold")
    special_best = _float_line(special_output, "best_canonical_challenger")
    unknown_special_warnings = _int_line(special_output, "unknown_warning_occurrences")

    axes = {
        "structural_universe": bool(universe.structural_denominator_proven),
        "race_projection": bool(race.projection_complete and not race.unresolved),
        "class_route_projection": bool(route.projection_complete and not route.unresolved),
        "attribute_projection": bool(attributes.projection_complete and not attributes.unresolved),
        "mundus_projection": bool(mundus.projection_complete and not mundus.unresolved),
        "provisioning_projection": bool(
            provisioning.projection_complete and not provisioning.unresolved
        ),
        "potion_irrelevance": bool(potion.objective_irrelevance_proven),
        "armor_denominator": bool(armor.denominator_proven and not armor.unresolved),
        "armor_frontier_reduction": bool(armor_frontier.reduction_proven),
        "jewelry_denominator": bool(jewelry.denominator_proven and not jewelry.unresolved),
        "champion_point_denominator": bool(
            champion.denominator_proven and not champion.unresolved
        ),
        "passive_projection": bool(passives.projection_complete and not passives.unresolved),
        "active_skill_projection": bool(
            active_skills.projection_complete and not active_skills.unresolved
        ),
        "equipment_trait_projection": bool(
            equipment.projection_complete and not equipment.unresolved
        ),
        "runtime_projection": bool(runtime.projection_complete and not runtime.unresolved),
        "weapon_irrelevance": bool(weapon.objective_irrelevance_proven),
        "emperor_monotonic_max": _emperor_axis_proven(),
        "emperor_witness_active": emperor_marker in active_buffs,
        "incumbent_physical_witness": realization is not None,
        "incumbent_canonical_score": abs(value - incumbent) <= 1e-6,
        "incumbent_effective_unresolved_zero": not effective,
        "ordinary_exact_closure": bool(
            ordinary_code == 0
            and _bool_line(ordinary_output, "ordinary_exact_frontier_closed")
            and _bool_line(ordinary_output, "ordinary_denominator_proven")
            and ordinary_best is not None
            and ordinary_best <= gear_threshold + 1e-9
            and ordinary_above == 0
        ),
        "special_runtime_closure": bool(
            special_code == 0
            and _bool_line(special_output, "special_frontier_closed")
            and _bool_line(special_output, "structural_denominator_clean")
            and _bool_line(special_output, "global_runtime_projection_complete")
            and special_best is not None
            and special_best <= incumbent + 1e-9
            and unknown_special_warnings == 0
        ),
    }

    print("EXTREME MAX MAGICKA FINAL WHOLE-RECORD CLOSURE")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print("legacy_exhaustive_whole_record_search_used=False")
    print("composition=proof_owned_axes+exact_ordinary_branch_and_bound+targeted_special_runtime")
    print(f"incumbent={incumbent:.3f}")
    print(f"incumbent_gear_delta={gear_threshold:.3f}")
    print()

    print("PROOF AXES")
    for name, complete in axes.items():
        print(f"{name}={complete}")

    print("\nINCUMBENT WITNESS")
    print(f"canonical_value={value:.3f}")
    print(
        "sets="
        + ", ".join(
            f"{name} {count}pc"
            for name, count in zip(realization.set_names, realization.counts)
        )
    )
    print(f"active_bar={bar}")
    print(
        f"armor=types:{armor_state.armor_type_count} "
        f"divines:{armor_state.divines_count} infused:{armor_state.infused_count}"
    )
    print(f"mundus={payload.get('mundus')!r}")
    print(f"food={payload.get('food')!r}")
    print(f"potion={payload.get('potion')!r}")
    print(f"active_buffs={payload.get('active_buffs')!r}")
    print(f"raw_unresolved={len(raw)}")
    print(f"proof_neutralized_unresolved={len(neutralized)}")
    print(f"effective_unresolved={len(effective)}")
    for item in effective:
        print(f"  unresolved: {item}")

    print("\nGEAR CLOSURE")
    print(f"ordinary_audit_exit_code={ordinary_code}")
    print(f"ordinary_best_exact_flat_delta={ordinary_best}")
    print(f"ordinary_topologies_above_threshold={ordinary_above}")
    print(f"special_audit_exit_code={special_code}")
    print(f"special_best_canonical_challenger={special_best}")
    print(f"special_unknown_warning_occurrences={unknown_special_warnings}")

    unresolved = tuple(
        dict.fromkeys(
            str(item)
            for item in (
                *universe.unresolved,
                *race.unresolved,
                *route.unresolved,
                *attributes.unresolved,
                *mundus.unresolved,
                *provisioning.unresolved,
                *potion.unresolved,
                *armor.unresolved,
                *jewelry.unresolved,
                *champion.unresolved,
                *passives.unresolved,
                *active_skills.unresolved,
                *equipment.unresolved,
                *runtime.unresolved,
                *weapon.unresolved,
                *effective,
            )
            if str(item)
        )
    )
    print(f"\nwhole_record_unresolved_count={len(unresolved)}")
    for item in unresolved:
        print(f"  unresolved: {item}")

    closed = bool(all(axes.values()) and not unresolved)
    print(f"whole_record_denominator_closed={closed}")
    if closed:
        print(f"PROVEN_MAX_MAGICKA_RECORD={incumbent:.3f}")
        print(
            "RECORD_CONTEXT=Update 50 Extreme legal snapshot with active Emperor and 6 Home Keeps"
        )
        print(
            "NEXT_STEP=record proof is closed; expose the proven build and its scenario qualifiers in Extreme Build UI"
        )
        return 0

    print("PROVEN_MAX_MAGICKA_RECORD=<not yet closed>")
    print("NEXT_STEP=resolve the False proof axis or listed unresolved evidence; do not reopen already-green axes")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
