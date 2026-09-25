from minmax.character_build.effect_layer import BarId
from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit
from models.combat_simulation import (
    CombatSimulationCombatant,
    CombatSimulationTargetState,
)
from services.extreme_sustained_dps_weapon_enchantment_oblivion_damage_service import (
    ExtremeSustainedDPSWeaponEnchantmentOblivionDamageService,
)
from services.extreme_sustained_dps_weapon_enchantment_proc_consequence_service import (
    ExtremeSustainedDPSWeaponEnchantmentProcOccurrence,
)
from services.extreme_sustained_dps_weapon_enchantment_runtime_source_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
)


def _state(maximum_health=200_000):
    return CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=maximum_health,
                maximum_health=maximum_health,
            ),
        ),
        recipient_bindings=(),
    )


def _occurrence(
    *,
    damage_type="oblivion",
    value=4875.0,
    scaling_type="target_max_health",
    quality="Gold",
    tier="Truly Superb",
    level="CP160",
):
    effect = CombatEffect(
        effect_type="damage",
        value=value,
        source="Glyph of Decrease Health",
        unit=EffectUnit.FLAT,
        damage_type=damage_type,
        target="target",
        scaling_type=scaling_type,
    )
    source = ExtremeSustainedDPSWeaponEnchantmentRuntimeSource(
        item_id=1,
        identity="decrease_health",
        identity_label="Decrease Health",
        source_label="Glyph of Decrease Health",
        active_bar=BarId.FRONT,
        source_slot="main_hand",
        effects=(effect,),
        enchantment_quality=quality,
        enchantment_tier=tier,
        item_level=level,
    )
    return ExtremeSustainedDPSWeaponEnchantmentProcOccurrence(
        time_seconds=1.0,
        sequence=2,
        source=source,
        consequences=(effect,),
    )


def test_legendary_cp160_oblivion_damage_caps_at_4875():
    result = ExtremeSustainedDPSWeaponEnchantmentOblivionDamageService.resolve(
        occurrences=(_occurrence(),),
        target_state=_state(200_000),
        target_identity="Boss",
    )

    assert result.resolved is True
    assert result.unresolved == ()
    assert len(result.damage) == 1
    row = result.damage[0]
    assert row.amount == 4875.0
    assert row.damage_type == "oblivion"
    assert row.recipient == "Boss"
    assert any(
        "reviewed non-critical proc exception" in evidence
        for evidence in result.evidence
    )


def test_legendary_cp160_oblivion_damage_uses_target_max_health_below_cap():
    result = ExtremeSustainedDPSWeaponEnchantmentOblivionDamageService.resolve(
        occurrences=(_occurrence(),),
        target_state=_state(100_000),
        target_identity="Boss",
    )

    assert result.resolved is True
    assert result.damage[0].amount == 3750.0


def test_missing_glyph_quality_fails_closed_instead_of_borrowing_weapon_quality():
    result = ExtremeSustainedDPSWeaponEnchantmentOblivionDamageService.resolve(
        occurrences=(_occurrence(quality=None),),
        target_state=_state(),
        target_identity="Boss",
    )

    assert result.damage == ()
    assert any(
        "requires explicit Legendary/Gold glyph quality" in row
        for row in result.unresolved
    )


def test_non_oblivion_weapon_enchantment_damage_remains_unresolved():
    result = ExtremeSustainedDPSWeaponEnchantmentOblivionDamageService.resolve(
        occurrences=(_occurrence(damage_type="flame", scaling_type=None),),
        target_state=_state(),
        target_identity="Boss",
    )

    assert result.damage == ()
    assert any(
        "outside the reviewed exact Oblivion consumer" in row
        for row in result.unresolved
    )


def test_stale_or_trait_inflated_oblivion_cap_fails_closed():
    result = ExtremeSustainedDPSWeaponEnchantmentOblivionDamageService.resolve(
        occurrences=(_occurrence(value=6337.5),),
        target_state=_state(),
        target_identity="Boss",
    )

    assert result.damage == ()
    assert any(
        "does not match reviewed CP160 Legendary 4875" in row
        for row in result.unresolved
    )


def test_missing_target_max_health_fails_closed():
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=None,
                maximum_health=None,
            ),
        ),
        recipient_bindings=(),
    )
    result = ExtremeSustainedDPSWeaponEnchantmentOblivionDamageService.resolve(
        occurrences=(_occurrence(),),
        target_state=state,
        target_identity="Boss",
    )

    assert result.damage == ()
    assert any("requires target maximum Health" in row for row in result.unresolved)
