from __future__ import annotations

"""Compose the final theoretical Extreme Stamina Recovery snapshot.

This audit starts from already-closed Stamina Recovery checkpoints: exact same-build
Enlivening/CP, the Torc named-gear champion, the Animal Companions + Curative
Runeforms + Shadow route, seven Medium pieces, and a verified Minor Endurance
carrier. It then proves final active-bar topology, a Two-Handed Torc gear witness,
and the remaining contextual percentage layers.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from minmax.named_combat_buffs import effects_for_buff
from minmax.skill_known_effects import verified_skill_effects
from minmax.stat_ids import StatId
from minmax.support_target_type import SupportTargetType
from services.extreme_armor_weight_filtered_slot_eligibility_service import (
    ExtremeArmorWeightFilteredSlotEligibilityService,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealizationService
from services.extreme_named_gear_set_slot_eligibility_service import ExtremeNamedGearSetSlotEligibilityService
from services.extreme_recovery_passive_special_branch_service import (
    ExtremeRecoveryPassiveBranchKind,
    ExtremeRecoveryPassiveSpecialBranchService,
)
from services.extreme_skill_universe_service import ExtremeSkillUniverseService
from tools.audit_extreme_magicka_recovery_combined_active_bar_frontier import _bar_shape_legal, _capacity

OBJECTIVE = "stamina_recovery"
BASE_PREGEAR = 3022.86328
NAMED_GEAR_CHAMPION = 1487.0
MEDIUM_ARMOR_PERCENT = 28.0
STATIC_ROUTE_PERCENT = 33.0  # Erudition 18 + Refreshing Shadows 15.
FLOURISH_PERCENT = 20.0
MINOR_ENDURANCE_BASE_ID = 183555
TWO_HANDED_TYPES = frozenset({"Two-Handed Sword", "Two-Handed Axe", "Two-Handed Mace"})
CHAMPION_SET_COUNTS = (
    ("Jailbreaker", 5),
    ("Coward's Gear", 5),
    ("Bloodspawn", 1),
    ("Torc of Tonal Constancy", 1),
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--home-keeps", type=int, default=6)
    return parser


def _named_percent(name: str) -> tuple[float | None, tuple[str, ...]]:
    rows = tuple(
        row
        for row in effects_for_buff(name)
        if row.stat is StatId.STAMINA_RECOVERY and row.bucket == "resource_percent"
    )
    if len(rows) != 1:
        return None, (f"Expected one canonical {name} Stamina Recovery effect, found {len(rows)}",)
    return float(rows[0].value) * 100.0, ()


def _passive_branch(database: Path, passive_name: str):
    universe = ExtremeSkillUniverseService(database)
    matches = tuple(row for row in universe.passives() if row.name.strip().casefold() == passive_name.casefold())
    if len(matches) != 1:
        return None, (f"Expected one passive named {passive_name!r}, found {len(matches)}",)
    branch = ExtremeRecoveryPassiveSpecialBranchService.classify(matches[0], OBJECTIVE)
    if branch is None:
        return None, (f"Passive {passive_name!r} did not classify for {OBJECTIVE}",)
    return branch, ()


def _minor_endurance_percent() -> tuple[float | None, tuple[str, ...]]:
    rows = tuple(
        row
        for row in verified_skill_effects(MINOR_ENDURANCE_BASE_ID, 0)
        if row.name == "minor_endurance"
        and row.target_type is SupportTargetType.SELF
        and row.condition is None
        and row.trigger is None
    )
    if len(rows) != 1:
        return None, (f"Expected one verified Arcanist's Domain Minor Endurance effect, found {len(rows)}",)
    return float(rows[0].magnitude) * 100.0, ()


def _two_handed_champion_witness(database: Path):
    raw = ExtremeNamedGearSetSlotEligibilityService(database).build()
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        database, raw, required_armor_weight="Medium"
    )
    by_name = {row.name: row for row in filtered.catalog.sets}
    missing = tuple(name for name, _count in CHAMPION_SET_COUNTS if name not in by_name)
    if missing:
        return None, filtered.denominator_proven, (f"Champion set eligibility missing: {missing!r}",)
    named_sets = tuple(by_name[name] for name, _count in CHAMPION_SET_COUNTS)
    topology = ExtremeGearSetCountTopology(
        counts=tuple(count for _name, count in CHAMPION_SET_COUNTS),
        unused_units=0,
    )
    witness = ExtremeNamedGearSetRealizationService.find_witness(
        topology,
        named_sets,
        required_weapon_types=TWO_HANDED_TYPES,
    )
    if witness is None:
        return None, filtered.denominator_proven, ("Torc champion has no legal Two-Handed physical witness",)
    return witness, filtered.denominator_proven, ()


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    unresolved: list[str] = []

    minor, errors = _minor_endurance_percent()
    unresolved.extend(errors)
    major, errors = _named_percent("Major Endurance")
    unresolved.extend(errors)

    continuous, errors = _passive_branch(database, "Continuous Attack")
    unresolved.extend(errors)
    battle_rush, errors = _passive_branch(database, "Battle Rush")
    unresolved.extend(errors)
    domination, errors = _passive_branch(database, "Domination")
    unresolved.extend(errors)

    def conditional_percent(branch, name: str, expected: float) -> float:
        if branch is None:
            return 0.0
        if branch.kind is not ExtremeRecoveryPassiveBranchKind.CONDITIONAL_PERCENT:
            unresolved.append(f"{name} classified as {branch.kind.value}, expected conditional_percent")
        value = float(branch.percent_ceiling or 0.0)
        if abs(value - expected) > 1e-9:
            unresolved.append(f"{name} percent ceiling is {value}, expected {expected}")
        return value

    continuous_percent = conditional_percent(continuous, "Continuous Attack", 20.0)
    battle_rush_percent = conditional_percent(battle_rush, "Battle Rush", 30.0)
    domination_percent = conditional_percent(domination, "Domination", 100.0)
    if int(args.home_keeps) != 6:
        unresolved.append("Final theoretical snapshot requires six Home Keeps for Domination ceiling")

    universe = ExtremeSkillUniverseService(database)
    animal = _capacity(universe, "Animal Companions")
    curative = _capacity(universe, "Curative Runeforms")
    legal_bar = _bar_shape_legal(((1, animal), (1, curative)))
    if not legal_bar:
        unresolved.append("One Animal Companions + one Curative Runeforms counted bar is not legal")

    carrier = tuple(
        row for row in universe.actives()
        if row.name.strip().casefold() == "arcanist's domain".casefold()
    )
    carrier_normal = bool(
        carrier
        and all("ultimate" not in str(row.skill_type or "").casefold() for row in carrier)
        and any(str(row.skill_line or "").strip().casefold() == "curative runeforms" for row in carrier)
    )
    if not carrier_normal:
        unresolved.append("Arcanist's Domain is not proven as a normal Curative Runeforms bar skill")

    witness, medium_filter_proven, errors = _two_handed_champion_witness(database)
    unresolved.extend(errors)
    weapon_types = () if witness is None else tuple(row.weapon_type for row in witness.weapon_assignments)
    two_handed_witness = bool(witness is not None and any(item in TWO_HANDED_TYPES for item in weapon_types))

    minor_percent = float(minor or 0.0)
    major_percent = float(major or 0.0)
    class_percent = STATIC_ROUTE_PERCENT + FLOURISH_PERCENT
    standing_percent = MEDIUM_ARMOR_PERCENT + class_percent + minor_percent
    contextual_percent = major_percent + continuous_percent + battle_rush_percent + domination_percent
    total_percent = standing_percent + contextual_percent
    pre_percent = BASE_PREGEAR + NAMED_GEAR_CHAMPION

    standing_final = pre_percent * (1.0 + standing_percent / 100.0)
    major_final = pre_percent * (1.0 + (standing_percent + major_percent) / 100.0)
    continuous_final = pre_percent * (1.0 + (standing_percent + major_percent + continuous_percent) / 100.0)
    battle_final = pre_percent * (1.0 + (standing_percent + major_percent + continuous_percent + battle_rush_percent) / 100.0)
    final_value = pre_percent * (1.0 + total_percent / 100.0)

    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = bool(
        medium_filter_proven
        and two_handed_witness
        and legal_bar
        and carrier_normal
        and abs(minor_percent - 15.0) <= 1e-9
        and abs(major_percent - 30.0) <= 1e-9
        and abs(class_percent - 53.0) <= 1e-9
        and abs(continuous_percent - 20.0) <= 1e-9
        and abs(battle_rush_percent - 30.0) <= 1e-9
        and abs(domination_percent - 100.0) <= 1e-9
        and not unique_unresolved
    )

    print("EXTREME STAMINA RECOVERY FINAL SNAPSHOT AUDIT")
    print(f"database={database}")
    print(f"base_pregear={BASE_PREGEAR:.3f}")
    print(f"named_gear_champion='Torc of Tonal Constancy'")
    print(f"named_gear_prepercent={NAMED_GEAR_CHAMPION:.3f}")
    print(f"pre_percent={pre_percent:.3f}")
    print()
    print("LEGALITY")
    print(f"promoted_route=('animal_companions', 'curative_runeforms', 'shadow')")
    print(f"counted_bar=(animal=1, carrier=\"Arcanist's Domain\")")
    print(f"five_normal_plus_one_ultimate_bar_legal={legal_bar}")
    print(f"minor_endurance_carrier_normal_skill={carrier_normal}")
    print(f"two_handed_torc_witness={two_handed_witness}")
    print(f"weapon_types={weapon_types!r}")
    if witness is not None:
        print("gear_assignments=" + repr(tuple((row.slot, row.set_name, row.weapon_type) for row in witness.assignments)))
    print()
    print("STANDING PERCENT LAYERS")
    print(f"medium_armor_recovery_percent={MEDIUM_ARMOR_PERCENT:.3f}")
    print(f"class_route_static_plus_flourish_percent={class_percent:.3f}")
    print(f"minor_endurance_percent={minor_percent:.3f}")
    print(f"standing_total_percent={standing_percent:.3f}")
    print(f"standing_final={standing_final:.3f}")
    print()
    print("CONTEXTUAL PERCENT LAYERS")
    print(f"major_endurance_percent={major_percent:.3f}")
    print(f"continuous_attack_percent={continuous_percent:.3f}")
    print(f"battle_rush_percent={battle_rush_percent:.3f}")
    print(f"domination_percent={domination_percent:.3f}")
    print(f"contextual_total_percent={contextual_percent:.3f}")
    print(f"major_endurance_final={major_final:.3f}")
    print(f"major_plus_continuous_final={continuous_final:.3f}")
    print(f"major_plus_continuous_plus_battle_rush_final={battle_final:.3f}")
    print()
    print("FINAL")
    print(f"total_percent={total_percent:.3f}")
    print(f"final_stamina_recovery={final_value:.3f}")
    print()
    print("PROOF GATES")
    print(f"medium_armor_physical_filter_proven={medium_filter_proven}")
    print(f"torc_two_handed_compatible={two_handed_witness}")
    print(f"active_bar_topology_proven={legal_bar and carrier_normal}")
    print(f"minor_endurance_15_proven={abs(minor_percent - 15.0) <= 1e-9}")
    print(f"major_endurance_30_proven={abs(major_percent - 30.0) <= 1e-9}")
    print(f"continuous_attack_20_proven={abs(continuous_percent - 20.0) <= 1e-9}")
    print(f"battle_rush_30_proven={abs(battle_rush_percent - 30.0) <= 1e-9}")
    print(f"domination_100_proven={abs(domination_percent - 100.0) <= 1e-9}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"final_snapshot_closed={closed}")
    print(
        "NEXT_STEP=promote the closed Stamina Recovery record into the Extreme result/runtime layer"
        if closed
        else "NEXT_STEP=close only the reported final-snapshot blockers"
    )
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
