import math

from minmax.formulas.additional_formulas import (
    calculate_crit_resist,
    calculate_magicka_restore,
    calculate_stamina_restore,
    calculate_mount_run_speed,
    calculate_overload_damage,
    calculate_la_bow,
    calculate_la_overload,
)
from minmax.formulas.heavy_attack import (
    calculate_ha_restore_bow,
    calculate_ha_restore_werewolf,
    calculate_ha_flame_spell_damage,
    calculate_ha_physical_weapon_damage,
    calculate_ha_flame_staff,
    calculate_ha_dual_wield,
    calculate_ha_speed,
)
from minmax.formulas.mitigations import (
    calculate_direct_damage_taken,
    calculate_magic_damage_taken,
    calculate_damage_taken,
    calculate_attack_spell_crit_damage,
    calculate_defense_spell_aoe_mitigation,
)


def test_additional_formulas():
    assert calculate_crit_resist(effective_level=1, skill2_crit_resist=0.01) == 1321
    assert calculate_magicka_restore(item_magicka_restore=10, skill_magicka_restore=20) == 30
    assert calculate_stamina_restore(set_stamina_restore=7) == 7
    assert calculate_mount_run_speed(base_walk_speed=100) == 145
    assert calculate_overload_damage(cp_overload_damage=0.1, set_overload_damage=0.2) == 0.30000000000000004


def test_light_attack_additions():
    assert calculate_la_bow(
        magicka=1000, stamina=2000,
        la_physical_weapon_damage=500, la_physical_spell_damage=300,
    ) == math.floor(0.045 * 2000) + math.floor(0.4725 * 500)
    assert calculate_la_overload(
        magicka=1000, stamina=2000,
        la_physical_weapon_damage=500, la_physical_spell_damage=300,
    ) == math.floor(0.100 * 2000) + math.floor(1.050 * 500)


def test_heavy_attack_additions():
    assert calculate_ha_restore_bow() == 2772
    assert calculate_ha_restore_werewolf(skill_ha_sta_restore_werewolf=0.1) == 3235 * 1.1
    assert calculate_ha_flame_spell_damage(
        spell_damage=1000, skill_bonus_spell_damage_flame=100
    ) == 1100
    assert calculate_ha_physical_weapon_damage(
        weapon_damage=1000, skill_bonus_weapon_damage_physical=100
    ) == 1100
    assert calculate_ha_flame_staff(
        magicka=1000, stamina=1000,
        ha_flame_spell_damage=1000, ha_flame_weapon_damage=800,
    ) > 0
    assert calculate_ha_dual_wield(
        magicka=1000, stamina=1000,
        ha_physical_weapon_damage=1000, ha_physical_spell_damage=800,
    ) > 0
    assert calculate_ha_speed() == 1.0


def test_mitigation_additions():
    # The duplicate Set.DirectDamageTaken term is intentionally preserved from UESP.
    assert math.isclose(calculate_direct_damage_taken(set_direct_damage_taken=0.1), 1.2)
    assert calculate_magic_damage_taken(cp_magic_damage_taken=0.1) == 0.1
    assert calculate_damage_taken() == -0.15
    assert math.isclose(
        calculate_attack_spell_crit_damage(spell_crit_damage=0.5, target_crit_resist=250),
        0.465,
    )
    assert math.isclose(
        calculate_defense_spell_aoe_mitigation(aoe_damage_taken=0.1, defense_spell_mitigation=0.5),
        0.45,
    )
