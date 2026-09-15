from tools.audit_extreme_weapon_damage_armor_mundus_cp_frontier import (
    _is_scoped_power_only,
    _is_sheet_weapon_damage_relevant,
)


def test_scoped_weapon_spell_damage_branches_do_not_count_as_sheet_stat() -> None:
    assert _is_scoped_power_only(
        "Grants 41 Weapon and Spell Damage to your damaging abilities per stage."
    )
    assert _is_scoped_power_only(
        "Grants 41 Weapon and Spell Damage to your healing abilities per stage."
    )
    assert _is_scoped_power_only(
        "Grants 100 Weapon and Spell Damage to Martial attacks. Affects Physical, Poison, Disease and Bleed Damage."
    )
    assert _is_scoped_power_only(
        "Grants 100 Weapon and Spell Damage to Magical attacks. Affects Magic, Flame, Frost, and Shock Damage."
    )

    assert not _is_sheet_weapon_damage_relevant(
        "Grants 41 Weapon and Spell Damage to your damaging abilities per stage."
    )


def test_generic_weapon_spell_damage_remains_sheet_stat_relevant() -> None:
    assert _is_sheet_weapon_damage_relevant(
        "Increases your Weapon and Spell Damage by 3 per stage."
    )
    assert not _is_scoped_power_only(
        "Increases your Weapon and Spell Damage by 3 per stage."
    )
