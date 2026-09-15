from __future__ import annotations

"""Translate legal Weapon Damage gear states into finite Sorcerer resource requirements.

This audit is an algebraic bridge between the physical named-gear frontier and the
final same-build whole-character search. It does not pretend that independently
maximized Max Resource is simultaneously present. Instead it fixes the reviewed
Weapon-Damage-maximizing non-gear/pre-class subtotal, adds each mechanic-complete
physical gear Pareto state's reviewed Weapon Damage, then asks how much *total*
higher Max Magicka/Stamina pure Sorcerer needs for Font of Power + Calculated
Defense to beat the strongest reviewed non-Sorcerer pure-class mastery route.

The gear state's own reviewed Max Magicka/Stamina contribution is then subtracted
from that total threshold. The result is the minimum higher Max Resource that the
rest of the exact same build must supply. This turns the coupled whole-build search
into a finite threshold test without mixing independent resource maxima.
"""

from math import floor
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.character_build.character_class import CharacterClass
from minmax.item_base_stats import (
    DUAL_WIELD_OFFHAND_POWER_RATIO,
    NAKED_LEVEL_50_POWER,
    WEAPON_NIRNHONED_PERCENT_GOLD,
    WEAPON_POWER_CP160_GOLD,
)
from minmax.gear_set_repository import GearSetRepository
from services.extreme_class_mastery_pair_service import ExtremeClassMasteryPairService
from tools.audit_extreme_weapon_damage_joint_named_gear_realization import (
    _filtered_breakpoints,
    _filtered_eligibility,
    _filtered_topologies,
    _realized_pareto,
    _score_realization,
    _survivor_rows,
)
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
)
from tools.audit_extreme_weapon_damage_preweapon_upper_bound import (
    BASE_LEVEL_50_POWER,
    _courage_ceiling,
    _cp_ceiling,
    _jewelry_ceiling,
    _mundus_ceiling,
    _race_ceiling,
    _weapon_enchant_ceiling,
)
from tools.audit_extreme_weapon_damage_weapon_runtime_frontier import (
    TWIN_BLADE_SWORD_DAMAGE_PER_SWORD,
)

DATABASE = ROOT / "data" / "eso.db"
OBJECTIVE = "weapon_damage"
RESOURCE_STEP = 1750
MAX_RESOURCE_PROOF_CEILING = 108_319.0


def _nirn_bonus(power: float, *, scale: float = 1.0) -> float:
    improved = float(floor(float(power) * (1.0 + WEAPON_NIRNHONED_PERCENT_GOLD)))
    return (improved - float(power)) * float(scale)


def _dual_wield_static_delta() -> float:
    one_hand = float(WEAPON_POWER_CP160_GOLD["Sword"])
    dual_base = (one_hand - NAKED_LEVEL_50_POWER) + floor(
        one_hand * DUAL_WIELD_OFFHAND_POWER_RATIO
    )
    dual_nirn = _nirn_bonus(one_hand) + _nirn_bonus(
        one_hand,
        scale=DUAL_WIELD_OFFHAND_POWER_RATIO,
    )
    dual_sword_passive = 2.0 * float(TWIN_BLADE_SWORD_DAMAGE_PER_SWORD)
    return float(dual_base + dual_nirn + dual_sword_passive)


def _nongear_preclass_weapon_damage() -> tuple[float, tuple[tuple[str, float], ...]]:
    race_name, race = _race_ceiling()
    components = (
        ("base_level_50_power", float(BASE_LEVEL_50_POWER)),
        (f"race:{race_name}", float(race)),
        ("bloodthirsty_plus_glyph_jewelry", float(_jewelry_ceiling())),
        ("warrior_divines_mundus", float(_mundus_ceiling())),
        ("cp_flat", float(_cp_ceiling())),
        ("minor_plus_major_courage", float(_courage_ceiling())),
        ("ordinary_weapon_damage_enchant", float(_weapon_enchant_ceiling())),
        ("dual_wield_static_weapon", float(_dual_wield_static_delta())),
    )
    return sum(value for _name, value in components), components


def _physical_frontier():
    repository = GearSetRepository(DATABASE)
    original_breakpoints, _pareto_rows, _unresolved_rows, survivor_by_key = _survivor_rows(repository)
    breakpoints = _filtered_breakpoints(original_breakpoints, survivor_by_key)
    eligibility = _filtered_eligibility(survivor_by_key)
    topologies = _filtered_topologies(repository, breakpoints)
    realization_service = ExtremeNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
    )

    scores = []
    for topology in topologies.topologies:
        result = realization_service.realize_topology(topology)
        scores.extend(
            _score_realization(witness, survivor_by_key)
            for witness in result.realizations
        )
    return _realized_pareto(tuple(scores)), eligibility


def _best_non_sorcerer(service: ExtremeClassMasteryPairService, reference: float):
    rows = []
    for base_class in CharacterClass:
        if base_class is CharacterClass.SORCERER:
            continue
        row = service.best_for_class(
            base_class,
            OBJECTIVE,
            reference_value=reference,
        )
        if row is not None and row.projected_delta is not None:
            rows.append(row)
    return max(
        rows,
        key=lambda row: (
            float(row.projected_delta or 0.0),
            row.base_class.value,
            row.passive_names,
        ),
        default=None,
    )


def _sorcerer(
    service: ExtremeClassMasteryPairService,
    reference: float,
    higher_resource: float,
):
    return service.best_for_class(
        CharacterClass.SORCERER,
        OBJECTIVE,
        reference_value=reference,
        higher_max_resource=higher_resource,
    )


def _minimum_total_resource(
    service: ExtremeClassMasteryPairService,
    reference: float,
    incumbent_delta: float,
):
    maximum_step = int(MAX_RESOURCE_PROOF_CEILING // RESOURCE_STEP)
    for step in range(maximum_step + 1):
        resource = float(step * RESOURCE_STEP)
        row = _sorcerer(service, reference, resource)
        if row is None or row.projected_delta is None:
            continue
        if float(row.projected_delta) > incumbent_delta + 1e-9:
            return resource, row
    return None, None


def main() -> int:
    nongear, components = _nongear_preclass_weapon_damage()
    frontier, eligibility = _physical_frontier()
    mastery = ExtremeClassMasteryPairService(DATABASE)

    print("EXTREME WEAPON DAMAGE PHYSICAL-GEAR RESOURCE REQUIREMENTS")
    print(f"database={DATABASE}")
    print(f"objective={OBJECTIVE}")
    print("scope=mechanic-complete physical named-gear Pareto states")
    print("same_build_resource_maximum_assumed=False")
    print("resource_requirement_is_threshold_not_claimed_score=True")
    print()

    print("REVIEWED NON-GEAR PRE-CLASS WEAPON DAMAGE SUBTOTAL")
    for name, value in components:
        print(f"  {name}={value:.3f}")
    print(f"nongear_preclass_weapon_damage={nongear:.3f}")
    print("named_gear_in_subtotal=False")
    print("class_mastery_in_subtotal=False")
    print()

    print("PHYSICAL GEAR REQUIREMENTS")
    print(f"physical_pareto_count={len(frontier)}")
    live = 0
    impossible = 0
    rows_out = []
    for gear in frontier:
        reference = nongear + float(gear.weapon_damage)
        incumbent = _best_non_sorcerer(mastery, reference)
        if incumbent is None or incumbent.projected_delta is None:
            continue
        incumbent_delta = float(incumbent.projected_delta)
        threshold, sorc = _minimum_total_resource(mastery, reference, incumbent_delta)
        package = " + ".join(
            f"{name} {count}pc" for name, count in zip(gear.set_names, gear.counts)
        )
        if threshold is None or sorc is None:
            impossible += 1
            rows_out.append((float("inf"), -reference, package, gear, reference, incumbent, None, None))
            continue
        gear_resource = float(gear.higher_resource)
        required_non_gear = max(0.0, float(threshold) - gear_resource)
        live += 1
        rows_out.append((required_non_gear, -reference, package, gear, reference, incumbent, threshold, sorc))

    rows_out.sort(key=lambda item: (item[0], item[1], item[2].casefold()))
    for required_non_gear, _neg_reference, package, gear, reference, incumbent, threshold, sorc in rows_out:
        print(f"  {package}")
        print(
            f"    preclass_weapon_damage={reference:.3f} "
            f"gear_weapon_damage={gear.weapon_damage:.3f}"
        )
        print(
            f"    incumbent={incumbent.base_class.value} "
            f"incumbent_delta={float(incumbent.projected_delta):.3f} "
            f"mastery={incumbent.passive_names!r}"
        )
        print(f"    gear_higher_resource_delta={gear.higher_resource:.3f}")
        if threshold is None or sorc is None:
            print("    sorcerer_can_overtake_under_global_resource_ceiling=False")
        else:
            print(f"    minimum_total_higher_max_resource={float(threshold):.0f}")
            print(f"    minimum_required_non_gear_higher_resource={required_non_gear:.3f}")
            print(f"    sorcerer_percent_at_threshold={float(sorc.percent):.3f}")
            print(f"    sorcerer_delta_at_threshold={float(sorc.projected_delta):.3f}")
        print()

    print("PROOF STATUS")
    print(f"physical_states_with_finite_sorcerer_threshold={live}")
    print(f"physical_states_sorcerer_globally_pruned={impossible}")
    print(f"slot_eligibility_unresolved={len(eligibility.unresolved)}")
    print("final_weapon_damage_class_route_closed=False")
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=use the canonical whole-build evaluator to determine whether the exact Weapon-Damage-maximizing "
        "non-gear axes can supply each row's minimum_required_non_gear_higher_resource; only threshold-crossing "
        "packages need full Sorcerer same-build optimization, while unresolved gear mechanics remain separate blockers"
    )
    return 0 if frontier and not eligibility.unresolved else 2


if __name__ == "__main__":
    raise SystemExit(main())
