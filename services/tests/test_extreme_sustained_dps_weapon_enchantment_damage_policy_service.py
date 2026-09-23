from minmax.character_build.effect_layer import BarId
from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit
from services.extreme_sustained_dps_weapon_enchantment_damage_policy_service import (
    ExtremeSustainedDPSWeaponEnchantmentDamagePolicyService,
)
from services.extreme_sustained_dps_weapon_enchantment_proc_consequence_service import (
    ExtremeSustainedDPSWeaponEnchantmentProcOccurrence,
)
from services.extreme_sustained_dps_weapon_enchantment_runtime_source_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
)


def _occurrence(*effects):
    source = ExtremeSustainedDPSWeaponEnchantmentRuntimeSource(
        item_id=1,
        identity="test",
        identity_label="Test",
        source_label="Test Glyph",
        active_bar=BarId.FRONT,
        source_slot="main_hand",
        effects=tuple(effects),
    )
    return ExtremeSustainedDPSWeaponEnchantmentProcOccurrence(
        time_seconds=1.0,
        sequence=2,
        source=source,
        consequences=tuple(effects),
    )


def _damage(damage_type, value=100.0):
    return CombatEffect(
        effect_type="damage",
        value=value,
        source="Test Glyph",
        unit=EffectUnit.FLAT,
        damage_type=damage_type,
    )


def test_oblivion_damage_uses_reviewed_noncritical_exception():
    result = ExtremeSustainedDPSWeaponEnchantmentDamagePolicyService.resolve(
        (_occurrence(_damage("oblivion")),)
    )

    assert result.resolved is True
    assert len(result.consequences) == 1
    row = result.consequences[0]
    assert row.damage_type == "oblivion"
    assert row.raw_value == 100.0
    assert row.can_crit is False
    assert "non-critical" in row.critical_evidence


def test_ordinary_elemental_enchant_crit_policy_fails_closed():
    result = ExtremeSustainedDPSWeaponEnchantmentDamagePolicyService.resolve(
        (_occurrence(_damage("flame")),)
    )

    assert result.resolved is False
    assert result.consequences[0].can_crit is None
    assert any(
        "critical eligibility is not authoritatively resolved" in row
        for row in result.unresolved
    )


def test_non_damage_consequences_are_not_reclassified_as_damage():
    restore = CombatEffect(
        effect_type="health_restore",
        value=100.0,
        source="Test Glyph",
        unit=EffectUnit.FLAT,
    )

    result = ExtremeSustainedDPSWeaponEnchantmentDamagePolicyService.resolve(
        (_occurrence(restore),)
    )

    assert result.resolved is True
    assert result.consequences == ()


def test_damage_without_canonical_type_fails_closed():
    result = ExtremeSustainedDPSWeaponEnchantmentDamagePolicyService.resolve(
        (_occurrence(_damage(None)),)
    )

    assert result.consequences == ()
    assert any("no canonical damage type" in row for row in result.unresolved)
