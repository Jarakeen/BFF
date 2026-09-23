from minmax.character_build.effect_layer import BarId
from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit
from services.extreme_sustained_dps_weapon_enchantment_consequence_coverage_service import (
    ExtremeSustainedDPSWeaponEnchantmentConsequenceCoverageService,
)
from services.extreme_sustained_dps_weapon_enchantment_proc_consequence_service import (
    ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution,
    ExtremeSustainedDPSWeaponEnchantmentProcOccurrence,
)
from services.extreme_sustained_dps_weapon_enchantment_runtime_source_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
)


def _resolution(*effect_types):
    effects = tuple(
        CombatEffect(
            effect_type=effect_type,
            value=100.0,
            source="Test Glyph",
            unit=EffectUnit.FLAT,
        )
        for effect_type in effect_types
    )
    source = ExtremeSustainedDPSWeaponEnchantmentRuntimeSource(
        item_id=1,
        identity="test",
        identity_label="Test",
        source_label="Test Glyph",
        active_bar=BarId.FRONT,
        source_slot="main_hand",
        effects=effects,
    )
    return ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution(
        occurrences=(
            ExtremeSustainedDPSWeaponEnchantmentProcOccurrence(
                time_seconds=1.0,
                sequence=2,
                source=source,
                consequences=effects,
            ),
        ),
    )


def test_selected_unconsumed_consequences_block_leaf_completeness():
    result = ExtremeSustainedDPSWeaponEnchantmentConsequenceCoverageService.assess(
        _resolution("damage", "health_restore"),
    )

    assert result.complete is False
    assert result.selected_consequence_count == 2
    assert result.consumed_consequence_count == 0
    assert any("damage" in row for row in result.unresolved)
    assert any("health_restore" in row for row in result.unresolved)


def test_only_explicitly_consumed_effect_types_clear_coverage():
    result = ExtremeSustainedDPSWeaponEnchantmentConsequenceCoverageService.assess(
        _resolution("damage", "health_restore"),
        consumed_effect_types=("damage", "health_restore"),
    )

    assert result.complete is True
    assert result.unresolved == ()
    assert result.selected_consequence_count == 2
    assert result.consumed_consequence_count == 2


def test_missing_effect_type_fails_closed():
    result = ExtremeSustainedDPSWeaponEnchantmentConsequenceCoverageService.assess(
        _resolution(""),
    )

    assert result.complete is False
    assert any("no canonical effect type" in row for row in result.unresolved)
