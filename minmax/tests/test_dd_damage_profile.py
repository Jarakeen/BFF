import pytest

from minmax.dd_damage_profile import (
    DDDamageProfile,
    get_dd_damage_profile,
)


def test_physical_damage_uses_weapon_damage_and_physical_penetration():
    result = get_dd_damage_profile("physical")

    assert isinstance(result, DDDamageProfile)
    assert result.offensive_stat == "weapon_damage"
    assert result.penetration_stat == "physical_penetration"


def test_poison_damage_uses_weapon_damage_and_physical_penetration():
    result = get_dd_damage_profile("poison")

    assert result.offensive_stat == "weapon_damage"
    assert result.penetration_stat == "physical_penetration"


def test_disease_damage_uses_weapon_damage_and_physical_penetration():
    result = get_dd_damage_profile("disease")

    assert result.offensive_stat == "weapon_damage"
    assert result.penetration_stat == "physical_penetration"


def test_bleed_damage_uses_weapon_damage_and_physical_penetration():
    result = get_dd_damage_profile("bleed")

    assert result.offensive_stat == "weapon_damage"
    assert result.penetration_stat == "physical_penetration"


def test_magical_damage_uses_spell_damage_and_spell_penetration():
    result = get_dd_damage_profile("magical")

    assert result.offensive_stat == "spell_damage"
    assert result.penetration_stat == "spell_penetration"


def test_flame_damage_uses_spell_damage_and_spell_penetration():
    result = get_dd_damage_profile("flame")

    assert result.offensive_stat == "spell_damage"
    assert result.penetration_stat == "spell_penetration"


def test_frost_damage_uses_spell_damage_and_spell_penetration():
    result = get_dd_damage_profile("frost")

    assert result.offensive_stat == "spell_damage"
    assert result.penetration_stat == "spell_penetration"


def test_shock_damage_uses_spell_damage_and_spell_penetration():
    result = get_dd_damage_profile("shock")

    assert result.offensive_stat == "spell_damage"
    assert result.penetration_stat == "spell_penetration"


def test_damage_type_is_case_insensitive():
    result = get_dd_damage_profile("FlAmE")

    assert result.damage_type == "flame"
    assert result.offensive_stat == "spell_damage"


def test_unsupported_damage_type_is_rejected():
    with pytest.raises(ValueError):
        get_dd_damage_profile("totally_not_a_damage_type")