from minmax.character_build.effect_layer import BarId
from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit
from minmax.weapon_enchantment_runtime_cadence import WeaponEnchantmentEffectFamily
from services.extreme_sustained_dps_weapon_enchantment_cadence_family_service import (
    ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService,
)
from services.extreme_sustained_dps_weapon_enchantment_runtime_source_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
)


def _source(*effect_types):
    rows = tuple(
        CombatEffect(
            effect_type=effect_type,
            value=100.0,
            source="Glyph",
            unit=EffectUnit.FLAT,
        )
        for effect_type in effect_types
    )
    return ExtremeSustainedDPSWeaponEnchantmentRuntimeSource(
        item_id=1,
        identity="glyph",
        identity_label="Glyph",
        source_label="Glyph",
        active_bar=BarId.FRONT,
        source_slot="main_hand",
        effects=rows,
    )


def test_damage_plus_restore_is_direct_damage_cadence_family():
    result = ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService.resolve(
        _source("damage", "health_restore")
    )

    assert result.resolved is True
    assert result.family is WeaponEnchantmentEffectFamily.DIRECT_DAMAGE
    assert any("co-produced restoration" in row for row in result.evidence)


def test_crusher_style_debuff_is_buff_or_debuff_cadence_family():
    result = ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService.resolve(
        _source("physical_spell_resistance_reduction")
    )

    assert result.resolved is True
    assert result.family is WeaponEnchantmentEffectFamily.BUFF_OR_DEBUFF


def test_weapon_damage_buff_is_buff_or_debuff_cadence_family():
    result = ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService.resolve(
        _source("weapon_spell_damage")
    )

    assert result.resolved is True
    assert result.family is WeaponEnchantmentEffectFamily.BUFF_OR_DEBUFF


def test_restoration_only_source_fails_closed():
    result = ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService.resolve(
        _source("magicka_restore")
    )

    assert result.family is None
    assert result.resolved is False
    assert any("restoration-only" in row for row in result.unresolved)


def test_unknown_consequence_type_fails_closed():
    result = ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService.resolve(
        _source("mysterious_effect")
    )

    assert result.family is None
    assert result.resolved is False
    assert any("unreviewed cadence-family" in row for row in result.unresolved)
