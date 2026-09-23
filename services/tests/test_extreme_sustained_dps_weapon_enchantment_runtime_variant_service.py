from minmax.character_build.effect_layer import BarId
from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit
from services.extreme_sustained_dps_weapon_enchantment_runtime_source_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
)
from services.extreme_sustained_dps_weapon_enchantment_runtime_variant_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeVariantService,
)


def _source(identity="absorb_health", slot="main_hand"):
    return ExtremeSustainedDPSWeaponEnchantmentRuntimeSource(
        item_id=43573,
        identity=identity,
        identity_label="Absorb Health",
        source_label="Glyph of Absorb Health",
        active_bar=BarId.FRONT,
        source_slot=slot,
        effects=(
            CombatEffect(
                effect_type="damage",
                value=1900.0,
                source="Glyph of Absorb Health",
                unit=EffectUnit.FLAT,
                damage_type="magic",
            ),
            CombatEffect(
                effect_type="health_restore",
                value=861.0,
                source="Glyph of Absorb Health",
                unit=EffectUnit.FLAT,
            ),
        ),
    )


def test_runtime_variant_emits_one_selection_effect_for_multi_consequence_source():
    result = ExtremeSustainedDPSWeaponEnchantmentRuntimeVariantService.resolve(
        (_source(),)
    )

    assert result.resolved is True
    assert len(result.effects) == 1
    effect = result.effects[0]
    assert effect.name == "absorb_health"
    assert effect.source == "Glyph of Absorb Health"
    assert effect.source_slot == "main_hand"
    assert effect.trigger == "weapon_enchantment_activation"
    assert effect.magnitude is None
    assert any("selection identity only" in row for row in result.evidence)


def test_runtime_variant_keeps_distinct_hands_as_distinct_sources():
    result = ExtremeSustainedDPSWeaponEnchantmentRuntimeVariantService.resolve(
        (_source(slot="main_hand"), _source(slot="off_hand"))
    )

    assert result.resolved is True
    assert len(result.effects) == 2
    assert {effect.source_slot for effect in result.effects} == {
        "main_hand",
        "off_hand",
    }


def test_runtime_variant_rejects_duplicate_same_slot_identity():
    source = _source()
    result = ExtremeSustainedDPSWeaponEnchantmentRuntimeVariantService.resolve(
        (source, source)
    )

    assert len(result.effects) == 1
    assert result.resolved is False
    assert any("duplicate weapon-enchantment runtime source" in row for row in result.unresolved)
