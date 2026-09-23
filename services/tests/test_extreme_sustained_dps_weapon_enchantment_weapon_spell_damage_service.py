from minmax.character_build.effect_layer import BarId
from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit
from services.extreme_sustained_dps_weapon_enchantment_proc_consequence_service import (
    ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution,
    ExtremeSustainedDPSWeaponEnchantmentProcOccurrence,
)
from services.extreme_sustained_dps_weapon_enchantment_runtime_source_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
)
from services.extreme_sustained_dps_weapon_enchantment_weapon_spell_damage_service import (
    ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageService,
)


def _occurrence(time_seconds, *, duration=5.0, target=None, value=348.0):
    effect = CombatEffect(
        effect_type="weapon_spell_damage",
        value=value,
        source="Glyph of Weapon Damage",
        unit=EffectUnit.FLAT,
        target=target,
        duration_value=duration,
        duration_unit="seconds",
    )
    source = ExtremeSustainedDPSWeaponEnchantmentRuntimeSource(
        item_id=1,
        identity="weapon_damage",
        identity_label="Weapon Damage",
        source_label="Glyph of Weapon Damage",
        active_bar=BarId.FRONT,
        source_slot="main_hand",
        effects=(effect,),
    )
    return ExtremeSustainedDPSWeaponEnchantmentProcOccurrence(
        time_seconds=time_seconds,
        sequence=0,
        source=source,
        consequences=(effect,),
    )


def test_selected_weapon_damage_projects_exact_active_runtime_variant():
    result = ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageService.resolve(
        ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution(
            occurrences=(_occurrence(1.0),),
        )
    )

    assert result.resolved is True
    assert result.active_effects_at(0.999) == ()
    active = result.active_effects_at(1.0)
    assert len(active) == 1
    assert active[0].name == "weapon_spell_damage"
    assert active[0].magnitude == 348.0
    assert result.active_effects_at(5.999)[0].magnitude == 348.0
    assert result.active_effects_at(6.0) == ()


def test_adjacent_weapon_damage_windows_are_resolved():
    result = ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageService.resolve(
        ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution(
            occurrences=(
                _occurrence(1.0),
                _occurrence(6.0),
            ),
        )
    )

    assert result.resolved is True
    assert len(result.active_effects_at(6.0)) == 1


def test_overlapping_weapon_damage_windows_fail_closed():
    result = ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageService.resolve(
        ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution(
            occurrences=(
                _occurrence(1.0),
                _occurrence(5.0),
            ),
        )
    )

    assert result.resolved is False
    assert any("overlap" in row for row in result.unresolved)


def test_weapon_damage_requires_reviewed_duration_and_target():
    result = ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageService.resolve(
        ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution(
            occurrences=(_occurrence(1.0, duration=None, target="enemy"),),
        )
    )

    assert result.resolved is False
    assert any("duration" in row for row in result.unresolved)
