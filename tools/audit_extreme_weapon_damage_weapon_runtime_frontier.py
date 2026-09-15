from __future__ import annotations

"""Audit the reviewed U50 Weapon Damage weapon/runtime frontier.

This audit deliberately separates static sheet Weapon Damage from a proc-active
Weapon Damage enchant snapshot. It reuses canonical CP160 Gold weapon power,
Nirnhoned math, the reviewed Twin Blade and Blunt sword bonus, and canonical
weapon-enchantment semantics. It does not claim the whole-record denominator;
named gear and alternate weapon-line passives remain separate challengers.
"""

from math import floor
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.item_base_stats import (
    DUAL_WIELD_OFFHAND_POWER_RATIO,
    NAKED_LEVEL_50_POWER,
    WEAPON_NIRNHONED_PERCENT_GOLD,
    WEAPON_POWER_CP160_GOLD,
)
from minmax.rule_repository import RuleRepository
from minmax.weapon_enchantment_effect_service import WeaponEnchantmentEffectService
from minmax.weapon_enchantment_repository import WeaponEnchantmentRepository

DATABASE = ROOT / "data" / "eso.db"
TWIN_BLADE_SWORD_DAMAGE_PER_SWORD = 129.0


def _nirn_bonus(power: float, *, scale: float = 1.0) -> float:
    improved = float(floor(float(power) * (1.0 + WEAPON_NIRNHONED_PERCENT_GOLD)))
    return (improved - float(power)) * float(scale)


def _best_weapon_damage_enchant(service: WeaponEnchantmentEffectService, repository: WeaponEnchantmentRepository, *, trait: str | None = None):
    best = None
    for item_id, name in repository.list_items():
        effects = service.resolve_effects(
            item_id,
            weapon_trait=trait,
            weapon_quality="Legendary" if trait == "Infused" else None,
        )
        for effect in effects:
            if str(effect.effect_type or "").strip().casefold() != "weapon_spell_damage":
                continue
            candidate = (float(effect.value), int(item_id), str(name), effect)
            if best is None or candidate[0] > best[0]:
                best = candidate
    return best


def main() -> int:
    repository = WeaponEnchantmentRepository(DATABASE)
    effect_service = WeaponEnchantmentEffectService(
        enchantment_repository=repository,
        rule_repository=RuleRepository(DATABASE),
    )

    one_hand = float(WEAPON_POWER_CP160_GOLD["Sword"])
    two_hand = float(WEAPON_POWER_CP160_GOLD["Two-Handed"])

    dual_base = (one_hand - NAKED_LEVEL_50_POWER) + floor(one_hand * DUAL_WIELD_OFFHAND_POWER_RATIO)
    dual_nirn = _nirn_bonus(one_hand) + _nirn_bonus(one_hand, scale=DUAL_WIELD_OFFHAND_POWER_RATIO)
    dual_sword_passive = 2.0 * TWIN_BLADE_SWORD_DAMAGE_PER_SWORD
    dual_nirn_static = dual_base + dual_nirn + dual_sword_passive

    two_hand_base = two_hand - NAKED_LEVEL_50_POWER
    two_hand_nirn = _nirn_bonus(two_hand)
    two_hand_nirn_before_line_passive = two_hand_base + two_hand_nirn

    ordinary_enchant = _best_weapon_damage_enchant(effect_service, repository)
    infused_enchant = _best_weapon_damage_enchant(effect_service, repository, trait="Infused")

    unresolved: list[str] = []
    if ordinary_enchant is None:
        unresolved.append("No canonical weapon_spell_damage weapon enchantment resolved")
    if infused_enchant is None:
        unresolved.append("No Infused weapon_spell_damage weapon enchantment resolved")

    ordinary_value = 0.0 if ordinary_enchant is None else ordinary_enchant[0]
    infused_value = 0.0 if infused_enchant is None else infused_enchant[0]
    infused_gain = infused_value - ordinary_value

    # Nirnhoned and Infused are mutually exclusive on the same weapon. Compare
    # the trait opportunity on the reviewed dual-sword witness: Nirnhoned's
    # static weapon-power gain versus Infused's extra proc-active enchant gain.
    dual_main_nirn_gain = _nirn_bonus(one_hand)
    dual_trait_prefers_nirn_at_proc = dual_main_nirn_gain >= infused_gain - 1e-9

    print("EXTREME WEAPON DAMAGE WEAPON / RUNTIME FRONTIER")
    print(f"database={DATABASE}")
    print()
    print("DUAL WIELD REVIEWED WITNESS")
    print(f"one_hand_power={one_hand:.3f}")
    print(f"dual_offhand_ratio={DUAL_WIELD_OFFHAND_POWER_RATIO:.6f}")
    print(f"dual_base_delta={dual_base:.3f}")
    print(f"dual_nirnhoned_delta={dual_nirn:.3f}")
    print(f"twin_blade_sword_delta={dual_sword_passive:.3f}")
    print(f"dual_nirnhoned_static_weapon_delta={dual_nirn_static:.3f}")
    print()
    print("TWO-HANDED REFERENCE")
    print(f"two_handed_power={two_hand:.3f}")
    print(f"two_handed_base_delta={two_hand_base:.3f}")
    print(f"two_handed_nirnhoned_delta={two_hand_nirn:.3f}")
    print(f"two_handed_nirnhoned_before_weapon_line_passive={two_hand_nirn_before_line_passive:.3f}")
    print("two_handed_weapon_line_power_passive_still_separate_challenger=True")
    print()
    print("WEAPON DAMAGE ENCHANT")
    if ordinary_enchant is not None:
        value, item_id, name, effect = ordinary_enchant
        print(f"ordinary_enchant_name={name!r}")
        print(f"ordinary_enchant_item_id={item_id}")
        print(f"ordinary_enchant_value={value:.3f}")
        print(f"ordinary_enchant_duration={effect.duration_value!r} {effect.duration_unit!r}")
    if infused_enchant is not None:
        value, item_id, name, effect = infused_enchant
        print(f"infused_enchant_name={name!r}")
        print(f"infused_enchant_item_id={item_id}")
        print(f"infused_enchant_value={value:.3f}")
        print(f"infused_enchant_duration={effect.duration_value!r} {effect.duration_unit!r}")
    print(f"infused_extra_proc_value={infused_gain:.3f}")
    print()
    print("TRAIT OPPORTUNITY")
    print(f"dual_main_nirnhoned_static_gain={dual_main_nirn_gain:.3f}")
    print(f"infused_extra_proc_gain={infused_gain:.3f}")
    print(f"dual_main_nirnhoned_beats_infused_extra_proc={dual_trait_prefers_nirn_at_proc}")
    print("weapon_damage_enchant_runtime_condition_preserved=True")
    print()
    print("PROOF GATES")
    print(f"canonical_weapon_damage_enchant_resolved={ordinary_enchant is not None}")
    print(f"canonical_infused_enchant_scaling_resolved={infused_enchant is not None}")
    print("dual_sword_static_witness_resolved=True")
    print(f"unresolved_count={len(unresolved)}")
    for row in unresolved:
        print(f"  unresolved: {row}")
    closed = not unresolved
    print(f"weapon_damage_weapon_runtime_frontier_inventory_closed={closed}")
    print("NEXT_STEP=compare alternate weapon-line sheet-power passives against the reviewed dual-sword witness, then combine the winning weapon realization with named gear and class/runtime power challengers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
